"""One frozen development comparison; confirmation is never loaded here."""
from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path

from .artifacts import sha256_file, verified_artifacts
from .provenance import new_manifest, require_upstream, save_manifest
from .v2_data import DATA_MANIFEST, load_partition
from .v2_protocol import BudgetLedger, LEDGER, require_contract, write_json


def negative_threshold(scores, alpha=.05):
    import numpy as np
    scores=np.asarray(scores,dtype=float)
    if scores.ndim != 1 or not len(scores) or not np.isfinite(scores).all() or not 0 < alpha < 1:
        raise ValueError("Threshold needs finite negative calibration scores")
    return float(np.sort(scores)[math.ceil((1-alpha)*len(scores))-1])


def operating_metrics(y,scores,threshold):
    import numpy as np
    from sklearn.metrics import average_precision_score, roc_auc_score
    y=np.asarray(y)
    if set(np.unique(y)) != {0,1}:
        raise ValueError("Both outcome classes required for a development comparison")
    alerts=np.asarray(scores)>threshold
    return {"recall":float(alerts[y==1].mean()),"fpr":float(alerts[y==0].mean()),
            "auroc":float(roc_auc_score(y,scores)),"average_precision":float(average_precision_score(y,scores)),
            "precision":float(y[alerts].mean()) if alerts.any() else 0.0,
            "failures":int(y.sum()),"successes":int((y==0).sum())}


def ranking(metrics,C):
    return (metrics["fpr"] <= .08,metrics["recall"],metrics["auroc"],-C)


def validation_halves(ids,study_id):
    import numpy as np
    order=sorted(range(len(ids)),key=lambda i:hashlib.sha256((study_id+str(ids[i])).encode()).hexdigest())
    return np.asarray(order[::2]),np.asarray(order[1::2])


def fit_with_budget(x,y,C,seed,ledger):
    import numpy as np
    from .followup import fit_linear
    from threadpoolctl import threadpool_limits
    with ledger.operation("linear probe fit",timed_resource="cpu_fit_seconds",fit_jobs=1), threadpool_limits(limits=1):
        return fit_linear(x,y,np.arange(len(y)),C,seed)


def select_family(train_x,train_y,val_x,val_y,selection,assessment,protocol,ledger):
    choices=[]
    for C in protocol["fitting"]["C"]:
        fitted=fit_with_budget(train_x,train_y,C,protocol["fitting"]["seed"],ledger)
        scores=fitted.margins(val_x)
        threshold=negative_threshold(scores[selection][val_y[selection]==0],protocol["fitting"]["threshold_fpr"])
        metrics=operating_metrics(val_y[assessment],scores[assessment],threshold)
        choices.append((ranking(metrics,C),fitted,metrics))
    _,best,metrics=max(choices,key=lambda item:item[0])
    return best,{"C":best.C,"validation_metrics":metrics}


def development_gate(candidate,controls,protocol):
    target=protocol["confirmation"]
    return bool(candidate["recall"] >= target["minimum_recall"] and candidate["fpr"] <= target["maximum_fpr"] and
                all(candidate["recall"]-control["recall"] >= target["minimum_recall_lift"] for control in controls))


def encode_puzzle(puzzle):
    from .diagnostics import independent_cells
    cells=independent_cells(puzzle)
    if cells is None:
        raise ValueError("Malformed Sudoku input")
    rows=[list(cells[r*9:(r+1)*9]) for r in range(9)]
    return [11]+sum((row+([10] if r<8 else []) for r,row in enumerate(rows)),[])+[11]


def retained_payload(root,run_id,name,payload,ledger):
    target=root/"results/v2/features"/run_id/name
    with ledger.operation(f"retain {name}",feature_bytes=len(payload)):
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open("xb") as stream:
            stream.write(payload)
    return {"file":target.relative_to(root).as_posix(),"sha256":sha256_file(target),"bytes":len(payload)}


