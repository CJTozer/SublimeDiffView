from abc import ABCMeta, abstractmethod
import subprocess
import re
import os

from ..parser.file_diff import FileDiff


class VCSHelper(object):
    """Abstract base class for helping with VCS operations.

    Given a directory, calling `VCSHelper.get_helper` will get an appropriate helper for the VCS system used by that
    directory.
    """
    __metaclass__ = ABCMeta
    SVN_BASE_MATCH = re.compile('Root Path:\s*([\:\\\\/\w\.\-]*)')

    @classmethod
    def get_helper(cls, cwd):
        """Get the correct VCS helper for this codebase.

        Checks for Git first, then Subversion.

        Args:
            cwd: The current directory.  Not necessarily the base of the VCS.

        Returns:
            A `GitHelper` or `SVNHelper` if in a repo.

        Raises:
            `NoVCSError` if the `cwd` isn't under version control.
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
                'svn info',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                cwd=cwd)
            out, err = p.communicate()
            if not err:
                match = VCSHelper.SVN_BASE_MATCH.search(out.decode('utf-8'))
                if match:
                    return SVNHelper(match.group(1))
                else:
                    print("Couldn't find SVN repo in:\n{}".format(out.decode('utf-8')))
        except:
            pass

        # No VCS found
        raise NoVCSError

    @abstractmethod
    def get_changed_files(self, diff_args):
        """Get a list of changed files.

        Args:
            diff_args: The diff args that define which files have changed.

        Returns:
            An array of `FileDiff` objects representing the changed files.
        """
        pass

    @abstractmethod
    def get_file_versions(self, diff_args):
        """Get both the versions of the file.

        An empty string means that the file is the working copy version.

        Args:
            diff_args: The diff arguments.

        Returns:
            A tuple with the 'version' for the old and new file, suitable for passing in to `get_file_content`.
        """
        pass

    @abstractmethod
    def get_file_content(self, filename, version):
        """Get the contents of a file at a specific version.

        Args:
            filename: The file.
            version: The version.

        Returns:
            A string with the file's contents at the specified version.
        """
        pass

    def vcs_command(self, args):
        """Wrapper to run a VCS command.

        Args:
            args: The args for the VCS command.

        Returns:
            The command's output, as a string.
        """
        # Using shell, just pass a string to subprocess.
        p = subprocess.Popen(
            " ".join([self.vcs] + args),
            stdout=subprocess.PIPE,
            shell=True,
            cwd=self.repo_base)
        out, err = p.communicate()
        return out.decode('utf-8')


class NoVCSError(Exception):
    """Exception raised when no VCS is found."""
    pass


class GitHelper(VCSHelper):
    """VCSHelper implementation for Git repositories."""

    STAT_CHANGED_FILE = re.compile('\s*([\w\.\-\/]+)\s*\|')
    DIFF_MATCH_MERGE_BASE = re.compile('(.*)\.\.\.(.*)')
    DIFF_MATCH = re.compile('(.*)\.\.(.*)')

    def __init__(self, repo_base):
        """Constructor

        Args:
            repo_base: The base directory of the repo.
        """
        self.repo_base = repo_base
        self.got_changed_files = False
        self.vcs = 'git'

    def get_changed_files(self, diff_args):
        files = []
        if not self.got_changed_files:
            diff_stat = self.vcs_command(['diff', '--stat', diff_args])
            for line in diff_stat.split('\n'):
                match = self.STAT_CHANGED_FILE.match(line)
                if match:
                    filename = match.group(1)
                    abs_filename = os.path.join(self.repo_base, filename)

                    # Get the diff text for this file.
                    diff_text = self.vcs_command(['diff', diff_args, '-U0', '--', filename])
                    files.append(FileDiff(filename, abs_filename, diff_text))
        self.got_changed_files = True
        return files

    def get_file_versions(self, diff_args):
        # Merge base diff
        match = self.DIFF_MATCH_MERGE_BASE.match(diff_args)
        if match:
            base1 = match.group(1) or 'HEAD'
            base2 = match.group(2) or 'HEAD'
            merge_base = self.vcs_command(['merge-base', base1, base2])
            # merge_base comes back with a newline on the end - strip it.
            return (merge_base.rstrip(), base2)

        # Normal diff
        match = self.DIFF_MATCH.match(diff_args)
        if match:
            return (match.group(1), match.group(2))

        if diff_args != '':
            # WC comparison
            return (diff_args, '')

        # HEAD to WC comparison
        return ('HEAD', '')

    def get_file_content(self, filename, version):
        git_args = ['show', '{}:{}'.format(version, filename)]
        try:
            content = self.vcs_command(git_args)
        except UnicodeDecodeError:
            content = "Unable to decode file..."
        return content


class SVNHelper(VCSHelper):
    """VCSHelper implementation for SVN repositories."""

    STATUS_CHANGED_FILE = re.compile('\s*[AM][\+CMLSKOTB\s]*([\w\.\-\/\\\\]+)')
    DUAL_REV_MATCH = re.compile('-r *(\d+):(\d+)')
    REV_MATCH = re.compile('-r *(\d+)')
    COMMIT_MATCH = re.compile('-c *(\d+)')

    def __init__(self, repo_base):
        self.repo_base = repo_base
        self.got_changed_files = False
        self.vcs = 'svn'

    def get_changed_files(self, diff_args):
        files = []
        if not self.got_changed_files:
            if self.DUAL_REV_MATCH.match(diff_args):
                # Comparison between 2 revisions
                status_text = self.vcs_command(['diff', diff_args, '--summarize'])
            elif self.REV_MATCH.match(diff_args):
                # Can only compare this against HEAD
                status_text = self.vcs_command(['diff', diff_args + ':HEAD', '--summarize'])
            elif self.COMMIT_MATCH.match(diff_args):
                # Commit match
                status_text = self.vcs_command(['diff', diff_args, '--summarize'])
            else:
                # Show uncommitted changes
                status_text = self.vcs_command(['status', diff_args])
            for line in status_text.split('\n'):
                match = self.STATUS_CHANGED_FILE.match(line)
                if match:
                    filename = match.group(1)
                    abs_filename = os.path.join(self.repo_base, filename)

                    # Don't add directories to the list
                    if not os.path.isdir(abs_filename):
                        # Get the diff text for this file.
                        diff_text = self.vcs_command(['diff', diff_args, filename])
                        files.append(FileDiff(filename, abs_filename, diff_text))

        self.got_changed_files = True
        return files

    def get_file_versions(self, diff_args):
        # Diff between two versions?
        match = self.DUAL_REV_MATCH.match(diff_args)
        if match:
            return ('-r {}'.format(match.group(1)), '-r {}'.format(match.group(2)))

        # Diff HEAD against a specific revision?
        match = self.REV_MATCH.match(diff_args)
        if match:
            return ('-r {}'.format(match.group(1)), '-r HEAD')

        # Diff for a specific commit
        match = self.COMMIT_MATCH.match(diff_args)
        if match:
            new_revision = int(match.group(1))
            old_revision = new_revision - 1
            return ('-r {}'.format(old_revision), '-r {}'.format(new_revision))

        # Compare HEAD against WC
        return ('-r HEAD', '')

    def get_file_content(self, filename, version):
        try:
            content = self.vcs_command(['cat', version, filename])
        except UnicodeDecodeError:
            content = "Unable to decode file..."
        return content
