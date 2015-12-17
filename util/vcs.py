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
                'git rev-parse --show-toplevel',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
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
    def get_changed_files(self, diff_args):
        """Get a list of changed files."""
        pass

    @abstractmethod
    def get_file_content(self, filename, version):
        """Get the contents of a file at a specific version."""
        pass


class GitHelper(VCSHelper):

    STAT_CHANGED_FILE = re.compile('\s*([\w\.\-\/]+)\s*\|')
    """VCSHelper implementation for Git repositories."""

    def __init__(self, repo_base):
        self.git_base = repo_base
        self.got_changed_files = False
        self.changed_files = []

    def get_changed_files(self, diff_args):
        files = []
        if not self.got_changed_files:
            diff_stat = self.git_command(['diff', '--stat', diff_args])
            for line in diff_stat.split('\n'):
                match = self.STAT_CHANGED_FILE.match(line)
                if match:
                    filename = match.group(1)
                    abs_filename = os.path.join(self.git_base, filename)

                    # Get the diff text for this file.
                    diff_text = self.git_command(
                        ['diff',
                         diff_args,
                         '-U0',
                         '--minimal',
                         '--word-diff=porcelain',
                         '--',
                         filename])
                    files.append(FileDiff(filename, abs_filename, diff_text))
        self.got_changed_files = True
        return files

    def get_file_content(self, filename, version):
        git_args = ['show', '{}:{}'.format(version, filename)]
        return self.git_command(git_args)

    def git_command(self, args):
        """Wrapper to run a Git command."""
        # Using shell, just pass a string to subprocess.
        p = subprocess.Popen(" ".join(['git'] + args),
                             stdout=subprocess.PIPE,
                             shell=True,
                             cwd=self.git_base)
        out, err = p.communicate()
        return out.decode('utf-8')


class SVNHelper(VCSHelper):

    def __init__(self, repo_base):
        self.svn_base = repo_base

    def get_changed_files(self, diff_args):
        return []
