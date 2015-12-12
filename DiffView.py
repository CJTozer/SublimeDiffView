import sublime
import sublime_plugin
import subprocess
import re
import os
import tempfile
import time
import threading

REGION_KEY = 'cjttest'

class DiffView(sublime_plugin.WindowCommand):
    diff_base = ''

    def run(self):
        self.window.last_diff = self
        self.last_hunk_index = 0
        self.preview = None

        # Use show_input_panel as show_quick_panel doesn't allow arbitrary data
        self.window.show_input_panel("Diff against? [HEAD]", self.diff_base, self.do_diff, None, None)

    def do_diff(self, diff_base):
        if diff_base == '':
            diff_base = 'HEAD'
        self.diff_base = diff_base

        # Record the original layout
        self.orig_layout = self.window.get_layout()

        # Create the diff parser
        self.parser = DiffParser(self.diff_base)

        # Show the list of changed hunks
        self.list_changed_hunks()

    def list_changed_hunks(self):
        self.window.show_quick_panel(
            [h.description for h in self.parser.changed_hunks],
            self.show_hunk_diff,
            0,
            self.last_hunk_index,
            self.preview_hunk)

    def show_hunk_diff(self, index):
        print("show_hunk_diff: {}".format(index))
        self.window.active_view().erase_regions(REGION_KEY)
        if index == -1:
            if self.preview:
                self.preview.close()
                self.preview = None
            return
        self.last_hunk_index = index
        hunk = self.parser.changed_hunks[index]
        self.window.open_file(hunk.filespec(), sublime.ENCODED_POSITION)

    def preview_hunk(self, index):
        hunk = self.parser.changed_hunks[index]
        already_exists = self.window.find_open_file(hunk.file_diff.filename)
        self.preview = self.window.open_file(hunk.filespec(), sublime.TRANSIENT | sublime.ENCODED_POSITION)
        if already_exists:
            self.preview = None
        hunk.file_diff.add_regions(self.window.active_view())

class DiffHunksList(sublime_plugin.WindowCommand):
    def run(self):
        if hasattr(self.window, 'last_diff'):
            self.window.last_diff.list_changed_hunks()

class DiffParser(object):
    STAT_CHANGED_FILE = re.compile('\s*([\w\.\-\/]+)\s*\|')

    def __init__(self, diff_base):
        self.git_base = git_command(['rev-parse', '--show-toplevel']).rstrip()
        self.diff_base = diff_base
        self.changed_files = self._get_changed_files()
        self.changed_hunks = []
        for f in self.changed_files:
            self.changed_hunks += f.get_hunks()

    def _get_changed_files(self):
        files = []
        for line in git_command(['diff', '--stat', self.diff_base]).split('\n'):
            match = self.STAT_CHANGED_FILE.match(line)
            if match:
                filename = match.group(1)
                abs_filename = os.path.join(self.git_base, filename)
                files.append(FileDiff(match.group(1), abs_filename, self.diff_base))
        return files

class FileDiff(object):
    HUNK_MATCH = re.compile('\r?\n@@ \-(\d+),(\d+) \+(\d+),(\d+) @@')

    def __init__(self, filename, abs_filename, diff_args):
        self.filename = filename
        self.abs_filename = abs_filename
        self.old_file = 'UNDEFINED'
        self.diff_args = diff_args
        self.diff_text = ''
        self.hunks = []

    def get_hunks(self):
        if not self.hunks:
            self.parse_diff()
        return self.hunks

    def parse_diff(self):
        if not self.diff_text:
            self.diff_text = git_command(['diff', self.diff_args, '--minimal', '-U0', '--', self.filename])
            hunks = self.HUNK_MATCH.split(self.diff_text)
            # First item is the header - drop it
            hunks.pop(0)
            print(hunks)
            while len(hunks) >= 5:
                # Don't force all parsing up-front
                self.hunks.append(HunkDiff(self,
                                           old_line_num=hunks[0],
                                           old_hunk_len=hunks[1],
                                           new_line_num=hunks[2],
                                           new_hunk_len=hunks[3],
                                           hunk_diff_text=hunks[4]))
                hunks = hunks[5:]

    def add_regions(self, view):
        regions = [sublime.Region(
            view.text_point(h.new_line_num, 0),
            view.text_point(h.new_line_num + h.new_hunk_len + 1, -1)) for h in self.hunks]
        view.add_regions(REGION_KEY, regions, "cjttest")

class HunkDiff(object):
    LINE_DELIM_MATCH = re.compile('\r?\n~\r?\n')
    ADD_LINE_MATCH = re.compile('^\+(.*)')
    DEL_LINE_MATCH = re.compile('^\-(.*)')

    def __init__(self,
                 file_diff,
                 old_line_num,
                 old_hunk_len,
                 new_line_num,
                 new_hunk_len,
                 hunk_diff_text):
        self.file_diff = file_diff
        self.old_line_num = int(old_line_num)
        self.old_hunk_len = int(old_hunk_len)
        self.new_line_num = int(new_line_num)
        self.new_hunk_len = int(new_hunk_len)
        self.hunk_diff_text = hunk_diff_text
        self.description = "{}:{}".format(file_diff.filename, self.new_line_num)
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

    def filespec(self):
        return "{}:{}".format(self.file_diff.abs_filename, self.new_line_num)

def git_command(args):
    p = subprocess.Popen(['git'] + args,
                         stdout=subprocess.PIPE,
                         shell=True)
    out, err = p.communicate()
    return out.decode('utf-8')
