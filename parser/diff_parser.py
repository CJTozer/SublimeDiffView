import os
import codecs
import tempfile

from ..util.vcs import VCSHelper


class DiffParser(object):
    """Class for handling understanding and parsing a specific diff.

    This class represents the entire diff.
    """

    def __init__(self, diff_args, cwd, debug=False, get_diff_headers=False):
        """Constructor.

        Args:
            diff_args: The arguments to be used for the Git diff.
            cwd: The working directory.
            get_diff_headers: Whether we want per-file header hunks for this diff.
        """
        self.diff_args = diff_args
        self.cwd = cwd
        self.temp_dir = tempfile.mkdtemp()
        self.debug = debug
        self.vcs_helper = VCSHelper.get_helper(self.cwd, debug=self.debug)
        self.changed_files = self.vcs_helper.get_changed_files(self.diff_args)
        self.changed_hunks = []
        for f in self.changed_files:
            self.changed_hunks += f.get_hunks(include_headers=get_diff_headers)

        self.setup_files()

    def setup_files(self):
        """Create all the files needed to show the diffs."""
        (old_ver, new_ver) = self.vcs_helper.get_file_versions(self.diff_args)

        for changed_file in self.changed_files:
            if old_ver == '':
                # Old file is working copy
                changed_file.old_file = changed_file.abs_filename
            else:
                # Get the old file contents in the temporary dir.
                changed_file.old_file = os.path.join(self.temp_dir, 'old', changed_file.filename)
                old_dir = os.path.dirname(changed_file.old_file)

                if not os.path.exists(old_dir):
                    os.makedirs(old_dir)
                with codecs.open(changed_file.old_file, 'w', 'utf-8') as f:
                    old_file_content = self.vcs_helper.get_file_content(changed_file.filename, old_ver)
                    f.write(old_file_content.replace('\r\n', '\n'))

            if new_ver == '':
                # New file is working copy
                changed_file.new_file = changed_file.abs_filename
            else:
                # Get the new file contents in the temporary dir.
                changed_file.new_file = os.path.join(
                    self.temp_dir,
                    'new',
                    changed_file.filename)
                new_dir = os.path.dirname(changed_file.new_file)

                if not os.path.exists(new_dir):
                    os.makedirs(new_dir)
                with codecs.open(changed_file.new_file, 'w', 'utf-8') as f:
                    new_file_content = self.vcs_helper.get_file_content(changed_file.filename, new_ver)
                    f.write(new_file_content.replace('\r\n', '\n'))
