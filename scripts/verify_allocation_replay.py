"""Check a fresh Git source archive plus restored evidence, without inference."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import zipfile

from concept_firewall.artifacts import sha256_file
from concept_firewall.v2_protocol import write_json


def main():
    root = Path(__file__).resolve().parents[1]
    inventory_path = root/'results/continuation/evidence_inventory.json'
    inventory = json.loads(inventory_path.read_text())
    archive = root/'dist'/inventory['archive']
    if sha256_file(archive) != inventory['archive_sha256']:
        raise ValueError('Evidence archive changed')
    revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    parent = root/'.tmp'/f'allocation-replay-{uuid.uuid4().hex[:12]}'
    parent.mkdir(parents=True, exist_ok=False)
    source = parent/'source.zip'
    subprocess.run(['git', '-C', str(root), 'archive', '--format=zip', f'--output={source}', revision], check=True)
    checkout = parent/'checkout'
    checkout.mkdir()
    with zipfile.ZipFile(source) as files:
        for item in files.infolist():
            if not (checkout/item.filename).resolve().is_relative_to(checkout):
                raise ValueError('Source archive path escapes replay folder')
        files.extractall(checkout)
    # The scientific source comes from the committed revision. The not-yet-
    # committed closeout inventory/helper are copied explicitly and hashed.
    additions = ('results/continuation/evidence_inventory.json', 'scripts/confidence_allocation_evidence.py')
    additions_hashes = {}
    for name in additions:
        destination = checkout/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root/name, destination)
        additions_hashes[name] = sha256_file(destination)
    temporary = checkout/'.test-tmp'
    temporary.mkdir()
    env = dict(os.environ, PYTHONPATH=str(checkout/'src'), TEMP=str(temporary), TMP=str(temporary))
    imported = subprocess.check_output([sys.executable, '-c',
        'from pathlib import Path; import concept_firewall, sys; p=Path(concept_firewall.__file__).resolve(); assert p.is_relative_to(Path(sys.argv[1])/"src"); print(p)',
        str(checkout)], cwd=checkout, env=env, text=True).strip()
    for _ in range(2):
        subprocess.run([sys.executable, str(checkout/'scripts/confidence_allocation_evidence.py'), 'restore',
                        '--archive', str(archive), '--root', str(checkout)], cwd=checkout, env=env, check=True, capture_output=True, text=True)
    process = subprocess.run([sys.executable, str(checkout/'scripts/audit_confidence_allocation.py'), '--root', str(checkout)],
                             cwd=checkout, env=env, check=True, capture_output=True, text=True)
    audit = json.loads(process.stdout)
    if audit['status'] != 'passed' or audit['new_model_calls'] or audit['new_fits']:
        raise ValueError('Restored audit failed or spent model resources')
    if audit['baseline_outcomes_checked'] != 1600 or audit['practical_fallback_audit']['development_outcomes_checked'] != 6400:
        raise ValueError('Restored audit missed declared outcomes')
    record = {'status': 'passed', 'source_revision': revision,
              'source_archive_sha256': sha256_file(source), 'closeout_additions_sha256': additions_hashes,
              'evidence_archive_sha256': inventory['archive_sha256'], 'restored_files': len(inventory['files']),
              'restored_twice_without_conflict': True, 'all_member_hashes_verified': True,
              'imported_source_path': imported, 'checkout': str(checkout),
              'baseline_outcomes_checked': audit['baseline_outcomes_checked'],
              'retry_outcomes_checked': sum(r['outcomes_checked'] for r in audit['policies']),
              'exact_fallback_outcomes_checked': audit['practical_fallback_audit']['development_outcomes_checked'],
              'new_model_calls': 0, 'new_fits': 0,
              'environment_boundary': 'Clean committed scientific source and restored evidence, using the existing research dependency environment; not a fresh environment build or a new scientific experiment',
              'verification_script_sha256': sha256_file(Path(__file__))}
    write_json(root/'results/continuation/replay_verification.json', record)
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
