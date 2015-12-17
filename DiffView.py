import sublime
import sublime_plugin
import os
import threading
import time

from .util.view_finder import ViewFinder
from .util.constants import Constants
from .parser.diff_parser import DiffParser


class DiffView(sublime_plugin.WindowCommand):

    diff_args = ''
    """Main Sublime command for running a diff.

    Asks for input for what to diff against; a Git SHA/branch/tag.
    """

    def run(self):
        self.window.last_diff = self
        self.last_hunk_index = 0

        # Use show_input_panel as show_quick_panel doesn't allow arbitrary data
        self.window.show_input_panel(
            "Diff against? [HEAD]",
            self.diff_args,
            self.do_diff,
            None,
            None)

    def do_diff(self, diff_args):
        """Compare the current codebase with the `diff_args`.

        Args:
            diff_args: the base SHA/tag/branch to compare against.
        """
        self.diff_args = diff_args
        if diff_args == '':
            diff_args = 'HEAD'

        # Create the diff parser
        cwd = os.path.dirname(self.window.active_view().file_name())
        self.parser = DiffParser(self.diff_args, cwd)

        if not self.parser.changed_hunks:
            # No changes; say so
            sublime.message_dialog("No changes to report...")
        else:
            # Show the list of changed hunks
            self.list_changed_hunks()

    def list_changed_hunks(self):
        """Show a list of changed hunks in a quick panel."""
        # Record the starting view and position.
        self.orig_view = self.window.active_view()
        self.orig_pos = self.orig_view.sel()[0]
        self.orig_viewport = self.orig_view.viewport_position()

        # Store old layout, then set layout to 2 columns.
        self.orig_layout = self.window.layout()
        self.window.set_layout(
            {"cols": [0.0, 0.5, 1.0],
             "rows": [0.0, 1.0],
             "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]})

        # Start listening for the quick panel creation, then create it.
        ViewFinder.instance().start_listen(self.quick_panel_found)
        self.window.show_quick_panel(
            [h.description for h in self.parser.changed_hunks],
            self.show_hunk_diff,
            sublime.MONOSPACE_FONT | sublime.KEEP_OPEN_ON_FOCUS_LOST,
            self.last_hunk_index,
            self.preview_hunk)

    def show_hunk_diff(self, hunk_index):
        """Open the location of the selected hunk.

        Removes any diff highlighting shown in the previews.

        Args:
            hunk_index: the selected index in the changed hunks list.
        """
        # Remove diff highlighting from all views.
        for view in self.window.views():
            view.erase_regions(Constants.ADD_REGION_KEY)
            view.erase_regions(Constants.MOD_REGION_KEY)
            view.erase_regions(Constants.DEL_REGION_KEY)

        # Reset the layout.
        self.window.set_layout(self.orig_layout)

        if hunk_index == -1:
            # Return to the original view/selection
            self.window.focus_view(self.orig_view)
            self.orig_view.sel().clear()
            self.orig_view.sel().add(self.orig_pos)
            self.orig_view.set_viewport_position(
                self.orig_viewport,
                animate=False)
            return

        self.last_hunk_index = hunk_index
        hunk = self.parser.changed_hunks[hunk_index]
        (_, new_filespec) = hunk.filespecs()
        self.window.open_file(new_filespec, sublime.ENCODED_POSITION)

    def preview_hunk(self, hunk_index):
        """Show a preview of the selected hunk.

        Args:
            hunk_index: the selected index in the changed hunks list.
        """
        hunk = self.parser.changed_hunks[hunk_index]
        (old_filespec, new_filespec) = hunk.filespecs()

        def highlight_when_ready(view, highlight_fn):
            while view.is_loading():
                time.sleep(0.1)
            highlight_fn(view)

        right_view = self.window.open_file(
            new_filespec,
            flags=sublime.TRANSIENT |
            sublime.ENCODED_POSITION |
            sublime.FORCE_GROUP,
            group=1)
        t = threading.Thread(
            target=highlight_when_ready,
            args=(right_view, hunk.file_diff.add_new_regions))
        t.start()

        left_view = self.window.open_file(
            old_filespec,
            flags=sublime.TRANSIENT |
            sublime.ENCODED_POSITION |
            sublime.FORCE_GROUP,
            group=0)
        left_view.set_read_only(True)
        t = threading.Thread(
            target=highlight_when_ready,
            args=(left_view, hunk.file_diff.add_old_regions))
        t.start()

        # Keep the focus in the quick panel
        self.window.focus_group(0)
        self.window.focus_view(self.qpanel)

    def quick_panel_found(self, view):
        """Callback to store the quick panel when found.

        Args:
            view: The quick panel view.
        """
        self.qpanel = view


class DiffHunksList(sublime_plugin.WindowCommand):
    """Resume the previous diff.

    Displays the list of changed hunks starting from the last hunk viewed.
    """
    def run(self):
        if hasattr(self.window, 'last_diff'):
            self.window.last_diff.list_changed_hunks()
