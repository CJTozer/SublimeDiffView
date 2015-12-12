import sublime
import sublime_plugin
import subprocess
import re
import os
import tempfile
import time
import threading

class DiffView(sublime_plugin.ApplicationCommand):
    diff_base = ''

    def run(self):
        self.git_base = git_command(['rev-parse', '--show-toplevel']).rstrip()
        sublime.active_window().last_diff = self
        self.last_file_index = 0
        self.preview = None

        # Create a temporary directory for (read-only) old versions of changed files
        self.temp_dir = tempfile.mkdtemp()

        # Use show_input_panel as show_quick_panel doesn't allow arbitrary data
        sublime.active_window().show_input_panel("Diff against? [HEAD]", self.diff_base, self.do_diff, None, None)

    def do_diff(self, diff_base):
        if diff_base == '':
            diff_base = 'HEAD'
        self.diff_base = diff_base

        # Record the original layout
        self.orig_layout = sublime.active_window().get_layout()

        # Create the diff parser
        self.parser = DiffParser(self.diff_base)

        # Create the old files in the temporary directory
        self.create_old_files()

        # Show the list of changed files
        self.list_changed_files()

    def create_old_files(self):
        for changed_file in self.parser.changed_files:
            target_dir = os.path.join(self.temp_dir, os.path.dirname(changed_file.filename))
            changed_file.old_file = os.path.join(self.temp_dir, changed_file.filename)
            if not os.path.exists(target_dir):
                os.makedirs(os.path.join(self.temp_dir, os.path.dirname(changed_file.filename)))
            with open(changed_file.old_file, 'w') as f:
                git_args = ['show', '{}:{}'.format(self.diff_base, changed_file.filename)]
                old_file_content = git_command(git_args)
                f.write(old_file_content.replace('\r\n', '\n'))

    def list_changed_files(self):
        print(self.parser.changed_files)
        sublime.active_window().show_quick_panel(
            [f.filename for f in self.parser.changed_files],
            self.show_file_diff,
            0,
            self.last_file_index,
            self.preview_diff)

    def show_file_diff(self, index):
        print("show_file_diff: {}".format(index))
        if index == -1:
            # Reset the layout
            self.preview_old_file.close()
            sublime.active_window().set_layout(self.orig_layout)
            return

        self.last_file_index = index
        changed_file = self.parser.changed_files[index]
        sublime.active_window().open_file(changed_file.old_file)
        # sublime.ENCODED_POSITION flag will look for "file:line:col", which will be useful later.


    def preview_diff(self, index):
        changed_file = self.parser.changed_files[index]

        sublime.active_window().set_layout( { "cols": [0.0, 0.5, 1.0], "rows": [0.0, 1.0], "cells": [[0, 0, 1, 1], [1, 0, 2, 1]] } )
        #new_file_abs = os.path.join(self.git_base, changed_file.filename)
        #self.preview_new_file = sublime.active_window().open_file(new_file_abs, sublime.TRANSIENT)
        self.preview_old_file = sublime.active_window().open_file(changed_file.old_file)#, sublime.TRANSIENT)

        # Wait for the view to load
        def move_old_view():
            print("Starting THREAD")
            while self.preview_old_file.is_loading():
                time.sleep(0.1)
            print("Moving view")
            print(sublime.active_window().active_group())
            #sublime.active_window().set_view_index(self.preview_old_file, 1, 0)

        threading.Thread(target=move_old_view).start()

        #sublime.active_window().set_view_index(self.preview_new_file, 1, 0)
        # sublime.ENCODED_POSITION flag will look for "file:line:col", which will be useful later.

class DiffFilesList(sublime_plugin.WindowCommand):
    def run(self):
        if hasattr(sublime.active_window(), 'last_diff'):
            sublime.active_window().last_diff.list_changed_files()

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
        self.old_file = 'UNDEFINED'
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
    p = subprocess.Popen(['git'] + args,
                         stdout=subprocess.PIPE,
                         shell=True)
    out, err = p.communicate()
    return out.decode('utf-8')