def capture_partition(root,rows,role,adapter,observer,protocol,run_id,ledger):
    import numpy as np
    import torch
    from .probes import feature_vector
    from .representations import extract_features
    from .schema import LevelState
    from .spatial import reconstruct_prefix
    from .sudoku_labels import validate_sudoku
    decoded,input_decoded,hidden,confidence,labels=[],[],[],[],[]
    level=protocol["primary_level"]
    for start in range(0,len(rows),protocol["batch_size"]):
        batch=rows[start:start+protocol["batch_size"]]
        with ledger.operation(f"{role} capture {start}",timed_resource="gpu_seconds"):
            context=adapter.prepare_context([encode_puzzle(row["puzzle"]) for row in batch])
            codes,obs=observer.generate(context)
            prefix=torch.tensor([sum((list(c) for c in item),[]) for item in obs.codes_prefix_by_sample],device=adapter.device)
            with torch.no_grad():
                latent=reconstruct_prefix(adapter.tokenizer.vqvae.vq,prefix,level)
                current=adapter._decode_latent(latent)
                final=adapter.decode_final(codes)
            for index,row in enumerate(batch):
                state=LevelState(run_id,row["puzzle_id"],f"{run_id}-{row['puzzle_id']}",level,obs.codes_prefix_by_sample[index],current[index])
                features=extract_features(state,row["puzzle"])
                decoded.append(feature_vector(features,state.codes_prefix,"decoded")[1])
                input_decoded.append(feature_vector(features,state.codes_prefix,"input_decoded")[1])
                hidden.append(obs.activation_by_sample[index])
                confidence.append(obs.confidence_by_sample[index])
                labels.append(int(not validate_sudoku(row["puzzle"],final[index]).is_valid))
            torch.cuda.synchronize()
        if (start+len(batch))%800 == 0 or start+len(batch)==len(rows):
            print(f"Captured {role}: {start+len(batch)}/{len(rows)}",flush=True)
    arrays={"decoded":np.asarray(decoded),"input_decoded":np.asarray(input_decoded),"activation":np.asarray(hidden),
            "confidence":np.asarray(confidence),"y":np.asarray(labels),"puzzle_ids":np.asarray([r["puzzle_id"] for r in rows])}
    arrays["decoded_confidence"]=np.concatenate((arrays["decoded"],arrays["confidence"]),axis=1)
    arrays["input_decoded_confidence"]=np.concatenate((arrays["input_decoded"],arrays["confidence"]),axis=1)
    payload=io.BytesIO()
    np.savez_compressed(payload,**arrays)
    entry=retained_payload(root,run_id,f"{role}.npz",payload.getvalue(),ledger)
    entry.update(puzzles=len(rows),failures=int(arrays["y"].sum()),successes=int((arrays["y"]==0).sum()))
    return arrays,entry


