"""Package/restore only the declared ignored follow-on evidence and ledgers."""
import argparse
import json
from pathlib import Path

from study_artifacts import pack, restore


PATHS = ('results/continuation/raw', 'results/continuation/runtime', 'results/v2/runtime',
         'results/v2/raw/20261025T030920192150Z-v2-outcome-audit')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('pack', 'restore'))
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--inventory', type=Path, default=Path('results/continuation/evidence_inventory.json'))
    args = parser.parse_args()
    root = args.root.resolve()
    inventory = (root/args.inventory).resolve()
    (pack if args.mode == 'pack' else restore)(root, args.archive.resolve(), inventory, directories=PATHS)
    if args.mode == 'pack':
        record = json.loads(inventory.read_text(encoding='utf-8'))
        record.update(scope='Confidence allocation and practical fallback: confirmation and retry tables, original audited development inputs/outcomes, exact fallback results, consumed follow-on and unchanged V2 ledgers',
                      excluded=['official checkpoints', 'Python environment', 'old V2 feature/model archives (not needed for this retained-data audit)'])
        inventory.write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
