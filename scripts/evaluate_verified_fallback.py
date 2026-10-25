"""Validate the practical exact fallback on exposed development records only."""
from collections import Counter
import json
from pathlib import Path
import time

from concept_firewall.artifacts import sha256_file
from concept_firewall.diagnostics import independent_inspection
from concept_firewall.provenance import source_hash
from concept_firewall.verified_solver import verified_completion
from concept_firewall.v2_protocol import write_json


def main():
    root = Path(__file__).resolve().parents[1]
    audit_path = root/'results/manifests/20261025T030920192150Z-v2-outcome-audit.json'
    audit = json.loads(audit_path.read_text())
    raw = root/audit['raw_file']
    if sha256_file(raw) != audit['raw_sha256']:
        raise ValueError('Existing development outcomes changed')
    rows = [json.loads(line) for line in raw.read_text().splitlines()]
    if len(rows) != 6400 or any(r['role'] not in ('train', 'validation', 'calibration') for r in rows):
        raise ValueError('Exposed development cohort required; no confirmation use')
    started = time.perf_counter()
    counts, nodes, solved, original = Counter(), 0, 0, 0
    decisions = []
    for row in rows:
        if time.perf_counter()-started > 120:
            raise RuntimeError('120-second engineering validation allowance exhausted')
        result = verified_completion(row['puzzle'], row['final_board'], node_limit=100000)
        valid = result.board is not None and independent_inspection(row['puzzle'], result.board)['valid']
        if valid != result.verified:
            raise ValueError('Independent verifier disagrees with fallback')
        original += int(row['final_valid'])
        solved += int(valid)
        nodes += result.search_nodes
        counts[result.status] += 1
        decisions.append({'puzzle_id': row['puzzle_id'], 'board': result.board,
                          'status': result.status, 'search_nodes': result.search_nodes})
    elapsed = time.perf_counter()-started
    destination = root/'results/continuation/raw/verified_fallback.jsonl'
    if destination.exists():
        raise ValueError('Engineering result already retained; refusing overwrite')
    payload = ''.join(json.dumps(r, separators=(',', ':'))+'\n' for r in decisions).encode()
    destination.write_bytes(payload)
    record = {'status': 'passed' if solved == len(rows) else 'partial',
              'scope': 'Engineering validation on already exposed V2 train/validation/calibration inputs; no learned recovery or independent confirmation claim',
              'source_sha256': source_hash(root), 'script_sha256': sha256_file(Path(__file__)),
              'parent_audit_sha256': sha256_file(audit_path), 'parent_raw_sha256': audit['raw_sha256'],
              'puzzles': len(rows), 'original_solved': original, 'combined_verified_solved': solved,
              'outcomes': dict(counts), 'search_nodes': nodes, 'node_limit_per_puzzle': 100000,
              'validation_wall_seconds': elapsed, 'timing_scope': 'CPU fallback, exact verification and host audit/record assembly; excludes the already completed NCM generation',
              'new_model_calls': 0, 'new_fits': 0, 'confirmation_accessed': False,
              'raw_file': destination.relative_to(root).as_posix(), 'raw_sha256': sha256_file(destination), 'raw_bytes': len(payload)}
    write_json(root/'results/continuation/verified_fallback.json', record)
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
