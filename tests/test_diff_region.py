import sys
from unittest import TestCase

diffview = sys.modules["DiffView"]
DiffRegion = diffview.parser.diff_region.DiffRegion

class test_DiffRegion(TestCase):

    def test_diff_region_init(self):
        r = DiffRegion("ADD", 3, 0, 5, 1)
        self.assertEqual(r.diff_type, "ADD")
        self.assertEqual(r.start_line, 3)
        self.assertEqual(r.start_col, 0)
        self.assertEqual(r.end_line, 5)
        self.assertEqual(r.end_col, 1)
