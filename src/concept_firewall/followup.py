"""One bounded development-only spatial study with nested grouped evaluation.

Primary aggregation is the sample-weighted mean of four outer-fold AUROCs.
Paired bootstrap resamples puzzle groups within each outer assessment fold;
it is conditional on fitted models and is exploratory, not fresh confirmation.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time

from .artifacts import sha256_file, verified_artifacts
from .provenance import new_manifest, require_upstream, save_manifest
from .spatial import rademacher_projection, reconstruct_prefix, spatial_summaries


def group_folds(groups, n_folds: int, seed: int):
    import numpy as np
    unique=sorted(set(groups))
    if n_folds < 2 or len(unique) < n_folds:
        raise ValueError("Not enough distinct groups for the declared folds")
    rng=np.random.default_rng(seed)
    rng.shuffle(unique)
    assignment={key:index % n_folds for index,key in enumerate(unique)}
    return np.asarray([assignment[key] for key in groups])


@dataclass
class FittedLinear:
    scaler: object
    model: object
    C: float
    validation_loss: float

    def margins(self,x):
        return self.model.decision_function(self.scaler.transform(x))


def fit_linear(x,y,training,C,seed):
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    if len(np.unique(y[training])) != 2:
        raise ValueError("Both classes are required in each fitting partition")
    scaler=StandardScaler().fit(x[training])
    model=LogisticRegression(C=C,solver="liblinear",max_iter=2000,random_state=seed).fit(scaler.transform(x[training]),y[training])
    if np.any(model.n_iter_ >= 2000):
        raise RuntimeError("Follow-up logistic regression did not converge")
    return FittedLinear(scaler,model,C,float("inf"))


def select_linear(x,y,training,inner_folds,C_values,seed,deadline):
    import numpy as np
    from sklearn.metrics import log_loss
    choices=[]
    for C in C_values:
        losses,weights=[],[]
        for fold in sorted(set(inner_folds)):
            if time.perf_counter() > deadline:
                raise RuntimeError("Declared fitting time budget exhausted")
            fit=training[inner_folds != fold]
            validation=training[inner_folds == fold]
            if len(np.unique(y[validation])) != 2:
                raise ValueError("Inner assessment fold has a single class")
            fitted=fit_linear(x,y,fit,C,seed)
            losses.append(log_loss(y[validation],fitted.model.predict_proba(fitted.scaler.transform(x[validation]))[:,1]))
            weights.append(len(validation))
        choices.append((float(np.average(losses,weights=weights)),C))
    loss,C=min(choices)
    fitted=fit_linear(x,y,training,C,seed)
    fitted.validation_loss=loss
    return fitted


def paired_fold_intervals(y,predictions,groups,folds,*,replicates,seed,coverage):
    import numpy as np
    from sklearn.metrics import roc_auc_score
    rng=np.random.default_rng(seed)
    scores={name:[] for name in ("selected_cheap_row","selected_cheap_cell")}
    fold_values=sorted(set(folds))
    all_indices={key:np.flatnonzero(np.asarray(groups)==key) for key in sorted(set(groups))}
    by_fold={fold:sorted(set(np.asarray(groups)[folds==fold])) for fold in fold_values}
    for _ in range(replicates):
        differences={name:[] for name in scores}
        weights=[]
        valid=True
        for fold in fold_values:
            keys=by_fold[fold]
            sampled=np.concatenate([all_indices[keys[i]] for i in rng.integers(len(keys),size=len(keys))])
            if len(np.unique(y[sampled])) != 2:
                valid=False
                break
            baseline=roc_auc_score(y[sampled],predictions["selected_cheap"][sampled])
            for name in scores:
                differences[name].append(roc_auc_score(y[sampled],predictions[name][sampled])-baseline)
            weights.append(len(sampled))
        if valid:
            for name in scores:
                scores[name].append(float(np.average(differences[name],weights=weights)))
    alpha=(1-coverage)/2
    if not all(scores.values()):
        raise ValueError("No valid paired bootstrap replicates")
    return {name:{"interval":list(map(float,np.quantile(values,[alpha,1-alpha]))),"coverage":coverage,"valid_replicates":len(values)} for name,values in scores.items()}


def capture_spatial_features(root,data,destination,protocol):
    import numpy as np
    import torch
    from .upstream_adapter import NCMAdapter
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; no replacement architecture or CPU cost estimate used")
    require_upstream(root)
    verified_artifacts(root)
    adapter=NCMAdapter.load(root/"third_party/ncm",root/"third_party/ncm/config/eval/sudoku-hard.yaml",root/"artifacts/sudoku-hard")
    vq=adapter.tokenizer.vqvae.vq
    dimension=protocol["projection_dimension"]
    row_np=rademacher_projection(9*vq.embed_dim,dimension,protocol["row_projection_seed"])
    cell_np=rademacher_projection(81*vq.embed_dim,dimension,protocol["cell_projection_seed"])
    projection_path=destination/"frozen_projections.npz"
    np.savez_compressed(projection_path,row=row_np,cell=cell_np)
    row_matrix,cell_matrix=torch.from_numpy(row_np).cuda(),torch.from_numpy(cell_np).cuda()
    arrays={key:data[key] for key in data.files}
    torch.cuda.synchronize()
    started=time.perf_counter()
    count=len(data["y"])
    parent=json.loads((root/protocol["parent_collection"]).read_text())
    batch_size=parent["configuration"]["batch_size"]
    for level in (protocol["primary_level"],protocol["secondary_level"]):
        rows,cells=[],[]
        for offset in range(0,count,batch_size):
            if time.perf_counter()-started > protocol["maximum_feature_capture_seconds"]:
                raise RuntimeError("Declared feature capture time budget exhausted")
            codes=torch.as_tensor(data[f"level{level}_codes"][offset:offset+batch_size],device="cuda")
            with torch.no_grad():
                latent=reconstruct_prefix(vq,codes,level)
                if not np.allclose(latent.mean(dim=1).cpu().numpy(),data[f"level{level}_latent"][offset:offset+batch_size],atol=1e-6,rtol=1e-5):
                    raise ValueError("Prefix reconstruction differs from the audited mean representation")
                expected=tuple(data[f"level{level}_boards"][offset:offset+batch_size])
                decoded=adapter._decode_latent(latent)
                if decoded != expected:
                    index=next(i for i,(a,b) in enumerate(zip(decoded,expected)) if a!=b)
                    raise ValueError(f"Prefix decoding differs from audited board at level {level}, development offset {offset+index}, batch size {batch_size}")
                row_features,cell_features=spatial_summaries(latent,row_matrix,cell_matrix)
                rows.append(row_features.cpu().numpy())
                cells.append(cell_features.cpu().numpy())
        arrays[f"level{level}_row"]=np.concatenate(rows)
        arrays[f"level{level}_cell"]=np.concatenate(cells)
        print(f"Captured two frozen spatial variants at level {level} on {count} development puzzles",flush=True)
    torch.cuda.synchronize()
    elapsed=time.perf_counter()-started
    output=destination/"development_spatial.npz"
    np.savez_compressed(output,**arrays)
    return arrays,{"features_sha256":sha256_file(output),"projection_sha256":sha256_file(projection_path),"capture_wall_seconds":elapsed,"batch_size":batch_size,"scope":"offline prefix reconstruction/decoding/projection only; no generation or online savings benchmark","all_prefix_decodes_match":True}


def run_followup(root:Path,audit_path:Path,protocol_path:Path)->Path:
    import numpy as np
    from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss
    from scipy.special import expit
    from threadpoolctl import threadpool_limits
    protocol=json.loads(protocol_path.read_text())
    audit=json.loads(audit_path.read_text())
    if audit.get("mode") != "m3-audit" or audit.get("status") != "passed":
        raise ValueError("A passed independent audit is required")
    if sha256_file(protocol_path) != audit["configuration"]["protocol_sha256"]:
        raise ValueError("Study protocol changed after the diagnostic audit")
    if protocol["new_representations"] != ["row_projection","cell_projection"]:
        raise ValueError("The bounded study permits exactly the two declared spatial variants")
    manifest=new_manifest(root,"m3-followup",{"protocol":protocol,"protocol_sha256":sha256_file(protocol_path),"audit_manifest":str(audit_path.relative_to(root)),"audit_sha256":sha256_file(audit_path)})
    manifest["aggregation"]="sample-weighted mean of outer-fold AUROCs is primary; pooled out-of-fold AUROC is descriptive secondary"
    manifest["fresh_confirmation_available"]=False
    manifest_path=save_manifest(root,manifest)
    try:
        input_path=root/audit["development_directory"]/"development.npz"
        if sha256_file(input_path) != audit["development_sha256"]:
            raise ValueError("Audited development features changed")
        old_splits=json.loads((root/protocol["parent_splits"]).read_text())
        expected=set(key for part in protocol["development_partitions"] for key in old_splits[part])
        with np.load(input_path,allow_pickle=False) as data:
            keys=data["puzzle_ids"].tolist()
            if set(keys) != expected or len(keys) != len(expected) or set(keys)&set(old_splits["test"]):
                raise ValueError("Old test identities or unexpected puzzles entered the follow-up")
            destination=root/"results/probes"/manifest["run_id"]
            destination.mkdir(parents=True)
            arrays,capture=capture_spatial_features(root,data,destination,protocol)
        y=arrays["y"]
        groups=arrays["groups"]
        folds=group_folds(groups,protocol["outer_folds"],protocol["fold_seed"])
        fold_document={"protocol_sha256":sha256_file(protocol_path),"excluded_original_test_puzzles":len(old_splits["test"]),"outer":[]}
        inner_assignments={}
        for fold in range(protocol["outer_folds"]):
            training=np.flatnonzero(folds!=fold)
            assessment=np.flatnonzero(folds==fold)
            inner=group_folds(groups[training],protocol["inner_folds"],protocol["fold_seed"]+fold+1)
            inner_assignments[fold]=inner
            fold_document["outer"].append({"fold":fold,"training_ids":[keys[i] for i in training],"assessment_ids":[keys[i] for i in assessment],"inner_assessment_ids":[[keys[i] for i in training[inner==j]] for j in range(protocol["inner_folds"])]})
        fold_path=root/"results/manifests"/f"{manifest['run_id']}-folds.json"
        fold_path.write_text(json.dumps(fold_document,indent=2)+"\n",encoding="utf-8")
        manifest.update(development_puzzles=len(keys),development_failures=int(y.sum()),excluded_original_test_puzzles=len(old_splits["test"]),fold_manifest=str(fold_path.relative_to(root)),fold_sha256=sha256_file(fold_path),feature_capture=capture,probe_directory=str(destination.relative_to(root)))
        save_manifest(root,manifest)
        started=time.perf_counter()
        deadline=started+protocol["maximum_fitting_seconds"]
        results=[]
        with threadpool_limits(limits=1):
            for level in (protocol["primary_level"],protocol["secondary_level"]):
                base={"decoded":arrays[f"level{level}_decoded"],"input_decoded":arrays[f"level{level}_input_decoded"],"mean_only":arrays[f"level{level}_latent"],"row_only":arrays[f"level{level}_row"],"cell_only":arrays[f"level{level}_cell"]}
                predictions={name:np.full(len(y),np.nan) for name in protocol["models"]}
                fold_results=[]
                for fold in range(protocol["outer_folds"]):
                    training,assessment=np.flatnonzero(folds!=fold),np.flatnonzero(folds==fold)
                    fitted={}
                    fold_result={"fold":fold,"samples":len(assessment),"failures":int(y[assessment].sum()),"metrics":{}}
                    def evaluate(name,x):
                        model=select_linear(x,y,training,inner_assignments[fold],protocol["regularization_C"],protocol["fold_seed"],deadline)
                        margins=model.margins(x[assessment])
                        predictions[name][assessment]=margins
                        probability=expit(margins)
                        fold_result["metrics"][name]={"auroc":float(roc_auc_score(y[assessment],margins)),"average_precision":float(average_precision_score(y[assessment],margins)),"uncalibrated_brier":float(brier_score_loss(y[assessment],probability)),"C":model.C,"inner_log_loss":model.validation_loss}
                        np.savez_compressed(destination/f"level-{level}-fold-{fold}-{name}.npz",mean=model.scaler.mean_,scale=model.scaler.scale_,coef=model.model.coef_,intercept=model.model.intercept_)
                        return model
                    for name,x in base.items():
                        fitted[name]=evaluate(name,x)
                    cheap=min(protocol["cheap_controls"],key=lambda name:(fitted[name].validation_loss,name))
                    predictions["selected_cheap"][assessment]=predictions[cheap][assessment]
                    fold_result["selected_cheap_family"]=cheap
                    fold_result["metrics"]["selected_cheap"]=dict(fold_result["metrics"][cheap])
                    for label,features in (("mean",base["mean_only"]),("row",base["row_only"]),("cell",base["cell_only"])):
                        evaluate(f"selected_cheap_{label}",np.concatenate((base[cheap],features),axis=1))
                    prevalence=float(y[training].mean())
                    predictions["prevalence"][assessment]=np.log(prevalence/(1-prevalence))
                    fold_result["metrics"]["prevalence"]={"auroc":.5,"average_precision":float(y[assessment].mean()),"uncalibrated_brier":float(brier_score_loss(y[assessment],np.full(len(assessment),prevalence))),"C":None,"inner_log_loss":None}
                    fold_results.append(fold_result)
                    print(f"Evaluated level {level}, outer fold {fold+1}/{protocol['outer_folds']}",flush=True)
                if any(not np.isfinite(values).all() for values in predictions.values()):
                    raise ValueError("Missing/nonfinite out-of-fold predictions")
                weights=[fold["samples"] for fold in fold_results]
                summary={name:{metric:float(np.average([fold["metrics"][name][metric] for fold in fold_results],weights=weights)) for metric in ("auroc","average_precision","uncalibrated_brier")} for name in predictions}
                for name in predictions:
                    summary[name]["pooled_oof_auroc_secondary"]=float(roc_auc_score(y,predictions[name]))
                intervals=paired_fold_intervals(y,predictions,groups,folds,replicates=protocol["bootstrap_replicates"],seed=protocol["bootstrap_seed"],coverage=protocol["primary_interval_coverage"])
                comparisons={}
                for name in ("selected_cheap_row","selected_cheap_cell"):
                    lift=summary[name]["auroc"]-summary["selected_cheap"]["auroc"]
                    mean_lift=summary[name]["auroc"]-summary["selected_cheap_mean"]["auroc"]
                    positive=sum(fold["metrics"][name]["auroc"]>fold["metrics"]["selected_cheap"]["auroc"] for fold in fold_results)
                    candidate=summary[name]["auroc"]>=protocol["candidate_minimum_auroc"] and lift>=protocol["candidate_minimum_auroc_lift"] and mean_lift>=protocol["candidate_minimum_auroc_lift"] and intervals[name]["interval"][0]>0 and positive>=protocol["candidate_minimum_positive_folds"]
                    comparisons[name]={"auroc_lift_over_cheap":lift,"auroc_lift_over_mean":mean_lift,"positive_folds":positive,"interval":intervals[name],"exploratory_candidate":bool(candidate),"promotion_gate_passed":False}
                results.append({"level":level,"primary":level==protocol["primary_level"],"metrics":summary,"fold_results":fold_results,"comparisons":comparisons})
                np.savez_compressed(destination/f"level-{level}-out-of-fold.npz",y=y,folds=folds,puzzle_ids=np.asarray(keys),groups=groups,**predictions)
        if audit["parent_sha256"] != {name:sha256_file(root/name) for name in audit["parent_sha256"]}:
            raise ValueError("Original protected evidence changed")
        manifest.update(status="passed",results=results,fitting_wall_seconds=time.perf_counter()-started,original_artifacts_unchanged=True,promotion_gate_passed=False,conclusion="Bounded exploratory study completed. No fresh independent hard-Sudoku confirmation split is available in the checked official release; M4-M7 remain gated.")
        save_manifest(root,manifest)
        return write_followup_report(root,manifest)
    except Exception as error:
        manifest.update(status="failed",error=f"{type(error).__name__}: {error}")
        save_manifest(root,manifest)
        raise


def write_followup_report(root,manifest):
    protocol=manifest["configuration"]["protocol"]
    lines=["# Bounded M3 spatial follow-up", "",f"Run `{manifest['run_id']}`; complete provenance in `results/manifests/{manifest['run_id']}.json`.","",f"Exploratory development-only evaluation on {manifest['development_puzzles']} puzzles ({manifest['development_failures']} failures). All {manifest['excluded_original_test_puzzles']} original test identities were excluded from feature capture and fitting. No fresh test result is claimed.","", "Exactly two frozen spatial variants were evaluated: row means projected to 256 dimensions and all cell-position latents projected to 256 dimensions. Projection signs/seeds are fixed without labels. Eight row-separator positions are excluded from spatial variants; the original 256-dimensional global mean is retained as a baseline. Every reconstructed current board and global mean matches the audited parent data.","", "Four grouped outer folds assess the method. Two grouped inner folds select regularization and the cheap baseline family using log loss. Scaling fits only inner/outer training rows. Cheap-family selection never uses its outer assessment labels. Limited digit-renaming/transpose equivalence is grouped; full Sudoku symmetry equivalence remains unaudited.","", "AUROC below is the sample-weighted mean of outer-fold AUROCs; pooled OOF AUROC is secondary in the manifest. New discrimination uses raw margins, without a calibration fit or sign inversion. Brier scores use uncalibrated logistic probabilities. This is exploratory reuse of exposed data; cross-validation does not restore fresh confirmation."]
    for result in manifest["results"]:
        lines += ["",f"## Level {result['level']} — {'primary' if result['primary'] else 'exploratory secondary'}", "", "| Model | Mean outer AUROC | Mean outer AP | Uncalibrated Brier |", "|---|---:|---:|---:|"]
        lines += [f"| {name} | {m['auroc']:.4f} | {m['average_precision']:.4f} | {m['uncalibrated_brier']:.4f} |" for name,m in result["metrics"].items()]
        lines += ["", "| Spatial addition | Lift over selected cheap | Lift over mean addition | Positive folds | 97.5% paired interval vs cheap | Candidate criterion |", "|---|---:|---:|---:|---|---|"]
        for name,c in result["comparisons"].items():
            bounds=c["interval"]["interval"]
            lines.append(f"| {name} | {c['auroc_lift_over_cheap']:.4f} | {c['auroc_lift_over_mean']:.4f} | {c['positive_folds']}/4 | [{bounds[0]:.4f}, {bounds[1]:.4f}] | {'met, requires fresh confirmation' if c['exploratory_candidate'] else 'not met'} |")
    lines += ["", "## Decision and limits", "",f"Candidate criteria were fixed in `{manifest['configuration']['protocol'] and 'configs/m3_followup.json'}`: AUROC at least {protocol['candidate_minimum_auroc']}, lift at least {protocol['candidate_minimum_auroc_lift']} over both selected cheap and mean-addition controls, positive lift in at least three folds, and paired interval lower bound above zero. Primary 97.5% intervals account for two declared primary spatial comparisons by a Bonferroni-style coverage choice; secondary-level results are exploratory. Bootstrap resamples groups within outer assessment folds and does not refit models, so it does not capture all fitting/selection uncertainty.", "", "The checked official hard-Sudoku release has only the same puzzle and solution files already evaluated. A resplit, digit renaming, or transpose does not create fresh confirmation. No paid compute, new foundation model, branching, policy controller, natural-language extension or viewer was used. Later milestones remain gated regardless of exploratory scores.", "",f"Offline prefix capture took {manifest['feature_capture']['capture_wall_seconds']:.1f} seconds; CPU fitting/evaluation took {manifest['fitting_wall_seconds']:.1f} seconds. These are experimental job costs, not an online speedup or monitoring-overhead comparison. Original protected artifacts were unchanged.", ""]
    target=root/"results/reports"/f"{manifest['run_id']}.md"
    target.write_text("\n".join(lines),encoding="utf-8")
    return target
