import sys
import subprocess
from unittest import TestCase
from unittest.mock import patch

diffview = sys.modules["DiffView"]
BzrHelper = diffview.util.vcs.BzrHelper


class test_BzrHelper(TestCase):

    def setUp(self):
        self.dummy_process = DummyProcess()

    def test_init(self):
        bzr_helper = BzrHelper('/repo/base')
        self.assertFalse(bzr_helper.got_changed_files)

    @patch('subprocess.Popen')
    def test_file_versions(self, mocked_Popen):
        bzr_helper = BzrHelper('/repo/base')
        self.assertEquals(
            bzr_helper.get_file_versions(''),
            ('last:1', ''))
        self.assertEquals(
            bzr_helper.get_file_versions('branch_name'),
            ('branch_name', ''))
        self.assertEquals(
            bzr_helper.get_file_versions('branch_name..'),
            ('branch_name', ''))
        self.assertEquals(
            bzr_helper.get_file_versions('branch_name..other_branch_name'),
            ('branch_name', 'other_branch_name'))
        self.assertEquals(
            bzr_helper.get_file_versions('..other_branch_name'),
            ('', 'other_branch_name'))


class DummyProcess(object):
    """Dummy process to return values from `communicate()`.

    Set `ret_vals` to use.
    """
    def communicate(self, *args, **kwargs):
        return self.ret_vals.pop(0)
