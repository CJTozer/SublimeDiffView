import sys
import subprocess
from unittest import TestCase
from unittest.mock import patch

diffview = sys.modules["DiffView"]
GitHelper = diffview.util.vcs.GitHelper


class test_GitHelper(TestCase):

    def setUp(self):
        self.dummy_process = DummyProcess()

    def test_init(self):
        git_helper = GitHelper('/repo/base')
        self.assertFalse(git_helper.got_changed_files)

    @patch('subprocess.Popen')
    def test_file_versions(self, mocked_Popen):
        git_helper = GitHelper('/repo/base')
        self.assertEquals(
            git_helper.get_file_versions(''),
            ('HEAD', ''))
        self.assertEquals(
            git_helper.get_file_versions('branch_name'),
            ('branch_name', ''))
        self.assertEquals(
            git_helper.get_file_versions('branch_name..'),
            ('branch_name', ''))
        self.assertEquals(
            git_helper.get_file_versions('branch_name..other_branch_name'),
            ('branch_name', 'other_branch_name'))
        self.assertEquals(
            git_helper.get_file_versions('..other_branch_name'),
            ('', 'other_branch_name'))

        # Popen not called until trying to get a merge base
        mocked_Popen.return_value = self.dummy_process
        self.dummy_process.ret_vals = [(b'merge_base_commit', b'')]
        self.assertEquals(
            git_helper.get_file_versions('branch_a...branch_b'),
            ('merge_base_commit', 'branch_b'))
        mocked_Popen.assert_called_with(
            'git merge_base branch_a branch_b',
            stdout=subprocess.PIPE,
            shell=True,
            cwd='/repo/base')

        self.dummy_process.ret_vals = [(b'merge_base_commit', b'')]
        self.assertEquals(
            git_helper.get_file_versions('branch_a...'),
            ('merge_base_commit', ''))
        mocked_Popen.assert_called_with(
            'git merge_base branch_a ',
            stdout=subprocess.PIPE,
            shell=True,
            cwd='/repo/base')

        self.dummy_process.ret_vals = [(b'merge_base_commit', b'')]
        self.assertEquals(
            git_helper.get_file_versions('...branch_b'),
            ('merge_base_commit', 'branch_b'))
        mocked_Popen.assert_called_with(
            'git merge_base  branch_b',
            stdout=subprocess.PIPE,
            shell=True,
            cwd='/repo/base')


class DummyProcess():
    """Dummy process to return values from `communicate()`.

    Set `ret_vals` to use.
    """
    def communicate(self, *args, **kwargs):
        return self.ret_vals.pop(0)
