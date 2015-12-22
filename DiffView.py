import sublime
import sublime_plugin
import os
import threading
import time
import tempfile

from .util.view_finder import ViewFinder
from .util.constants import Constants
from .util.vcs import NoVCSError
from .parser.diff_parser import DiffParser


class DiffView(sublime_plugin.WindowCommand):

    diff_args = ''
    """Main Sublime command for running a diff.

    Asks for input for what to diff against; a Git SHA/branch/tag.
    """

    def _prepare(self):
        """Some preparation common to all subclasses."""
        self.window.last_diff = self
        self.last_hunk_index = 0
        self.settings = sublime.load_settings('DiffView.sublime-settings')
        self.view_style = self.settings.get("view_style", "quick_panel")

        # Set up the groups
        self.list_group = 0
        if self.view_style == "quick_panel":
            self.diff_layout = {
                "cols": [0.0, 0.5, 1.0],
                "rows": [0.0, 1.0],
                "cells": [
                    [0, 0, 1, 1],
                    [1, 0, 2, 1]]}
            self.diff_list_group = None
            self.lhs_group = 0
            self.rhs_group = 1
        elif self.view_style == "persistent_list":
            self.diff_layout = {
                "cols": [0.0, 0.5, 1.0],
                "rows": [0.0, 0.25, 1.0],
                "cells": [
                    [0, 0, 2, 1],
                    [0, 1, 1, 2],
                    [1, 1, 2, 2]]}
            self.diff_list_group = 0
            self.lhs_group = 1
            self.rhs_group = 2
        else:
            sublime.error_message(
                "Invalid value '{}'' for 'view_style'".format(
                    self.view_style))
            raise ValueError("Invalid 'view_style': '{}'".format(
                self.view_style))

    def run(self):
        self._prepare()

        # Use show_input_panel as show_quick_panel doesn't allow arbitrary data
        self.window.show_input_panel(
            "Diff arguments?",
            self.diff_args,
            self.do_diff,
            None,
            None)

    def do_diff(self, diff_args):
        """Run a diff and display the changes.

        Args:
            diff_args: the arguments to the diff.
        """
        self.diff_args = diff_args

        try:
            # Create the diff parser
            cwd = os.path.dirname(self.window.active_view().file_name())
            self.parser = DiffParser(self.diff_args, cwd)
        except NoVCSError:
            # No changes; say so
            sublime.message_dialog(
                "This file does not appear to be under version control " +
                "(Git or SVN).")
            return

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
        self.window.set_layout(self.diff_layout)

        if self.view_style == "quick_panel":
            # Start listening for the quick panel creation, then create it.
            ViewFinder.instance().start_listen(self.quick_panel_found)
            self.window.show_quick_panel(
                [h.description for h in self.parser.changed_hunks],
                self.show_hunk_diff,
                sublime.MONOSPACE_FONT | sublime.KEEP_OPEN_ON_FOCUS_LOST,
                self.last_hunk_index,
                self.preview_hunk)
        else:
            # Put the hunks list in the top panel
            self.changes_list_file = tempfile.mkstemp()[1]
            with open(self.changes_list_file, 'w') as f:
                changes_list = "\n".join(
                    [h.oneline_description for h in self.parser.changed_hunks])
                f.write(changes_list)
            self.changes_list_view = self.window.open_file(
                self.changes_list_file,
                flags=sublime.TRANSIENT |
                sublime.FORCE_GROUP,
                group=self.list_group)
            self.changes_list_view.set_read_only(True)
            self.changes_list_view.set_scratch(True)

            # Move cursor to the last selected diff when the file is ready
            def select_latest_diff_when_ready(view):
                while view.is_loading():
                    time.sleep(0.1)

                # Force a change in position - so the selection change event
                # always triggers.
                view.sel().clear()
                view.sel().add(sublime.Region(1, 1))
                view.run_command(
                    "show_diff_list",
                    args={'last_selected': self.last_hunk_index})

            # Listen for changes to this view's selection.
            DiffViewEventListner.instance().start_listen(
                self.preview_hunk,
                self.changes_list_view,
                self)

            # Choose the last selected change, when the view's ready
            t = threading.Thread(
                target=select_latest_diff_when_ready,
                args=(self.changes_list_view,))
            t.start()

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

        if hunk_index == -1:
            self.reset_window()
            return

        # Reset the layout.
        self.window.set_layout(self.orig_layout)
        if self.view_style == "persistent_list":
            self.changes_list_view.close()

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
            group=self.rhs_group)
        t = threading.Thread(
            target=highlight_when_ready,
            args=(right_view, hunk.file_diff.add_new_regions))
        t.start()

        left_view = self.window.open_file(
            old_filespec,
            flags=sublime.TRANSIENT |
            sublime.ENCODED_POSITION |
            sublime.FORCE_GROUP,
            group=self.lhs_group)
        t = threading.Thread(
            target=highlight_when_ready,
            args=(left_view, hunk.file_diff.add_old_regions))
        t.start()

        self.window.focus_group(0)
        if self.view_style == "quick_panel":
            # Keep the focus in the quick panel
            self.window.focus_view(self.qpanel)

    def reset_window(self):
        """Reset the window to its original state."""
        # Return to the original layout/view/selection
        if self.view_style == "persistent_list":
            self.changes_list_view.close()
        self.window.set_layout(self.orig_layout)
        self.window.focus_view(self.orig_view)
        self.orig_view.sel().clear()
        self.orig_view.sel().add(self.orig_pos)
        self.orig_view.set_viewport_position(
            self.orig_viewport,
            animate=False)

        # Stop listening for events
        ViewFinder.instance().stop()
        DiffViewEventListner.instance().stop()
        self.qpanel = None

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


