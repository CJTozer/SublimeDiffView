import sys
from unittest import TestCase

diffview = sys.modules["DiffView"]
SVNHelper = diffview.util.vcs.SVNHelper


class test_SVNHelper(TestCase):

    def test_init(self):
        svn_helper = SVNHelper('/repo/base')
        self.assertFalse(svn_helper.got_changed_files)

    def test_file_versions(self):
        svn_helper = SVNHelper('/repo/base')
        self.assertEquals(
            svn_helper.get_file_versions(''),
            ('-r HEAD', ''))
        self.assertEquals(
            svn_helper.get_file_versions('-r 123'),
            ('-r 123', '-r HEAD'))
        self.assertEquals(
            svn_helper.get_file_versions('-r123'),
            ('-r 123', '-r HEAD'))
        self.assertEquals(
            svn_helper.get_file_versions('-r  234'),
            ('-r 234', '-r HEAD'))
        self.assertEquals(
            svn_helper.get_file_versions('-r 123:234'),
            ('-r 123', '-r 234'))
        self.assertEquals(
            svn_helper.get_file_versions('-r  123:234'),
            ('-r 123', '-r 234'))
        self.assertEquals(
            svn_helper.get_file_versions('-c 1234'),
            ('-r 1233', '-r 1234'))
        self.assertEquals(
            svn_helper.get_file_versions('--cl issue1234'),
            ('-r HEAD', ''))
