from abc import ABCMeta, abstractmethod
import subprocess
import re
import os

from ..parser.file_diff import FileDiff


class VCSHelper(object):
    __metaclass__ = ABCMeta
    SVN_BASE_MATCH = re.compile('Root Path:\s*([\\/\w\.\-]*)')

    @classmethod
    def get_helper(cls, cwd):
        """Get the correct VCS helper for this codebase.

        Args:
            cwd: The current directory.  Not necessarily the base of the VCS.
        """
        # Check for a Git repo first
        try:
            p = subprocess.Popen(
                ['git', 'rev-parse', '--show-toplevel'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd)
            out, err = p.communicate()
            if not err:
                return GitHelper(out.decode('utf-8').rstrip())
        except:
            pass

        try:
            # Now check for SVN
            p = subprocess.Popen(
                ['svn', 'info'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd)
            out, err = p.communicate()
            if not err:
                m = VCSHelper.SVN_BASE_MATCH.search(out.decode('utf-8'))
                if m:
                    return SVNHelper(m.group(1))
                else:
                    print("Couldn't find SVN repo in:\n{}".format(
                        out.decode('utf-8')))
        except:
            pass

    @abstractmethod
    def get_changed_files():
        """@@@"""
        pass


class GitHelper(VCSHelper):

    STAT_CHANGED_FILE = re.compile('\s*([\w\.\-\/]+)\s*\|')
    """VCSHelper implementation for Git repositories."""

    def __init__(self, repo_base, diff_args):
        self.git_base = repo_base
        self.diff_args = diff_args
        self.got_changed_files = False
        self.changed_files = []

    def get_changed_files(self):
        files = []
        if not self.got_changed_files:
            diff_stat = self.git_command(
                ['diff', '--stat', self.diff_args], self.repo_base)
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
        self.got_changed_files = True
        return files

    def git_command(args, cwd):
        """Wrapper to run a Git command."""
        # Using shell, just pass a string to subprocess.
        p = subprocess.Popen(" ".join(['git'] + args),
                             stdout=subprocess.PIPE,
                             shell=True,
                             cwd=cwd)
        out, err = p.communicate()
        return out.decode('utf-8')


class SVNHelper(VCSHelper):

    def __init__(self, repo_base, diff_args):
        self.svn_base = repo_base
        self.diff_args = diff_args

    def get_changed_files(self):
        return []


def git_command(args, cwd):
    """Wrapper to run a Git command."""
    # Using shell, just pass a string to subprocess.
    p = subprocess.Popen(" ".join(['git'] + args),
                         stdout=subprocess.PIPE,
                         shell=True,
                         cwd=cwd)
    out, err = p.communicate()
    return out.decode('utf-8')