class DiffCancel(sublime_plugin.WindowCommand):
    """Cancel the current diff."""
    def run(self):
        if hasattr(self.window, 'last_diff'):
            self.window.last_diff.reset_window()


class DiffShowSelected(sublime_plugin.WindowCommand):
    """Show the change that's curently selected by this view."""
    def run(self):
        if hasattr(self.window, 'last_diff'):
            self.window.last_diff.show_hunk_diff(
                DiffViewEventListner.instance().current_row)


class DiffViewUncommitted(DiffView):
    """Command to display a simple diff of uncommitted changes."""
    def run(self):
        self._prepare()
        self.do_diff('')


class ShowDiffListCommand(sublime_plugin.TextCommand):
    """Command to show the diff list.

    Args:
        changes_list: The text of the changes list.
        last_selected: The last selected change (zero indexed).
    """
    def run(self, edit, last_selected):
        # Move cursor to the last selected diff
        self.view.sel().clear()
        pos = self.view.text_point(last_selected, 0)
        self.view.sel().add(sublime.Region(pos, pos))


class DiffViewEventListner(sublime_plugin.EventListener):
    _instance = None

    """Helper class for catching events during a diff."""
    def __init__(self):
        self.__class__._instance = self
        self._listening = False
        self.current_row = -1

    def on_selection_modified_async(self, view):
        """Called when a selection has been modified.

        Only interested if this is the change list view.
        """
        if self._listening and view == self.view:
            current_selection = view.sel()[0]
            (self.current_row, _) = view.rowcol(current_selection.a)
            # rowcol is zero indexed, so line 1 gives index zero - perfect
            self.diff.preview_hunk(self.current_row)

    def on_query_context(self, view, key, operator, operand, match_all):
        """Context queries mean someone is trying to work out whether to
        override key bindings.

        The bindings that are overridden are as follows:
        - escape -> "cancel_diff" when a diff is running
        - enter -> "show_hunk" when in the changes list view
        """
        if key == "diff_running":
            return self._listening
        elif key == "diff_changes_list":
            return self._listening and view == self.view
        return None

    @classmethod
    def instance(cls):
        if cls._instance:
            return cls._instance
        else:
            return cls()

    def start_listen(self, cb, view, diff):
        """Start listening for the changes list.

        Args:
            cb: The callback to call when a widget is created.
            view: The view to listen for.
            diff: The diff currently being run.
        """
        self.cb = cb
        self.view = view
        self.diff = diff
        self._listening = True

    def stop(self):
        """Stop listening."""
        self._listening = False
