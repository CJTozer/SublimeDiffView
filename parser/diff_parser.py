import os
import tempfile

from ..util.vcs import VCSHelper


class DiffParser(object):
    """Representation of the entire diff.

    Args:
        diff_args: The arguments to be used for the Git diff.
        cwd: The working directory.
    """
    def __init__(self, diff_args, cwd):
        self.diff_args = diff_args
        self.cwd = cwd
        self.temp_dir = tempfile.mkdtemp()
        self.vcs_helper = VCSHelper.get_helper(self.cwd)
        self.changed_files = self.vcs_helper.get_changed_files(self.diff_args)
        self.changed_hunks = []
        for f in self.changed_files:
            self.changed_hunks += f.get_hunks()

        # Create the required temporary files
        self.create_files()

    def create_files(self):
        """Create all the files needed to show the diffs."""
        for changed_file in self.changed_files:
            changed_file.old_file = os.path.join(
                self.temp_dir,
                'old',
                changed_file.filename)
            old_dir = os.path.dirname(changed_file.old_file)

            if not os.path.exists(old_dir):
                os.makedirs(old_dir)
            with open(changed_file.old_file, 'w') as f:
                old_file_content = self.vcs_helper.get_file_content(
                    changed_file.filename,
                    self.diff_args)
                f.write(old_file_content.replace('\r\n', '\n'))

            # TODO - when doing more complex diffs, need to grab a blob with
            # `git show` like above, and copy to the 'new' temporary directory.
            # changed_file.new_file = os.path.join(
            #     self.temp_dir,
            #     'new',
            #     changed_file.filename)
            # new_dir = os.path.dirname(changed_file.new_file)
            # if not os.path.exists(new_dir):
            #     os.makedirs(new_dir)
            # shutil.copyfile(changed_file.abs_filename, changed_file.new_file)
