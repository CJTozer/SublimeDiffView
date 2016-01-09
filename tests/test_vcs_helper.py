import sys
from unittest import TestCase
from unittest.mock import patch

diffview = sys.modules["DiffView"]
VCSHelper = diffview.util.vcs.VCSHelper
GitHelper = diffview.util.vcs.GitHelper
SVNHelper = diffview.util.vcs.SVNHelper


class test_VCSHelper(TestCase):

    def setUp(self):
        self.dummy_process = DummyProcess()

    @patch('subprocess.Popen')
    def test_get_helper_no_vcs(self, mocked_Popen):
        mocked_Popen.return_value = self.dummy_process
        # Errors for both Git and SVN commands
        self.dummy_process.ret_vals = [
            (b'output ignored', b'error in Git command'),
            (b'output ignored', b'error in SVN command')
        ]
        with self.assertRaises(diffview.util.vcs.NoVCSError):
            VCSHelper.get_helper('.')

    @patch('subprocess.Popen')
    def test_get_helper_git(self, mocked_Popen):
        mocked_Popen.return_value = self.dummy_process
        # No error in Git command
        self.dummy_process.ret_vals = [
            (b'/some/magic/dir', b''),
            (b'output ignored', b'error in SVN command')
        ]
        helper = VCSHelper.get_helper('.')
        self.assertIsInstance(helper, GitHelper)
        self.assertEquals(helper.git_base, '/some/magic/dir')

    @patch('subprocess.Popen')
    def test_get_helper_svn(self, mocked_Popen):
        mocked_Popen.return_value = self.dummy_process
        # Error in Git command, SVN command OK
        self.dummy_process.ret_vals = [
            (b'/some/magic/dir', b'...but I failed...'),
            (b'some\nthings\nThen a Root Path: /dir/to/svn  \nThen more', b'')
        ]
        helper = VCSHelper.get_helper('.')
        self.assertIsInstance(helper, SVNHelper)
        self.assertEquals(helper.svn_base, '/dir/to/svn')


class DummyProcess(object):
    """Dummy process to return values from `communicate()`.

    Set `ret_vals` to use.
    """
    def communicate(self, *args, **kwargs):
        return self.ret_vals.pop(0)
