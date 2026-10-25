"""Reuse the verified archive checks for the explicitly allowed V2 evidence paths."""
import argparse
import json
from pathlib import Path

from study_artifacts import pack, restore

PATHS=("data/v2/generator-signals-v1","results/v2/features","results/v2/models","results/v2/raw","results/v2/runtime")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('pack','restore'))
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--inventory',type=Path,default=Path('results/v2/contracts/v2-evidence-inventory.json'))
    args=parser.parse_args()
    root=args.root.resolve()
    inventory=(root/args.inventory).resolve()
    if args.mode=='restore':
        restore(root,args.archive.resolve(),inventory,directories=PATHS)
    else:
        pack(root,args.archive.resolve(),inventory,directories=PATHS)
        record=json.loads(inventory.read_text(encoding='utf-8'))
        record.update(scope='V2 generator-signals-v1 closed study: cohort inputs, observed summaries, models, raw audit outcomes and consumed budget ledger',
                      excluded=['official checkpoints','pinned source hard.txt blob (restore from Git source)','Python environment','confirmation model outcomes (never generated)'])
        inventory.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
