import sublime
import sublime_plugin
import subprocess
import re
import os

ADD_REGION_KEY = 'diffview-highlight-addition'
MOD_REGION_KEY = 'diffview-highlight-modification'
DEL_REGION_KEY = 'diffview-highlight-deletion'


class DiffView(sublime_plugin.WindowCommand):

    diff_args = ''
    """Main Sublime command for running a diff.

    Asks for input for what to diff against; a Git SHA/branch/tag.
    """

    def run(self):
        self.window.last_diff = self
        self.last_hunk_index = 0
        self.preview = None

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
        if diff_args == '':
            diff_args = 'HEAD'
        self.diff_args = diff_args

        # Record the starting view and position.
        self.orig_view = self.window.active_view()
        self.orig_pos = self.orig_view.sel()[0]
        self.orig_viewport = self.orig_view.viewport_position()

        # Create the diff parser
        cwd = os.path.dirname(self.window.active_view().file_name())
        self.parser = DiffParser(self.diff_args, cwd)

        if not self.parser.changed_hunks:
            # No changes; say so
            sublime.status_message("No changes...")
        else:
            # Show the list of changed hunks
            self.list_changed_hunks()

    def list_changed_hunks(self):
        """Show a list of changed hunks in a quick panel."""
        self.window.show_quick_panel(
            [h.description for h in self.parser.changed_hunks],
            self.show_hunk_diff,
            sublime.MONOSPACE_FONT,
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
            view.erase_regions(ADD_REGION_KEY)
            view.erase_regions(MOD_REGION_KEY)
            view.erase_regions(DEL_REGION_KEY)

        if hunk_index == -1:
            if self.preview:
                self.preview.close()
                self.preview = None

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
        self.window.open_file(hunk.filespec(), sublime.ENCODED_POSITION)

    def preview_hunk(self, hunk_index):
        """Show a preview of the selected hunk.

        Args:
            hunk_index: the selected index in the changed hunks list.
        """
        hunk = self.parser.changed_hunks[hunk_index]
        # TODO - don't think this works when the "already existing" file isn't
        # the active view (it gets closed anyway)...
        already_exists = self.window.find_open_file(hunk.file_diff.filename)
        self.preview = self.window.open_file(
            hunk.filespec(),
            sublime.TRANSIENT | sublime.ENCODED_POSITION)
        if already_exists:
            self.preview = None
        hunk.file_diff.add_regions(self.window.active_view())


class DiffHunksList(sublime_plugin.WindowCommand):
    """Resume the previous diff.

    Displays the list of changed hunks starting from the last hunk viewed.
    """
    def run(self):
        if hasattr(self.window, 'last_diff'):
            self.window.last_diff.list_changed_hunks()


class DiffParser(object):

    STAT_CHANGED_FILE = re.compile('\s*([\w\.\-\/]+)\s*\|')
    """Representation of the entire diff.

    Args:
        diff_args: The arguments to be used for the Git diff.
        cwd: The working directory.
    """

    def __init__(self, diff_args, cwd):
        self.cwd = cwd
        self.git_base = git_command(
            ['rev-parse', '--show-toplevel'], self.cwd).rstrip()
        self.diff_args = diff_args
        self.changed_files = self._get_changed_files()
        self.changed_hunks = []
        for f in self.changed_files:
            self.changed_hunks += f.get_hunks()

    def _get_changed_files(self):
        files = []
        diff_stat = git_command(
            ['diff', '--stat', self.diff_args], self.git_base)
        for line in diff_stat.split('\n'):
            match = self.STAT_CHANGED_FILE.match(line)
            if match:
                filename = match.group(1)
                abs_filename = os.path.join(self.git_base, filename)

                # Get the diff text for this file.
                diff_text = git_command(
                    ['diff',
                     self.diff_args,
                     '-U0',
                     '--minimal',
                     '--word-diff=porcelain',
                     '--',
                     filename],
                    self.git_base)

                files.append(FileDiff(filename, abs_filename, diff_text))
        return files


class FileDiff(object):

    HUNK_MATCH = re.compile('\r?\n@@ \-(\d+),?(\d*) \+(\d+),?(\d*) @@')
    """Representation of a single file's diff.

    Args:
        filename: The filename as given by Git - i.e. relative to the Git base
            directory.
        abs_filename: The absolute filename for this file.
        diff_text: The text of the Git diff.
    """

    def __init__(self, filename, abs_filename, diff_text):
        self.filename = filename
        self.abs_filename = abs_filename
        self.old_file = 'UNDEFINED'
        self.diff_text = diff_text
        self.hunks = []

    def get_hunks(self):
        """Get the changed hunks for this file.

        Wrapper to force parsing only once, and only when the hunks are
        required.
        """
        if not self.hunks:
            self.parse_diff()
        return self.hunks

    def parse_diff(self):
        """Run the Git diff command, and parse the diff for this file into
        hunks.
        """
        hunks = self.HUNK_MATCH.split(self.diff_text)

        # First item is the header - drop it
        hunks.pop(0)
        match_len = 5
        while len(hunks) >= match_len:
            self.hunks.append(HunkDiff(self, hunks[:match_len]))
            hunks = hunks[match_len:]

    def add_regions(self, view):
        """Add all highlighted regions to the view for this file."""
        view.add_regions(
            ADD_REGION_KEY,
            [r for h in self.hunks for r in h.get_regions(view)
                if h.hunk_type == "ADD"],
            "support.class",
            flags=sublime.HIDE_ON_MINIMAP | sublime.DRAW_NO_FILL)
        view.add_regions(
            MOD_REGION_KEY,
            [r for h in self.hunks for r in h.get_regions(view)
                if h.hunk_type == "MOD"],
            "string",
            flags=sublime.DRAW_EMPTY |
            sublime.HIDE_ON_MINIMAP |
            sublime.DRAW_NO_FILL)
        view.add_regions(
            DEL_REGION_KEY,
            [r for h in self.hunks for r in h.get_regions(view)
                if h.hunk_type == "DEL"],
            "invalid",
            flags=sublime.DRAW_EMPTY |
            sublime.HIDE_ON_MINIMAP |
            sublime.DRAW_EMPTY_AS_OVERWRITE |
            sublime.DRAW_NO_FILL)


class HunkDiff(object):

    NEWLINE_MATCH = re.compile('\r?\n')
    LINE_DELIM_MATCH = re.compile('^~')
    ADD_LINE_MATCH = re.compile('^\+(.*)')
    DEL_LINE_MATCH = re.compile('^\-(.*)')
    """Representation of a single 'hunk' from a Git diff.

    Args:
        file_diff: The parent `FileDiff` object.
        match: The match parts of the hunk header.
    """

    def __init__(self, file_diff, match):
        self.file_diff = file_diff
        self.regions = []

        # Matches' meanings are:
        # - 0: start line in old file
        # - 1: num lines removed from old file (0 for ADD, missing if it's a
        #      one-line change)
        # - 2: start line in new file
        # - 3: num lines added to new file (0 for DEL, missing if it's a
        #      one-line change)
        # - 4: the remainder of the hunk, after the header
        self.old_line_start = int(match[0])
        self.old_hunk_len = 1
        if len(match[1]) > 0:
            self.old_hunk_len = int(match[1])
        self.new_line_start = int(match[2])
        self.new_hunk_len = 1
        if len(match[3]) > 0:
            self.new_hunk_len = int(match[3])
        self.context = self.NEWLINE_MATCH.split(match[4])[0]
        self.hunk_diff_lines = self.NEWLINE_MATCH.split(match[4])[1:]

        if self.old_hunk_len == 0:
            self.hunk_type = "ADD"
        elif self.new_hunk_len == 0:
            self.hunk_type = "DEL"
        else:
            self.hunk_type = "MOD"

        # Create the description that will appear in the quick_panel.
        self.description = [
            "{} : {}".format(file_diff.filename, self.new_line_start),
            self.context,
            "{} | {}{}".format(self.old_hunk_len + self.new_hunk_len,
                               "+" * self.new_hunk_len,
                               "-" * self.old_hunk_len)]

    def parse_diff(self):
        """Generate representations of the changed regions."""
        # TODO - create regions for old file too...
        # ADD and DEL are easy.
        if self.hunk_type == "ADD":
            self.regions.append(DiffRegion(
                "ADD",
                self.new_line_start,
                0,
                self.new_line_start + self.new_hunk_len,
                0))
        elif self.hunk_type == "DEL":
            self.regions.append(DiffRegion(
                "DEL",
                self.new_line_start,
                0,
                self.new_line_start + self.new_hunk_len,
                0))
        else:
            # We have a chunk that's not just whole lines...
            # Start by grouping the lines between the '~' lines.
            add_chunks, del_chunks = self.sort_chunks()

            # Handle ADD chunks.
            add_start_line = self.new_line_start
            cur_line = self.new_line_start
            add_start_col = 0
            cur_col = 0
            in_add = False
            for chunk in add_chunks:
                for segment in chunk:
                    if segment.startswith(' '):
                        if in_add:
                            # ADD region ends.
                            self.regions.append(DiffRegion(
                                "ADD",
                                add_start_line,
                                add_start_col,
                                cur_line,
                                cur_col))
                        in_add = False
                        cur_col += len(segment) - 1
                    elif segment.startswith('+'):
                        if not in_add:
                            # ADD region starts.
                            add_start_line = cur_line
                            add_start_col = cur_col
                        in_add = True
                        cur_col += len(segment) - 1
                    else:
                        print("Unexpected segment: {} in {}".format(
                            segment, chunk))

                # End of that line.
                cur_line += 1
                cur_col = 0

            # TODO - Handle DEL chunks too.
            # ...but not interesting when we're only looking at the new file.

    def sort_chunks(self):
        """Sort the sub-chunks in this hunk into those which are interesting
        for ADD regions, and those that are interesting for DEL regions.

        Returns:
            (add_chunks, del_chunks)
        """
        add_chunks = []
        del_chunks = []
        cur_chunk = []
        cur_chunk_has_del = False
        need_newline = False
        for line in self.hunk_diff_lines:
            if line.startswith('~'):
                if need_newline or not cur_chunk_has_del:
                    add_chunks.append(cur_chunk)
                    cur_chunk = []
                    cur_chunk_has_del = False
                    need_newline = False
            elif line.startswith('-'):
                cur_chunk_has_del = True
            else:
                cur_chunk.append(line)
                if line.startswith('+'):
                    need_newline = True

        return (add_chunks, del_chunks)

    def filespec(self):
        """Get the portion of code that this hunk refers to in the format
        `filename:col`.
        """
        return "{}:{}".format(self.file_diff.abs_filename, self.new_line_start)

    def get_regions(self, view):
        """Create a `sublime.Region` for each part of this hunk."""
        if not self.regions:
            self.parse_diff()
        return [sublime.Region(
            view.text_point(r.start_line - 1, r.start_col),
            view.text_point(r.end_line - 1, r.end_col)) for r in self.regions]


class DiffRegion(object):
    """Class representing a region that's changed.

    Args:
        type: "ADD", "MOD" or "DEL"
        start_line: The line where the region starts
        start_col: The column where the region starts
        end_line: The line where the region ends
        end_col: The column where the region ends
    """

    def __init__(self, diff_type, start_line, start_col, end_line, end_col):
        self.diff_type = diff_type
        self.start_line = start_line
        self.start_col = start_col
        self.end_line = end_line
        self.end_col = end_col


def git_command(args, cwd):
    """Wrapper to run a Git command."""
    p = subprocess.Popen(['git'] + args,
                         stdout=subprocess.PIPE,
                         shell=True,
                         cwd=cwd)
    out, err = p.communicate()
    return out.decode('utf-8')
