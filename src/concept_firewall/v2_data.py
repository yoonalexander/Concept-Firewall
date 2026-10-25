"""Outcome-blind Sudoku source validation and conservative symmetry grouping."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import time

from .artifacts import sha256_file
from .diagnostics import independent_cells, load_puzzles
from .provenance import new_manifest, save_manifest
from .v2_protocol import BudgetLedger, LEDGER, require_contract, write_json

SOURCE_REVISION = "d8c8ebaee0c08c412cfba96af1923dfa61c83317"
DATA_MANIFEST = "results/v2/contracts/generator-signals-v1-data.json"


def symmetry_group(puzzle: str) -> str:
    """Isomorphic clue graphs have identical hashes; collisions over-group safely.

    Row/column and band/stack colors are shared, allowing transposition. Symbols
    are unlabelled. Standard digit, within-band row, band, column/stack, and
    transpose symmetries therefore cannot create different partition groups.
    This is an invariant, not a claim of complete canonicalization: unrelated
    puzzles may merge, which conservatively removes data rather than leaks it.
    """
    import networkx as nx
    cells = independent_cells(puzzle)
    if cells is None:
        raise ValueError("Malformed puzzle")
    graph=nx.Graph()
    for index,value in enumerate(cells):
        row,column=divmod(index,9)
        cell=f"cell{index}"
        graph.add_node(cell,kind="cell")
        for unit in (f"row{row}",f"column{column}"):
            graph.add_node(unit,kind="line")
            graph.add_edge(cell,unit)
        box=f"box{row//3}-{column//3}"
        graph.add_node(box,kind="box")
        graph.add_edge(cell,box)
        if value:
            symbol=f"symbol{value}"
            graph.add_node(symbol,kind="symbol")
            graph.add_edge(cell,symbol)
    for kind in ("row","column"):
        for index in range(9):
            parent=f"{kind}group{index//3}"
            graph.add_node(parent,kind="line_group")
            graph.add_edge(f"{kind}{index}",parent)
    return nx.weisfeiler_lehman_graph_hash(graph,node_attr="kind",iterations=6,digest_size=32)


def unique_solution(puzzle: str, *, max_nodes=100000) -> tuple[bool,int]:
    """Independent bit-mask MRV enumeration, stopping at two solutions."""
    parsed=independent_cells(puzzle)
    if parsed is None:
        return False,0
    cells=list(parsed)
    rows,columns,boxes=[0]*9,[0]*9,[0]*9
    for index,value in enumerate(cells):
        if not value:
            continue
        r,c=divmod(index,9)
        b=r//3*3+c//3
        mask=1<<value
        if (rows[r]|columns[c]|boxes[b])&mask:
            return False,0
        rows[r]|=mask
        columns[c]|=mask
        boxes[b]|=mask
    nodes=0
    def search():
        nonlocal nodes
        nodes+=1
        if nodes > max_nodes:
            raise RuntimeError("Uniqueness validation node cap exhausted")
        chosen,choices=-1,0
        smallest=10
        for index,value in enumerate(cells):
            if value:
                continue
            r,c=divmod(index,9)
            mask=1022 & ~(rows[r]|columns[c]|boxes[r//3*3+c//3])
            count=mask.bit_count()
            if count == 0:
                return 0
            if count < smallest:
                chosen,choices,smallest=index,mask,count
                if count == 1:
                    break
        if chosen < 0:
            return 1
        r,c=divmod(chosen,9)
        b=r//3*3+c//3
        total=0
        while choices:
            bit=choices & -choices
            choices-=bit
            cells[chosen]=bit.bit_length()-1
            rows[r]|=bit; columns[c]|=bit; boxes[b]|=bit
            total+=search()
            rows[r]^=bit; columns[c]^=bit; boxes[b]^=bit
            cells[chosen]=0
            if total >= 2:
                return 2
        return total
    return search()==1,nodes


def load_partition(root: Path, role: str, *, confirmation_authorized=False) -> list[dict]:
    if role not in ("train","validation","calibration","confirmation"):
        raise ValueError("Unknown data role")
    if role == "confirmation" and not confirmation_authorized:
        raise ValueError("Confirmation inputs are sealed until frozen-candidate evaluation")
    m=json.loads((root/DATA_MANIFEST).read_text(encoding="utf-8"))
    entry=m["partitions"][role]
    target=root/entry["file"]
    if sha256_file(target) != entry["sha256"]:
        raise ValueError("Partition content differs from frozen data manifest")
    rows=[json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
    if len(rows) != entry["puzzles"]:
        raise ValueError("Partition count changed")
    return rows


def restore_data(root: Path, source: Path) -> Path:
    """Rehydrate exactly the frozen inputs, without reselection or model calls."""
    m=json.loads((root/DATA_MANIFEST).read_text(encoding="utf-8"))
    raw=subprocess.check_output(["git","-C",str(source),"show",f"{m['source_revision']}:hard.txt"])
    if hashlib.sha256(raw).hexdigest() != m["source_blob_sha256"]["hard.txt"]:
        raise ValueError("Pinned source blob digest mismatch")
    wanted={key for part in m["partitions"].values() for key in part["puzzle_ids"]}
    values={}
    for line in raw.decode("ascii").splitlines():
        _,puzzle,rating=line.split()
        key=hashlib.sha256(puzzle.encode()).hexdigest()
        if key in wanted:
            values[key]=(puzzle,float(rating))
    if set(values) != wanted:
        raise ValueError("Frozen identities missing from source")
    pending=[]
    for role,entry in m["partitions"].items():
        rows=[{"puzzle_id":key,"group":group,"puzzle":values[key][0],"source_rating":values[key][1]}
              for key,group in zip(entry["puzzle_ids"],entry["groups"])]
        payload="".join(json.dumps(row,separators=(",",":"))+"\n" for row in rows).encode("utf-8")
        if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
            raise ValueError("Restored partition differs from frozen digest")
        target=root/entry["file"]
        if target.exists() and sha256_file(target) != entry["sha256"]:
            raise ValueError("Refusing conflicting existing partition")
        pending.append((target,payload))
    for target,payload in pending:
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open("xb") as stream:
                stream.write(payload)
    return root/DATA_MANIFEST


def prepare_data(root: Path, protocol_path: Path, source: Path) -> Path:
    import networkx
    p,contract=require_contract(root,protocol_path)
    if (root/DATA_MANIFEST).exists():
        raise ValueError("Data cohort already frozen; refusing reselection")
    revision=subprocess.check_output(["git","-C",str(source),"rev-parse","HEAD"],text=True).strip()
    if revision != SOURCE_REVISION:
        raise ValueError("Unexpected external source revision")
    # Read immutable Git blobs, unaffected by checkout line-ending conversion.
    blobs={name:subprocess.check_output(["git","-C",str(source),"show",f"{revision}:{name}"]) for name in ("hard.txt","README.md","LICENSE.txt")}
    if b"public domain" not in blobs["LICENSE.txt"]:
        raise ValueError("Expected source data dedication missing")
    manifest=new_manifest(root,"v2-data",{"protocol_sha256":contract["protocol_sha256"],
        "source_revision":revision,"selection":"hard.txt only; sort SHA256(study_id+puzzle_id), one per conservative group; no model outcomes",
        "validation_cap":9000,"uniqueness_node_cap":100000,"data_preparation_wall_cap_seconds":900,
        "networkx_version":networkx.__version__})
    path=save_manifest(root,manifest)
    ledger=BudgetLedger(root/LEDGER,contract["protocol_sha256"],p["limits"])
    start=time.perf_counter()
    try:
        _,legacy=load_puzzles(root)
        legacy_groups={symmetry_group(puzzle) for puzzle in legacy.values()}
        pool=[]
        for line in blobs["hard.txt"].decode("ascii").splitlines():
            fields=line.split()
            if len(fields)!=3 or len(fields[1]) != 81 or any(c not in "0123456789" for c in fields[1]):
                raise ValueError("Unexpected source row format")
            puzzle=fields[1]
            identity=hashlib.sha256(puzzle.encode()).hexdigest()
            order=hashlib.sha256((p["study_id"]+identity).encode()).hexdigest()
            pool.append((order,identity,puzzle,float(fields[2])))
        pool.sort()
        selected=[]
        seen=set(legacy_groups)
        rejected=Counter()
        checked=0
        for _,identity,puzzle,rating in pool:
            if time.perf_counter()-start > 900 or checked >= 9000:
                raise RuntimeError("Frozen data validation budget exhausted")
            checked+=1
            group=symmetry_group(puzzle)
            if group in seen:
                rejected["legacy_or_selected_group_overlap"]+=1
                continue
            valid,nodes=unique_solution(puzzle)
            if not valid:
                rejected["not_unique_or_inconsistent"]+=1
                continue
            seen.add(group)
            selected.append({"puzzle_id":identity,"group":group,"puzzle":puzzle,"source_rating":rating})
            if len(selected)%1000 == 0:
                print(f"Validated {len(selected)}/8000 independent project puzzle groups",flush=True)
            if len(selected)==p["new_data"]["planned_total"]:
                break
        if len(selected) != p["new_data"]["planned_total"]:
            raise ValueError("Insufficient eligible independent project groups")
        selected.sort(key=lambda row:hashlib.sha256(("partition:"+p["study_id"]+row["group"]).encode()).hexdigest())
        partitions={}
        offset=0
        with ledger.operation("freeze new puzzle cohort",new_puzzles=len(selected)):
            for role,count in p["new_data"]["partitions"].items():
                rows=selected[offset:offset+count]
                offset+=count
                target=root/"data/v2"/p["study_id"]/f"{role}.jsonl"
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open("x",encoding="utf-8",newline="\n") as stream:
                    for row in rows:
                        stream.write(json.dumps(row,separators=(",",":"))+"\n")
                partitions[role]={"puzzles":count,"file":target.relative_to(root).as_posix(),"sha256":sha256_file(target),
                                  "puzzle_ids":[row["puzzle_id"] for row in rows],"groups":[row["group"] for row in rows]}
        sources={name:hashlib.sha256(blob).hexdigest() for name,blob in blobs.items()}
        for name,blob in blobs.items():
            target=root/"data/v2/source"/name
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open("xb") as stream:
                stream.write(blob)
        m={"status":"eligible","study_id":p["study_id"],"protocol_sha256":contract["protocol_sha256"],
           "source":"https://github.com/grantm/sudoku-exchange-puzzle-bank", "source_revision":revision,
           "source_blob_sha256":sources,"license":"public-domain dedication in pinned LICENSE.txt",
           "partitions":partitions,"legacy_groups_excluded":len(legacy_groups),"rejections":dict(rejected),
           "validated_candidates":checked,"unique_solution_checked":len(selected),"model_outcomes_generated":0,
           "clue_count_histogram":dict(sorted(Counter(sum(c!='0' for c in row["puzzle"]) for row in selected).items())),
           "rating_range":[min(row["source_rating"] for row in selected),max(row["source_rating"] for row in selected)],
           "grouping":"6-iteration colored clue-graph WL invariant; standard Sudoku symmetries cannot split groups; non-equivalent collisions conservatively merge groups; not full canonicalization",
           "checkpoint_training_exposure":"unknown; fresh project confirmation only; no claim of training independence",
           "distribution":"Sudoku Exchange hard bucket, not a replication of official fixed-30-clue distribution"}
        write_json(root/DATA_MANIFEST,m)
        manifest.update(status="passed",data_manifest=DATA_MANIFEST,new_data_ready=True,puzzles=len(selected),
                        data_manifest_sha256=sha256_file(root/DATA_MANIFEST),elapsed_seconds=time.perf_counter()-start,
                        model_runs=0,probe_fits=0,budget=ledger.snapshot())
    except BaseException as error:
        manifest.update(status="failed",error=f"{type(error).__name__}: {error}",elapsed_seconds=time.perf_counter()-start,budget=ledger.snapshot())
        save_manifest(root,manifest)
        raise
    return save_manifest(root,manifest)
