import sublime
import sublime_plugin
import subprocess
import re
import os
import tempfile

class DiffView(sublime_plugin.WindowCommand):
    last_diff = ''

    def run(self):
        # Use this as show_quick_panel doesn't allow arbitrary data
        self.window.show_input_panel("Diff against? [HEAD]", self.last_diff, self.do_diff, None, None)
        self.window.last_diff = self
        self.last_file_index = 0

        # Create a temporary directory for (read-only) old versions of changed files
        self.temp_dir = tempfile.mkdtemp()

    def do_diff(self, diff_base):
        if diff_base == '':
            diff_base = 'HEAD'
        self.last_diff = diff_base
        self.diff_base = diff_base
        print("Diff args: %s" % self.diff_base)

        self.parser = DiffParser(self.diff_base)

        # Create the old files in the temporary directory
        self.create_old_files()

        # Show the list of changed files
        self.list_changed_files()

    def create_old_files(self):
        for changed_file in self.parser.changed_files:
            print("File {} has changed".format(changed_file.filename))
            target_dir = os.path.join(self.temp_dir, os.path.dirname(changed_file.filename))
            target_file = os.path.join(self.temp_dir, changed_file.filename)
            print(target_file)
            if not os.path.exists(target_dir):
                os.makedirs(os.path.join(self.temp_dir, os.path.dirname(changed_file.filename)))
            with open(target_file, 'w') as f:
                git_args = ['show', '{}:{}'.format(self.diff_base, changed_file.filename)]
                old_file_content = git_command(git_args)
                f.write(old_file_content.replace('\r\n', '\n'))

    def list_changed_files(self):
        self.window.show_quick_panel(
            [f.filename for f in self.parser.changed_files],
            self.show_file_diff,
            0,
            self.last_file_index,
            self.preview_diff)

    def show_file_diff(self, index):
        self.last_file_index = index
        print("show_file_diff: {}".format(self.parser.changed_files[index]))

    def preview_diff(self, index):
        print("preview_diff: {}".format(index))

class DiffFilesList(sublime_plugin.WindowCommand):
    def run(self):
        if hasattr(self.window, 'last_diff'):
            self.window.last_diff.list_changed_files()

class DiffParser(object):
    STAT_CHANGED_FILE = re.compile('\s*([\w\.\-\/]+)\s*\|')

    def __init__(self, diff_base):
        self.diff_base = diff_base
        self.changed_files = self._get_changed_files()

    def _get_changed_files(self):
        files = []
        for line in git_command(['diff', '--stat', self.diff_base]).split('\n'):
            match = self.STAT_CHANGED_FILE.match(line)
            if match:
                files.append(FileDiff(match.group(1), self.diff_base))
        return files

class FileDiff(object):
    HUNK_MATCH = re.compile('\r?\n@@ \-(\d+),\d+ \+(\d+),\d+ @@')

    def __init__(self, filename, diff_args):
        self.filename = filename
        self.diff_args = diff_args
        self.diff_text = ''
        self.hunks = []

    def parse_diff(self):
        if not self.diff_text:
            self.diff_text = git_command(['diff', self.diff_args, '--minimal', '-U0', '--word-diff=porcelain', '--', self.filename])
            hunks = self.HUNK_MATCH.split(self.diff_text)
            # First item is the header - drop it
            hunks.pop(0)
            print(hunks)
            while len(hunks) >= 3:
                # Don't force all parsing up-front
                self.hunks.append(HunkDiff(old_line_num=hunks[0],
                                           new_line_num=hunks[1],
                                           hunk_diff_text=hunks[2]))
                hunks = hunks[3:]

class HunkDiff(object):
    LINE_DELIM_MATCH = re.compile('\r?\n~\r?\n')
    ADD_LINE_MATCH = re.compile('^\+(.*)')
    DEL_LINE_MATCH = re.compile('^\-(.*)')

    def __init__(self, old_line_num, new_line_num, hunk_diff_text):
        self.old_line_num = int(old_line_num)
        self.new_line_num = int(new_line_num)
        self.hunk_diff_text = hunk_diff_text
        print("Created new hunk.")
        print("    Old line start: {}".format(self.old_line_num))
        print("    New line start: {}".format(self.new_line_num))
        print("    Diff:\n{}----".format(self.hunk_diff_text))

    def parse_diff(self):
        # Need to track line number (and character position) as we run through the regions.
        # Multiline adds and deletes are spread over multiple regions.
        old_line_num = self.old_line_num
        new_line_num = self.new_line_num
        for region in self.LINE_DELIM_MATCH.split(self.hunk_diff_text):
            print("$$$$" + region + "&&&&")
            add_match = self.ADD_LINE_MATCH.match(region)
            del_match = self.DEL_LINE_MATCH.match(region)

def git_command(args):
    print(args)
    p = subprocess.Popen(['git'] + args,
                         stdout=subprocess.PIPE,
                         shell=True)
    out, err = p.communicate()
    return out.decode('utf-8')
