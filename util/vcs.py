from abc import ABCMeta, abstractmethod
import subprocess


class VCSHelper(object):
    __metaclass__ = ABCMeta

    @classmethod
    def get_helper(cwd):
        """@@@"""
        pass

    @abstractmethod
    def get_changed_files():
        """@@@"""
        pass


class GitHelper(VCSHelper):

    def get_changed_files():
        pass


class SVNHelper(VCSHelper):

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
