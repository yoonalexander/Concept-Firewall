"""Observe one real generator step without replacing its sampling algorithm."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable


CONFIDENCE_NAMES = ("mean_normalized_entropy", "max_normalized_entropy",
                    "mean_top_two_probability_margin", "minimum_top_two_probability_margin",
                    "mean_selected_code_log_probability", "minimum_selected_code_log_probability")


@dataclass(frozen=True)
class GeneratorObservation:
    level: int
    codes_prefix_by_sample: tuple[tuple[tuple[int, ...], ...], ...]
    activation_by_sample: tuple[tuple[float, ...], ...]
    confidence_by_sample: tuple[tuple[float, ...], ...]


def confidence_summary(log_probabilities, selected_codes):
    import torch
    if log_probabilities.ndim != 3 or selected_codes.shape != log_probabilities.shape[:2] or log_probabilities.shape[-1] < 2:
        raise ValueError("Confidence tensors have unexpected shape")
    if not torch.isfinite(log_probabilities).all():
        raise ValueError("Non-finite confidence scores")
    probabilities = log_probabilities.exp()
    entropy = -(probabilities*log_probabilities).sum(-1)/math.log(probabilities.shape[-1])
    top = probabilities.topk(2, dim=-1).values
    margin = top[...,0]-top[...,1]
    chosen = log_probabilities.gather(-1,selected_codes.unsqueeze(-1)).squeeze(-1)
    return torch.stack((entropy.mean(1),entropy.max(1).values,margin.mean(1),margin.min(1).values,
                        chosen.mean(1),chosen.min(1).values),dim=1)


class GeneratorObserver:
    def __init__(self, adapter, *, level=6, projection_dimension=256, seed=20261024):
        import numpy as np
        import torch
        self.adapter, self.level = adapter, level
        model = adapter.generator
        if not 1 <= level <= len(adapter.levels):
            raise ValueError("Observation level outside hierarchy")
        if not model.query_level0 or model.l0_ar or adapter.generation_settings.cfg_scale != 0:
            raise ValueError("Observation supports the frozen parallel-level, non-CFG path only")
        if projection_dimension < 1 or seed < 0:
            raise ValueError("Invalid fixed projection")
        self.head = model.lm_heads[level-1]
        width = int(model.config.n_embd) if hasattr(model,"config") else int(model.transformer.ln_f.weight.shape[0])
        rng = np.random.default_rng(seed)  # Never touches the generator's Torch RNG.
        signs = rng.integers(0,2,size=(adapter.levels[level-1]*width,projection_dimension),dtype=np.int8)
        projection=(signs.astype(np.float32)*2-1)/math.sqrt(projection_dimension)
        self.projection = torch.from_numpy(projection).to(adapter.device)
        self.projection_bytes = projection.tobytes()

    def generate(self, context, on_observation: Callable[[GeneratorObservation],None] | None = None):
        import torch
        model = self.adapter.generator
        if "_sample_level" in model.__dict__:
            raise ValueError("Generator is already observed or sampling is overridden")
        original_sample = model._sample_level
        prefixes, observations = [], []
        captured = None

        def head_hook(_module, inputs, logits):
            nonlocal captured
            if len(prefixes) != self.level-1 or captured is not None:
                raise ValueError("Unexpected observation head order or repeated head call")
            hidden = inputs[0].detach()
            if hidden.ndim != 3 or hidden.shape[1] != self.adapter.levels[self.level-1] or hidden.flatten(1).shape[1] != self.projection.shape[0]:
                raise ValueError("Head input includes unexpected positions/width")
            if not torch.isfinite(hidden).all() or not torch.isfinite(logits).all():
                raise ValueError("Non-finite activation/logits")
            captured=(hidden.float().flatten(1) @ self.projection,
                      torch.log_softmax(logits.detach().float(),dim=-1))
            # Returning None leaves the head's actual output unmodified.

        def observed_sample(logits, *args, **kwargs):
            nonlocal captured
            selected = original_sample(logits,*args,**kwargs)
            index = len(prefixes)
            if index >= len(self.adapter.levels) or selected.shape != (context.shape[0],self.adapter.levels[index]):
                raise ValueError("Unexpected sampling order/shape")
            if index < self.level:
                prefixes.append(selected.detach().clone())
            else:
                prefixes.append(None)
            if index+1 == self.level:
                if captured is None:
                    raise ValueError("Sampler reached observation boundary without head scores")
                projected, log_probabilities = captured
                confidence = confidence_summary(log_probabilities,selected)
                if not torch.isfinite(projected).all() or not torch.isfinite(confidence).all():
                    raise ValueError("Non-finite exported features")
                batch_prefix = [x.cpu().tolist() for x in prefixes]
                observation = GeneratorObservation(self.level,
                    tuple(tuple(tuple(rows[b]) for rows in batch_prefix) for b in range(context.shape[0])),
                    tuple(tuple(float(v) for v in row) for row in projected.cpu().tolist()),
                    tuple(tuple(float(v) for v in row) for row in confidence.cpu().tolist()))
                observations.append(observation)
                captured = None
                if on_observation:
                    on_observation(observation)  # Called before the generator can compute the next level.
            return selected

        handle = self.head.register_forward_hook(head_hook)
        model._sample_level = observed_sample
        try:
            result = self.adapter.generate(context)
            if len(prefixes) != len(self.adapter.levels) or len(observations) != 1:
                raise ValueError("Incomplete observed generation")
            return result, observations[0]
        finally:
            handle.remove()
            del model._sample_level


def run_pilot(root, protocol_path):
    import hashlib
    import io
    import json
    import numpy as np
    import torch
    from .diagnostics import load_puzzles
    from .provenance import new_manifest, require_upstream, save_manifest
    from .upstream_adapter import NCMAdapter
    from .v2_protocol import BudgetLedger, LEDGER, require_contract
    from .artifacts import sha256_file, verified_artifacts

    p,contract = require_contract(root,protocol_path)
    require_upstream(root)
    if verified_artifacts(root) != contract["artifact_sha256"]:
        raise ValueError("Official artifact hashes differ from frozen contract")
    if sha256_file(root/p["legacy"]["splits"]) != contract["legacy_splits_sha256"]:
        raise ValueError("Legacy splits changed")
    if not torch.cuda.is_available():
        raise RuntimeError("V2 pilot requires existing local CUDA GPU; no fallback")
    ledger=BudgetLedger(root/LEDGER,contract["protocol_sha256"],p["limits"])
    manifest=new_manifest(root,"v2-pilot",{"protocol_sha256":contract["protocol_sha256"],"scope":"operational equivalence, not detector fitting"})
    path=save_manifest(root,manifest)
    try:
        with ledger.operation("load existing checkpoints",timed_resource="gpu_seconds"):
            adapter=NCMAdapter.load(root/"third_party/ncm",root/"third_party/ncm/config/eval/sudoku-hard.yaml",root/"artifacts/sudoku-hard",device="cuda")
            observer=GeneratorObserver(adapter,level=p["primary_level"],projection_dimension=p["measurement"]["projection_dimension"],seed=p["measurement"]["projection_seed"])
            torch.cuda.synchronize()
        contexts,puzzles=load_puzzles(root)
        mapping=dict(zip(puzzles,contexts))
        ids=contract["pilot_puzzle_ids"]
        hidden,confidence,prefixes=[],[],[]
        code_hash=hashlib.sha256()
        callback_count=0
        for start in range(0,len(ids),p["batch_size"]):
            selected=ids[start:start+p["batch_size"]]
            with ledger.operation(f"pilot batch {start}",timed_resource="gpu_seconds",pilot_puzzles=len(selected)):
                context=adapter.prepare_context([mapping[key] for key in selected])
                control=adapter.generate(context)
                seen=[]
                observed,observation=observer.generate(context,seen.append)
                if not torch.equal(control,observed) or adapter.decode_final(control) != adapter.decode_final(observed):
                    raise ValueError("Observed generator changed codes or final boards")
                if seen != [observation]:
                    raise ValueError("Boundary callback was not delivered exactly once")
                exported=np.asarray([sum((list(c) for c in row),[]) for row in observation.codes_prefix_by_sample],dtype=np.int64)
                if not np.array_equal(exported,control[:,:sum(adapter.levels[:p["primary_level"]])].cpu().numpy()):
                    raise ValueError("Exported prefix differs from actual generated prefix")
                callback_count+=1
                code_hash.update(control.cpu().numpy().tobytes())
                hidden.extend(observation.activation_by_sample)
                confidence.extend(observation.confidence_by_sample)
                prefixes.extend(exported)
                torch.cuda.synchronize()
            print(f"Verified observed/control equivalence: {start+len(selected)}/{len(ids)} pilot puzzles",flush=True)
        payload=io.BytesIO()
        np.savez_compressed(payload,puzzle_ids=np.asarray(ids),activation=np.asarray(hidden,dtype=np.float32),
                            confidence=np.asarray(confidence,dtype=np.float32),codes_prefix=np.asarray(prefixes,dtype=np.int64))
        feature_path=root/"results/v2/features"/manifest["run_id"]/"pilot.npz"
        with ledger.operation("retain bounded pilot summaries",feature_bytes=len(payload.getvalue())):
            feature_path.parent.mkdir(parents=True,exist_ok=True)
            with feature_path.open("xb") as output:
                output.write(payload.getvalue())
        manifest.update(status="passed",puzzles=len(ids),all_codes_equal=True,all_final_boards_equal=True,
                        all_prefixes_equal=True,callback_batches=callback_count,observation_level=p["primary_level"],
                        feature_file=feature_path.relative_to(root).as_posix(),features_sha256=sha256_file(feature_path),
                        projection_sha256=hashlib.sha256(observer.projection_bytes).hexdigest(),
                        generated_codes_sha256=code_hash.hexdigest(),probe_fits=0,new_confirmation_data=False,
                        budget=ledger.snapshot())
    except BaseException as error:
        manifest.update(status="failed",error=f"{type(error).__name__}: {error}",budget=ledger.snapshot())
        save_manifest(root,manifest)
        raise
    return save_manifest(root,manifest)
