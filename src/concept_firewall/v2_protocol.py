"""Frozen V2 study contract and crash-visible, single-writer budget accounting."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time

from .artifacts import sha256_file, verified_artifacts
from .provenance import new_manifest, require_upstream, save_manifest


CONTRACT = "results/v2/contracts/generator-signals-v1.json"
LEDGER = "results/v2/runtime/generator-signals-v1.json"


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".pending")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_protocol(path: Path) -> dict:
    p = json.loads(path.read_text(encoding="utf-8"))
    if p.get("study_id") != "generator-signals-v1" or p.get("schema_version") != 1:
        raise ValueError("Unknown V2 study/schema")
    if p.get("primary_level") != 6 or p["measurement"]["observed_levels"] != [6]:
        raise ValueError("V2 has exactly one prespecified observation level")
    if p["measurement"]["projection_dimension"] != 256 or p["measurement"]["confidence_temperature"] != 1:
        raise ValueError("Unexpected measurement specification")
    if sum(p["new_data"]["partitions"].values()) != p["new_data"]["planned_total"]:
        raise ValueError("New-data partition sizes disagree")
    account = p["fitting"]["fit_accounting"]
    if sum(v for k,v in account.items() if k != "total") != account["total"] or account["total"] != p["limits"]["fit_jobs"]:
        raise ValueError("Fit-job accounting exceeds or disagrees with budget")
    for key,value in p["limits"].items():
        if type(value) not in (int,float) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"Invalid positive resource cap: {key}")
    return p


def require_contract(root: Path, protocol_path: Path) -> tuple[dict, dict]:
    p = load_protocol(protocol_path)
    contract = json.loads((root / CONTRACT).read_text(encoding="utf-8"))
    if contract["status"] != "frozen" or contract["protocol_sha256"] != sha256_file(protocol_path):
        raise ValueError("Protocol changed or contract is not frozen; create a separately scoped study")
    return p, contract


class BudgetExceeded(RuntimeError):
    pass


class BudgetLedger:
    def __init__(self, path: Path, protocol_digest: str, limits: dict):
        self.path, self.digest, self.limits = path, protocol_digest, limits
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._locked():
            if not path.exists():
                write_json(path, {"protocol_sha256": protocol_digest, "limits": limits,
                                  "used": {k: 0 for k in limits}, "active": None, "events": []})
            self._read()

    def _read(self):
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if value["protocol_sha256"] != self.digest or value["limits"] != self.limits:
            raise ValueError("Ledger does not belong to frozen protocol/budget")
        if set(value["used"]) != set(self.limits) or any(not math.isfinite(v) or v < 0 for v in value["used"].values()):
            raise ValueError("Invalid ledger resource counters")
        return value

    @contextmanager
    def _locked(self):
        lock = self.path.with_suffix(".lock")
        handle = lock.open("x")
        try:
            yield
        finally:
            handle.close()
            lock.unlink()

    def snapshot(self):
        return self._read()

    @contextmanager
    def operation(self, name: str, *, timed_resource: str | None = None, **charges):
        if timed_resource is not None and timed_resource not in ("gpu_seconds", "cpu_fit_seconds"):
            raise ValueError("Unexpected time resource")
        for key,value in charges.items():
            if key not in self.limits or type(value) not in (int,float) or not math.isfinite(value) or value < 0:
                raise ValueError("Invalid budget charge")
        with self._locked():
            state = self._read()
            if state["active"] is not None:
                raise BudgetExceeded("Interrupted/running operation exists; ledger fails closed")
            if any(state["used"][k] > cap for k,cap in self.limits.items()):
                raise BudgetExceeded("A previous operation exhausted the study")
            if timed_resource and state["used"][timed_resource] >= self.limits[timed_resource]:
                raise BudgetExceeded("Time allowance exhausted")
            if any(state["used"][k]+v > self.limits[k] for k,v in charges.items()):
                raise BudgetExceeded("Requested operation would exceed resource allowance")
            for key,value in charges.items():
                state["used"][key] += value
            state["active"] = {"name": name, "timed_resource": timed_resource, "charges": charges,
                               "started_utc": datetime.now(timezone.utc).isoformat()}
            write_json(self.path,state)
        start, outcome = time.perf_counter(), "passed"
        try:
            yield
        except BaseException:
            outcome = "failed"
            raise
        finally:
            elapsed = time.perf_counter()-start
            with self._locked():
                state = self._read()
                event = state["active"]
                if timed_resource:
                    state["used"][timed_resource] += elapsed
                exhausted = any(state["used"][k] > cap for k,cap in self.limits.items())
                event.update(status="exhausted" if exhausted else outcome, elapsed_seconds=elapsed)
                state["events"].append(event)
                state["active"] = None
                write_json(self.path,state)
            if exhausted:
                raise BudgetExceeded("Indivisible operation exceeded allowance; study exhausted")


def prospective_precision(protocol: dict) -> dict:
    """CPU-only Monte Carlo planning; no puzzle/model outcomes are loaded."""
    import numpy as np
    q = protocol["prospective"]
    rng = np.random.default_rng(q["seed"])
    n, repeats = q["confirmation_size"], q["replicates"]
    failures = rng.binomial(n,q["legacy_failure_rate"],repeats)
    both = q["joint_true_positive_probability_given_failure"]
    probabilities = [both,q["candidate_recall"]-both,q["control_recall"]-both,
                     1-q["candidate_recall"]-q["control_recall"]+both]
    passed=[]
    for failure in failures:
        counts = rng.multinomial(int(failure),probabilities)
        difference = (counts[1]-counts[2])/max(1,int(failure))
        variance = (counts[1]+counts[2])/max(1,int(failure))-difference**2
        lower = difference-1.959963984540054*math.sqrt(max(0,variance)/max(1,int(failure)))
        passed.append(bool(failure >= protocol["new_data"]["minimum_confirmation_failures"] and
                           difference >= protocol["confirmation"]["minimum_recall_lift"] and lower > 0))
    fpr_scenarios={}
    successes=n-failures
    z=1.6448536269514722
    for actual in q["fpr_scenarios"]:
        alarms=rng.binomial(successes,actual)
        rates=alarms/successes
        upper=(rates+z*z/(2*successes)+z*np.sqrt(rates*(1-rates)/successes+z*z/(4*successes**2)))/(1+z*z/successes)
        fpr_scenarios[str(actual)]={"fpr_gate_pass_fraction":float(np.mean((rates <= .05)&(upper <= .08))),
                                    "mean_one_sided_upper_bound":float(upper.mean())}
    return {"expected_failures": n*q["legacy_failure_rate"],"confirmation_size": n,
            "minimum_failure_count_probability":float(np.mean(failures >= protocol["new_data"]["minimum_confirmation_failures"])),
            "paired_lift_gate_pass_fraction_normal_approximation":float(np.mean(passed)),
            "fpr_scenarios":fpr_scenarios,
            "limits":"Conditional design sensitivity only; no model scores; normal lift approximation is not the final paired bootstrap and excludes the absolute-recall gate and threshold-estimation/selection uncertainty. Not joint study power."}


def freeze_contract(root: Path, protocol_path: Path) -> Path:
    p = load_protocol(protocol_path)
    if (root / CONTRACT).exists():
        require_contract(root,protocol_path)
        return root / CONTRACT
    require_upstream(root)
    artifacts=verified_artifacts(root)
    splits_path=root/p["legacy"]["splits"]
    splits=json.loads(splits_path.read_text(encoding="utf-8"))
    if any(set(splits[a]) & set(splits[b]) for a in splits for b in splits if a != b):
        raise ValueError("Legacy partitions overlap")
    pilot=sorted(splits["train"])[:p["limits"]["pilot_puzzles"]]
    plan=prospective_precision(p)
    manifest=new_manifest(root,"v2-contract",{"protocol":p,"protocol_sha256":sha256_file(protocol_path)})
    manifest.update(status="passed",prospective=plan,legacy_splits_sha256=sha256_file(splits_path),
                    artifact_sha256=artifacts,pilot_puzzle_ids=pilot,
                    model_runs=0,probe_fits=0,new_data_ready=False)
    path=save_manifest(root,manifest)
    contract={"status":"frozen","study_id":p["study_id"],"protocol_sha256":sha256_file(protocol_path),
              "legacy_splits_sha256":sha256_file(splits_path),"pilot_puzzle_ids":pilot,
              "artifact_sha256":artifacts,"contract_manifest":path.relative_to(root).as_posix()}
    write_json(root/CONTRACT,contract)
    BudgetLedger(root/LEDGER,contract["protocol_sha256"],p["limits"])
    return path
