"""Retain raw outcomes and independently replay V2 labels; no fits or confirmation."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import sys

import numpy as np
import torch

from concept_firewall.artifacts import sha256_file, verified_artifacts
from concept_firewall.diagnostics import independent_inspection
from concept_firewall.probes import feature_vector
from concept_firewall.provenance import new_manifest, require_upstream, save_manifest
from concept_firewall.representations import extract_features
from concept_firewall.schema import LevelState
from concept_firewall.spatial import reconstruct_prefix
from concept_firewall.upstream_adapter import NCMAdapter
from concept_firewall.v2_data import load_partition
from concept_firewall.v2_protocol import BudgetLedger, LEDGER, require_contract
from concept_firewall.v2_training import encode_puzzle


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    parent=args.manifest.resolve()
    original_hash=sha256_file(parent)
    original=json.loads(parent.read_text(encoding='utf-8'))
    p,contract=require_contract(root,root/'configs/v2_study.json')
    if original['status']!='passed' or original['configuration']['protocol_sha256']!=contract['protocol_sha256']:
        raise ValueError('Completed frozen development run required')
    require_upstream(root)
    if verified_artifacts(root)!=contract['artifact_sha256']:
        raise ValueError('Official artifacts changed')
    ledger=BudgetLedger(root/LEDGER,contract['protocol_sha256'],p['limits'])
    manifest=new_manifest(root,'v2-outcome-audit',{'parent_manifest':str(parent.relative_to(root)),
        'parent_sha256':original_hash,'script_sha256':sha256_file(Path(__file__)),'confirmation_accessed':False})
    manifest['command']=[sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]]
    save_manifest(root,manifest)
    payload=io.StringIO()
    count=0
    try:
        with ledger.operation('load audit checkpoints',timed_resource='gpu_seconds'):
            adapter=NCMAdapter.load(root/'third_party/ncm',root/'third_party/ncm/config/eval/sudoku-hard.yaml',root/'artifacts/sudoku-hard',device='cuda')
            torch.cuda.synchronize()
        for role in ('train','validation','calibration'):
            rows=load_partition(root,role)
            capture=original['captures'][role]
            if sha256_file(root/capture['file'])!=capture['sha256']:
                raise ValueError('Recorded feature file changed')
            with np.load(root/capture['file'],allow_pickle=False) as data:
                expected={key:data[key] for key in ('y','decoded','input_decoded','puzzle_ids')}
            for start in range(0,len(rows),p['batch_size']):
                batch=rows[start:start+p['batch_size']]
                with ledger.operation(f'independent {role} audit {start}',timed_resource='gpu_seconds'):
                    with torch.no_grad():
                        codes=adapter.generate(adapter.prepare_context([encode_puzzle(row['puzzle']) for row in batch]))
                        final=adapter.decode_final(codes)
                        current=adapter._decode_latent(reconstruct_prefix(adapter.tokenizer.vqvae.vq,codes[:,:sum(adapter.levels[:6])],6))
                    raw_codes=codes.cpu().tolist()
                    for index,row in enumerate(batch):
                        at=start+index
                        if row['puzzle_id']!=expected['puzzle_ids'][at]:
                            raise ValueError('Assessment identity order changed')
                        outcome=independent_inspection(row['puzzle'],final[index])
                        if int(not outcome['valid'])!=expected['y'][at]:
                            raise ValueError('Independent label replay differs from recorded outcome')
                        prefix=[]; offset=0
                        for length in adapter.levels[:6]:
                            prefix.append(tuple(raw_codes[index][offset:offset+length])); offset+=length
                        state=LevelState(manifest['run_id'],row['puzzle_id'],row['puzzle_id'],6,tuple(prefix),current[index])
                        features=extract_features(state,row['puzzle'])
                        for family in ('decoded','input_decoded'):
                            if not np.array_equal(feature_vector(features,state.codes_prefix,family)[1],expected[family][at]):
                                raise ValueError('Current-prefix feature replay differs')
                        payload.write(json.dumps({'role':role,'puzzle_id':row['puzzle_id'],'puzzle':row['puzzle'],
                            'current_board':current[index],'final_board':final[index],'final_valid':outcome['valid'],
                            'codes':raw_codes[index]},separators=(',',':'))+'\n')
                        count+=1
                    torch.cuda.synchronize()
            print(f'Independently checked {role}: {len(rows)} outcomes and current-board features',flush=True)
        raw=payload.getvalue().encode('utf-8')
        target=root/'results/v2/raw'/manifest['run_id']/'outcomes.jsonl'
        with ledger.operation('retain independent raw outcomes',feature_bytes=len(raw)):
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as stream:
                stream.write(raw)
        if sha256_file(parent)!=original_hash:
            raise ValueError('Original study was modified')
        manifest.update(status='passed',outcomes_checked=count,current_features_checked=count,
                        raw_file=target.relative_to(root).as_posix(),raw_sha256=sha256_file(target),raw_bytes=len(raw),
                        original_study_unchanged=True,confirmation_accessed=False,new_fits=0,budget=ledger.snapshot())
    except BaseException as error:
        manifest.update(status='failed',error=f'{type(error).__name__}: {error}',budget=ledger.snapshot())
        save_manifest(root,manifest)
        raise
    print(save_manifest(root,manifest))


if __name__=='__main__':
    main()
