from abc import ABCMeta, abstractmethod
import subprocess
import re


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
    """VCSHelper implementation for Git repositories."""

    def __init__(self, repo_base):
        self.git_base = repo_base

    def get_changed_files():
        pass


class SVNHelper(VCSHelper):

    def __init__(self, repo_base):
        self.svn_base = repo_base

    def get_changed_files():
        pass


def git_command(args, cwd):
    """Wrapper to run a Git command."""
    # Using shell, just pass a string to subprocess.
    p = subprocess.Popen(" ".join(['git'] + args),
                         stdout=subprocess.PIPE,
                         shell=True,
                         cwd=cwd)
    out, err = p.communicate()
    return out.decode('utf-8')