def run_study(root: Path,protocol_path: Path) -> Path:
    import numpy as np
    import torch
    from .upstream_adapter import NCMAdapter
    from .v2_observer import GeneratorObserver
    p,contract=require_contract(root,protocol_path)
    require_upstream(root)
    if verified_artifacts(root) != contract["artifact_sha256"]:
        raise ValueError("Official artifacts changed")
    data=json.loads((root/DATA_MANIFEST).read_text(encoding="utf-8"))
    if data["status"] != "eligible" or data["protocol_sha256"] != contract["protocol_sha256"]:
        raise ValueError("New data gate has not passed for frozen protocol")
    previous=list((root/"results/manifests").glob("*v2-study.json"))
    if previous:
        raise ValueError("Bounded study already attempted; refusing an unplanned repeat")
    pilots=[json.loads(path.read_text()) for path in (root/"results/manifests").glob("*v2-pilot.json")]
    if not any(m["status"]=="passed" and m["configuration"]["protocol_sha256"]==contract["protocol_sha256"] for m in pilots):
        raise ValueError("Measurement gate has not passed")
    rows={role:load_partition(root,role) for role in ("train","validation","calibration")}
    ledger=BudgetLedger(root/LEDGER,contract["protocol_sha256"],p["limits"])
    manifest=new_manifest(root,"v2-study",{"protocol_sha256":contract["protocol_sha256"],"data_manifest_sha256":sha256_file(root/DATA_MANIFEST),"confirmation_accessed":False})
    path=save_manifest(root,manifest)
    try:
        with ledger.operation("load checkpoints and fixed observer",timed_resource="gpu_seconds"):
            adapter=NCMAdapter.load(root/"third_party/ncm",root/"third_party/ncm/config/eval/sudoku-hard.yaml",root/"artifacts/sudoku-hard",device="cuda")
            observer=GeneratorObserver(adapter,level=p["primary_level"],projection_dimension=p["measurement"]["projection_dimension"],seed=p["measurement"]["projection_seed"])
            torch.cuda.synchronize()
        datasets={}
        manifest["captures"]={}
        for role in rows:
            datasets[role],manifest["captures"][role]=capture_partition(root,rows[role],role,adapter,observer,p,manifest["run_id"],ledger)
            save_manifest(root,manifest)
        del adapter,observer
        torch.cuda.empty_cache()
        train,val,cal=(datasets[role] for role in ("train","validation","calibration"))
        selection,assessment=validation_halves(val["puzzle_ids"],p["study_id"])
        manifest["validation_halves"]={"selection":[str(val["puzzle_ids"][i]) for i in selection],"assessment":[str(val["puzzle_ids"][i]) for i in assessment]}
        chosen={}
        families=p["fitting"]["families"]
        for family in families:
            _,chosen[family]=select_family(train[family],train["y"],val[family],val["y"],selection,assessment,p,ledger)
        confidence_families=[name for name in families if "confidence" in name]
        best_conf=max(confidence_families,key=lambda name:ranking(chosen[name]["validation_metrics"],chosen[name]["C"])+(-families.index(name),))
        for dataset in datasets.values():
            dataset["activation_candidate"]=np.concatenate((dataset[best_conf],dataset["activation"]),axis=1)
        _,chosen["activation_candidate"]=select_family(train["activation_candidate"],train["y"],val["activation_candidate"],val["y"],selection,assessment,p,ledger)
        manifest.update(selected=chosen,activation_base=best_conf)
        save_manifest(root,manifest)
        models,metrics,thresholds,scores={},{},{},{}
        for family,choice in chosen.items():
            fitted=fit_with_budget(np.concatenate((train[family],val[family])),np.concatenate((train["y"],val["y"])),choice["C"],p["fitting"]["seed"],ledger)
            scores[family]=fitted.margins(cal[family])
            thresholds[family]=negative_threshold(scores[family][cal["y"]==0],p["fitting"]["threshold_fpr"])
            metrics[family]=operating_metrics(cal["y"],scores[family],thresholds[family])
            target=root/"results/v2/models"/manifest["run_id"]/f"{family}.json"
            record={"family":family,"activation_base":best_conf,"C":fitted.C,"mean":fitted.scaler.mean_.tolist(),
                    "scale":fitted.scaler.scale_.tolist(),"coefficient":fitted.model.coef_[0].tolist(),"intercept":float(fitted.model.intercept_[0]),
                    "threshold":thresholds[family],"classes":fitted.model.classes_.tolist(),"protocol_sha256":contract["protocol_sha256"]}
            encoded=(json.dumps(record,indent=2)+"\n").encode()
            with ledger.operation(f"retain {family} probe",feature_bytes=len(encoded)):
                if target.exists():
                    raise ValueError("Refusing to overwrite probe")
                write_json(target,record)
            replay=(cal[family]-np.asarray(record["mean"]))/np.asarray(record["scale"]) @ np.asarray(record["coefficient"])+record["intercept"]
            if not np.allclose(replay,scores[family],rtol=0,atol=1e-10):
                raise ValueError("Portable probe score replay differs")
            models[family]={"file":target.relative_to(root).as_posix(),"sha256":sha256_file(target)}
        shuffle=np.random.default_rng(p["fitting"]["seed"]).permutation(train["y"])
        shuffled=fit_with_budget(train["activation_candidate"],shuffle,chosen["activation_candidate"]["C"],p["fitting"]["seed"],ledger)
        from sklearn.metrics import roc_auc_score
        manifest["label_shuffle_validation_auroc"]=float(roc_auc_score(val["y"],shuffled.margins(val["activation_candidate"])))
        candidate=None
        required=[]
        if development_gate(metrics["activation_candidate"],[metrics[f] for f in families],p):
            candidate="activation_candidate"; required=families
        elif development_gate(metrics[best_conf],[metrics[f] for f in families if "confidence" not in f],p):
            candidate=best_conf; required=[f for f in families if "confidence" not in f]
        manifest.update(status="passed",development_metrics=metrics,thresholds=thresholds,models=models,
                        candidate=candidate,required_comparators=required,development_gate_passed=candidate is not None,
                        confirmation_accessed=False,budget=ledger.snapshot(),
                        decision="freeze one candidate for confirmation" if candidate else "close detector study: no candidate passes frozen development criteria")
        if candidate:
            target=root/"results/v2/contracts/generator-signals-v1-candidate.json"
            if target.exists():
                raise ValueError("Candidate already frozen")
            write_json(target,{"protocol_sha256":contract["protocol_sha256"],"study_manifest":path.relative_to(root).as_posix(),
                               "candidate":candidate,"required_comparators":required,"models":models,"activation_base":best_conf,
                               "data_manifest_sha256":sha256_file(root/DATA_MANIFEST)})
    except BaseException as error:
        manifest.update(status="failed",error=f"{type(error).__name__}: {error}",budget=ledger.snapshot(),confirmation_accessed=False)
        save_manifest(root,manifest)
        raise
    return save_manifest(root,manifest)
