"""Run the separately frozen confidence allocation follow-on."""
import argparse
from pathlib import Path

from concept_firewall.confidence_allocation import freeze, run_confirmation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=('freeze', 'confirm', 'recover'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.step == 'recover':
        from concept_firewall.allocation_recovery import run_recovery
        print(run_recovery(root))
    else:
        print((freeze if args.step == 'freeze' else run_confirmation)(root))


if __name__ == '__main__':
    main()
