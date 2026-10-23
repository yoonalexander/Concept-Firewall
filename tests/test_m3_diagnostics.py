import unittest

from concept_firewall.diagnostics import independent_cells, independent_inspection, digit_normalized_identity

SOLUTION="534678912672195348198342567859761423426853791713924856961537284287419635345286179"


class IndependentAuditTests(unittest.TestCase):
    def test_valid_and_changed_clue_witness(self):
        self.assertTrue(independent_inspection("0"*81,SOLUTION)["valid"])
        result=independent_inspection("6"+"0"*80,SOLUTION)
        self.assertFalse(result["valid"])
        self.assertEqual(result["changed_clues"],[{"row":1,"column":1,"clue":6,"output":5}])

    def test_duplicate_unit_witness_is_explicit(self):
        result=independent_inspection("0"*81,"3"+SOLUTION[1:])
        witness=result["conflict_witnesses"][0]
        self.assertEqual(witness["unit"],"row 1")
        self.assertEqual(witness["duplicate_digits"],[3])

    def test_malformed_and_incomplete_are_different(self):
        self.assertIsNone(independent_cells(SOLUTION+"|"))
        self.assertIsNone(independent_cells("１"*81))
        self.assertTrue(independent_inspection("0"*81,SOLUTION[:-1])["malformed"])
        partial=independent_inspection("0"*81,"_"+SOLUTION[1:])
        self.assertFalse(partial["malformed"])
        self.assertEqual(partial["blank_count"],1)
        self.assertFalse(partial["valid"])

    def test_strict_upstream_format_and_input_consistency(self):
        board="|".join(SOLUTION[r:r+9] for r in range(0,81,9))
        self.assertEqual(independent_cells(board),independent_cells(SOLUTION))
        with self.assertRaises(ValueError):
            independent_inspection("11"+"0"*79,SOLUTION)

    def test_limited_symmetry_normalization_is_digit_invariant(self):
        translated=SOLUTION.translate(str.maketrans("123456789","987654321"))
        self.assertEqual(digit_normalized_identity(SOLUTION),digit_normalized_identity(translated))
