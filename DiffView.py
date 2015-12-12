import sublime
import sublime_plugin
import subprocess
import re
import os
import tempfile
import time
import threading

ADD_REGION_KEY = 'diffview-highlight-addition'
MOD_REGION_KEY = 'diffview-highlight-modification'
DEL_REGION_KEY = 'diffview-highlight-deletion'

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
            sublime.MONOSPACE_FONT,
            self.last_hunk_index,
            self.preview_hunk)

    def show_hunk_diff(self, index):
        self.window.active_view().erase_regions(ADD_REGION_KEY)
        self.window.active_view().erase_regions(MOD_REGION_KEY)
        self.window.active_view().erase_regions(DEL_REGION_KEY)

        if index == -1:
            if self.preview:
                self.preview.close()
                self.preview = None
            return
        self.last_hunk_index = index
        hunk = self.parser.changed_hunks[index]
        self.window.open_file(hunk.filespec(), sublime.ENCODED_POSITION)

    def preview_hunk(self, index):
        self.window.active_view().erase_regions(ADD_REGION_KEY)
        self.window.active_view().erase_regions(MOD_REGION_KEY)
        self.window.active_view().erase_regions(DEL_REGION_KEY)

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
    HUNK_MATCH = re.compile('\r?\n@@ \-(\d+),?(\d*) \+(\d+),?(\d*) @@')

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
            self.diff_text = git_command(['diff', self.diff_args, '-U0', '--minimal', '--word-diff=porcelain', '--', self.filename])
            hunks = self.HUNK_MATCH.split(self.diff_text)

            # First item is the header - drop it
            hunks.pop(0)
            match_len = 5
            while len(hunks) >= match_len:
                self.hunks.append(HunkDiff(self, hunks[:match_len]))
                hunks = hunks[match_len:]

    def add_regions(self, view):
        view.add_regions(
            ADD_REGION_KEY,
            [h.get_region(view) for h in self.hunks if h.hunk_type == "ADD"],
            "support.class",
            flags=sublime.HIDE_ON_MINIMAP | sublime.DRAW_NO_FILL)
        view.add_regions(
            MOD_REGION_KEY,
            [h.get_region(view) for h in self.hunks if h.hunk_type == "MOD"],
            "string",
            flags=sublime.HIDE_ON_MINIMAP | sublime.DRAW_NO_FILL)
        view.add_regions(
            DEL_REGION_KEY,
            [h.get_region(view) for h in self.hunks if h.hunk_type == "DEL"],
            "invalid",
            flags=sublime.DRAW_EMPTY | sublime.HIDE_ON_MINIMAP | sublime.DRAW_EMPTY_AS_OVERWRITE | sublime.DRAW_NO_FILL)

class HunkDiff(object):
    NEWLINE_MATCH = re.compile('\r?\n')
    LINE_DELIM_MATCH = re.compile('\r?\n~\r?\n')
    ADD_LINE_MATCH = re.compile('^\+(.*)')
    DEL_LINE_MATCH = re.compile('^\-(.*)')

    def __init__(self, file_diff, match):
        self.file_diff = file_diff

        # Maches' meanings are:
        # - 0: start line in old file
        # - 1: num lines removed from old file (0 for ADD, missing if it's a one-line change)
        # - 2: start line in new file
        # - 3: num lines added to new file (0 for DEL, missing if it's a one-line change)
        # - 4: the remainder of the hunk, after the header
        self.old_line_start = int(match[0])
        self.old_hunk_len = 1
        if len(match[1]) > 0:
            self.old_hunk_len = int(match[1])
        self.new_line_start = int(match[2])
        self.new_hunk_len = 1
        if len(match[3]) > 0:
            self.new_hunk_len = int(match[3])
        self.hunk_diff_lines = self.NEWLINE_MATCH.split(match[4])

        if self.old_hunk_len == 0:
            self.hunk_type = "ADD"
        elif self.new_hunk_len == 0:
            self.hunk_type = "DEL"
        else:
            self.hunk_type = "MOD"

        self.description = [
            "{}:{}".format(file_diff.filename, self.new_line_start),
            self.hunk_diff_lines[0],
            "{} | {}{}".format(self.old_hunk_len + self.new_hunk_len,
                               "+" * self.new_hunk_len,
                               "-" * self.old_hunk_len)]

    def parse_diff(self):
        # TODO - more detailed diffs (better than just line-by-line)
        # Need to track line number (and character position) as we run through the regions.
        # Multiline adds and deletes are spread over multiple regions.
        old_line_num = self.old_line_start
        new_line_num = self.new_line_start
        for region in self.LINE_DELIM_MATCH.split(self.hunk_diff_text):
            print("$$$$" + region + "&&&&")
            add_match = self.ADD_LINE_MATCH.match(region)
            del_match = self.DEL_LINE_MATCH.match(region)

    def filespec(self):
        return "{}:{}".format(self.file_diff.abs_filename, self.new_line_start)

    def get_region(self, view):
        return sublime.Region(
            view.text_point(self.new_line_start - 1, 0),
            view.text_point(self.new_line_start + self.new_hunk_len - 1, 0))

def git_command(args):
    p = subprocess.Popen(['git'] + args,
                         stdout=subprocess.PIPE,
                         shell=True)
    out, err = p.communicate()
    return out.decode('utf-8')
