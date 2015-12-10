import sublime
import sublime_plugin
import subprocess
import re

class DiffView(sublime_plugin.WindowCommand):
    last_diff = ''

    def run(self):
        # Use this as show_quick_panel doesn't allow arbitrary data
        self.window.show_input_panel("Diff parameters?", self.last_diff, self.do_diff, None, None)
        self.window.last_diff = self

    def do_diff(self, diff_args):
        self.last_diff = diff_args
        if diff_args == '':
            diff_args = 'HEAD'
        print("Diff args: %s" % diff_args)

        parser = DiffParser(diff_args)

        # For now, just print some info...
        for f in parser.changed_files:
            print("File {} has changed".format(f.filename))
            f.parse_diff()
            for hunk in f.hunks:
                hunk.parse_diff()

class DiffFilesList(sublime_plugin.WindowCommand):
    def run(self):
        if self.window.last_diff:
            print("Using existing diff...")

class DiffParser(object):
    STAT_CHANGED_FILE = re.compile('\s*([\w\.\-]+)\s*\|')

    def __init__(self, diff_args):
        self.diff_args = diff_args
        self.changed_files = self._get_changed_files()

    def _get_changed_files(self):
        files = []
        for line in git_command(['diff', '--stat', self.diff_args]).split('\n'):
            match = self.STAT_CHANGED_FILE.match(line)
            if match:
                files.append(FileDiff(match.group(1), self.diff_args))
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
            self.diff_text = git_command(['diff', self.diff_args, '--minimal', '--word-diff=porcelain', '--', self.filename])
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
    p = subprocess.Popen(['git'] + args,
                         stdout=subprocess.PIPE,
                         shell=True)
    out, err = p.communicate()
    return out.decode('utf-8')
