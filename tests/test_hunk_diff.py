import sys
from unittest import TestCase

diffview = sys.modules["DiffView"]
HunkDiff = diffview.parser.hunk_diff.HunkDiff

class DummyFileDiff(object):
    filename = 'dummy_filename'
    old_file = 'dummy_old_file'
    new_file = 'dummy_new_file'

class test_DiffRegion(TestCase):

    def setUp(self):
        self.file_diff = DummyFileDiff()

    def test_single_add_no_context(self):
        # @@ -10,0 +11,1 @@ some_function():
        # +new line
        match = ['10', '0', '11', '1',
            'some_function():\n' +
            '+new line'
        ]
        h = HunkDiff(self.file_diff, match)
        self.assertEqual(h.old_regions, [])
        self.assertEqual(len(h.new_regions), 1)
        self.check_region(
            h.new_regions[0],
            'ADD', 11, 0, 12, 0)
        self.assertEqual(h.old_line_focus, 10)
        self.assertEqual(h.new_line_focus, 11)
        self.assertEqual(h.hunk_type, 'ADD')
        self.assertEqual(
            h.description,
            ['dummy_filename : 11',
             'some_function():',
             '1 | +'])

    def test_single_del_no_context(self):
        # @@ -15,1 +14,0 @@ some_function():
        # -old line
        match = ['15', '1', '14', '0',
            'some_function():\n' +
            '-old line'
        ]
        h = HunkDiff(self.file_diff, match)
        self.assertEqual(len(h.old_regions), 1)
        self.check_region(
            h.old_regions[0],
            'DEL', 15, 0, 16, 0)
        self.assertEqual(h.new_regions, [])
        self.assertEqual(h.old_line_focus, 15)
        self.assertEqual(h.new_line_focus, 14)
        self.assertEqual(h.hunk_type, 'DEL')
        self.assertEqual(
            h.description,
            ['dummy_filename : 14',
             'some_function():',
             '1 | -'])

    def test_single_mod_no_context(self):
        # @@ -23,1 +34,1 @@ some_function():
        # -old line
        # +new line
        match = ['23', '1', '34', '1',
            'some_function():\n' +
            '-old line\n' +
            '+new line'
        ]
        h = HunkDiff(self.file_diff, match)
        self.assertEqual(len(h.old_regions), 1)
        self.check_region(
            h.old_regions[0],
            'DEL', 23, 0, 24, 0)
        self.assertEqual(len(h.new_regions), 1)
        self.check_region(
            h.new_regions[0],
            'ADD', 34, 0, 35, 0)
        self.assertEqual(h.old_line_focus, 23)
        self.assertEqual(h.new_line_focus, 34)
        self.assertEqual(h.hunk_type, 'MOD')
        self.assertEqual(
            h.description,
            ['dummy_filename : 34',
             'some_function():',
             '2 | +-'])


    def check_region(self, r, diff_type, start_line, start_col, end_line, end_col):
        self.assertEqual(r.diff_type, diff_type)
        self.assertEqual(r.start_line, start_line)
        self.assertEqual(r.start_col, start_col)
        self.assertEqual(r.end_line, end_line)
        self.assertEqual(r.end_col, end_col)
