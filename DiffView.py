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

        for f in parser.changed_files:
            print("File {} has changed".format(f.filename))
            f.parse_diff()
            for hunk in f.hunks:
                print(hunk.hunk_match.group(0))

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
                files.append(FileDiffParser(match.group(1), self.diff_args))
        return files

class FileDiffParser(object):
    HUNK_MATCH = re.compile('^@@ \-(\d+),(\d+) \+(\d+),(\d+) @@')

    def __init__(self, filename, diff_args):
        self.filename = filename
        self.diff_args = diff_args
        self.diff_text = ''
        self.hunks = []

    def parse_diff(self):
        if not self.diff_text:
            self.diff_text = git_command(['diff', self.diff_args, '--', self.filename])
            hunk = None
            for line in self.diff_text.split('\n'):
                match = self.HUNK_MATCH.match(line)
                if match:
                    hunk = HunkDiffParser(match)
                    self.hunks.append(hunk)
                elif hunk:
                    hunk.diff_lines.append(line)

class HunkDiffParser(object):
    def __init__(self, hunk_match):
        self.hunk_match = hunk_match
        self.diff_lines = []

def git_command(args):
    p = subprocess.Popen(['git'] + args,
                         stdout=subprocess.PIPE,
                         shell=True)
    out, err = p.communicate()
    return out.decode('utf-8')
