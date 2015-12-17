import os
import re

from .file_diff import FileDiff
from ..util.vcs import git_command, VCSHelper


class DiffParser(object):

    STAT_CHANGED_FILE = re.compile('\s*([\w\.\-\/]+)\s*\|')
    """Representation of the entire diff.

    Args:
        diff_args: The arguments to be used for the Git diff.
        cwd: The working directory.
    """

    def __init__(self, diff_args, cwd):
        self.cwd = cwd
        self.vcs_helper = VCSHelper.get_helper(self.cwd)
        self.git_base = git_command(
            ['rev-parse', '--show-toplevel'], self.cwd).rstrip()
        self.diff_args = diff_args
        self.changed_files = self._get_changed_files()
        self.changed_hunks = []
        for f in self.changed_files:
            self.changed_hunks += f.get_hunks()

    def _get_changed_files(self):
        files = []
        diff_stat = git_command(
            ['diff', '--stat', self.diff_args], self.git_base)
        for line in diff_stat.split('\n'):
            match = self.STAT_CHANGED_FILE.match(line)
            if match:
                filename = match.group(1)
                abs_filename = os.path.join(self.git_base, filename)

                # Get the diff text for this file.
                diff_text = git_command(
                    ['diff',
                     self.diff_args,
                     '-U0',
                     '--minimal',
                     '--word-diff=porcelain',
                     '--',
                     filename],
                    self.git_base)

                files.append(FileDiff(filename, abs_filename, diff_text))
        return files
