import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from concept_firewall.v2_data import load_partition, restore_data, symmetry_group, unique_solution

PUZZLE='530070000600195000098000060800060003400803001700020006060000280000419005000080079'
SOLUTION='534678912672195348198342567859761423426853791713924856961537284287419635345286179'


class V2DataTests(unittest.TestCase):
    def test_uniqueness_rejects_empty_inconsistent_and_ambiguous(self):
        self.assertTrue(unique_solution(PUZZLE)[0])
        self.assertTrue(unique_solution(SOLUTION)[0])
        self.assertFalse(unique_solution('0'*81)[0])
        self.assertFalse(unique_solution('55'+PUZZLE[2:])[0])
        self.assertFalse(unique_solution('malformed')[0])
        with self.assertRaisesRegex(RuntimeError,'node cap'):
            unique_solution(PUZZLE,max_nodes=1)

    def test_group_invariant_for_all_standard_symmetry_generators(self):
        expected=symmetry_group(PUZZLE)
        grids=[]
        grids.append(''.join(str(10-int(c)) if c!='0' else c for c in PUZZLE))
        for rows,columns in (([1,0,2,3,4,5,6,7,8],list(range(9))),
                             ([3,4,5,0,1,2,6,7,8],list(range(9))),
                             (list(range(9)),[2,1,0,3,4,5,6,7,8]),
                             (list(range(9)),[6,7,8,3,4,5,0,1,2])):
            grids.append(''.join(PUZZLE[r*9+c] for r in rows for c in columns))
        grids.append(''.join(PUZZLE[c*9+r] for r in range(9) for c in range(9)))
        for puzzle in grids:
            with self.subTest(puzzle=puzzle):
                self.assertEqual(symmetry_group(puzzle),expected)
        self.assertNotEqual(symmetry_group('0'*81),expected)

    def test_confirmation_loader_seals_inputs_and_detects_digest_change(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            target=root/'results/v2/contracts/generator-signals-v1-data.json'
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps({'partitions':{'train':{'file':'changed.jsonl','sha256':'invalid','puzzles':1}}}))
            (root/'changed.jsonl').write_text('{}\n')
            with self.assertRaisesRegex(ValueError,'sealed'):
                load_partition(root,'confirmation')
            with self.assertRaisesRegex(ValueError,'differs'):
                load_partition(root,'train')

    def test_frozen_restore_preserves_conflicting_content(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            key=hashlib.sha256(PUZZLE.encode()).hexdigest()
            raw=f'source {PUZZLE} 3.0\n'.encode()
            row={'puzzle_id':key,'group':'group','puzzle':PUZZLE,'source_rating':3.0}
            payload=(json.dumps(row,separators=(',',':'))+'\n').encode()
            manifest={'source_revision':'frozen','source_blob_sha256':{'hard.txt':hashlib.sha256(raw).hexdigest()},
                      'partitions':{'train':{'file':'data/train.jsonl','puzzle_ids':[key],'groups':['group'],'sha256':hashlib.sha256(payload).hexdigest()}}}
            target=root/'results/v2/contracts/generator-signals-v1-data.json'
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(manifest))
            with patch('concept_firewall.v2_data.subprocess.check_output',return_value=raw):
                restore_data(root,Path('source'))
                self.assertEqual((root/'data/train.jsonl').read_bytes(),payload)
                (root/'data/train.jsonl').write_bytes(b'preserve this')
                with self.assertRaisesRegex(ValueError,'conflicting'):
                    restore_data(root,Path('source'))
                self.assertEqual((root/'data/train.jsonl').read_bytes(),b'preserve this')
