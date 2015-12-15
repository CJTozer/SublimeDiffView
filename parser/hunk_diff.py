import re
import sublime

from .diff_region import DiffRegion


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
        self.old_regions = []
        self.new_regions = []

        # Matches' meanings are:
        # - 0: start line in old file
        self.old_line_start = int(match[0])
        # - 1: num lines removed from old file (0 for ADD, missing if it's a
        #      one-line change)
        self.old_hunk_len = 1
        if len(match[1]) > 0:
            self.old_hunk_len = int(match[1])
        # - 2: start line in new file
        self.new_line_start = int(match[2])
        # - 3: num lines added to new file (0 for DEL, missing if it's a
        #      one-line change)
        self.new_hunk_len = 1
        if len(match[3]) > 0:
            self.new_hunk_len = int(match[3])
        # - 4: the remainder of the hunk, after the header
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
        # ADD and DEL are easy.
        if self.hunk_type == "ADD":
            self.old_regions.append(DiffRegion(
                "DEL",
                self.old_line_start,
                0,
                self.old_line_start + self.old_hunk_len,
                0))
            self.new_regions.append(DiffRegion(
                "ADD",
                self.new_line_start,
                0,
                self.new_line_start + self.new_hunk_len,
                0))
        elif self.hunk_type == "DEL":
            self.old_regions.append(DiffRegion(
                "ADD",
                self.old_line_start,
                0,
                self.old_line_start + self.old_hunk_len,
                0))
            self.new_regions.append(DiffRegion(
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
                            self.new_regions.append(DiffRegion(
                                "ADD",
                                add_start_line,
                                add_start_col,
                                cur_line,
                                cur_col))
                            # Add a blank DEL region to the old regions.
                            self.old_regions.append(DiffRegion(
                                "DEL",
                                self.old_line_start,
                                add_start_col,
                                self.old_line_start,
                                add_start_col))
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

            # Handle DEL chunks.
            del_start_line = self.old_line_start
            cur_line = self.old_line_start - 1
            del_start_col = 0
            cur_col = 0
            in_del = False
            for chunk in del_chunks:
                # End of that line.  Do this here (and minus 1 above) to make
                # catching the final chunk easier.
                cur_line += 1
                cur_col = 0

                for segment in chunk:
                    if segment.startswith(' '):
                        if in_del:
                            # DEL region ends.
                            self.old_regions.append(DiffRegion(
                                "DEL",
                                del_start_line,
                                del_start_col,
                                cur_line,
                                cur_col))
                            # Add a blank ADD region to the new regions.
                            self.new_regions.append(DiffRegion(
                                "ADD",
                                self.new_line_start,
                                del_start_col,
                                self.new_line_start,
                                del_start_col))
                        in_del = False
                        cur_col += len(segment) - 1
                        # Workaround a weird problem in Git diff
                        if not segment.endswith(' '):
                            cur_col += 1
                    elif segment.startswith('-'):
                        if not in_del:
                            # DEL region starts.
                            del_start_line = cur_line
                            del_start_col = cur_col
                        in_del = True
                        cur_col += len(segment) - 1
                    else:
                        print("Unexpected segment: {} in {}".format(
                            segment, chunk))

            if in_del:
                # Add the last chunk in...
                self.old_regions.append(DiffRegion(
                    "DEL",
                    del_start_line,
                    del_start_col,
                    cur_line,
                    cur_col))

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
        cur_chunk_has_add = False
        need_newline = False

        # ADD chunks
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

        # DEL chunks
        cur_chunk = []
        for line in self.hunk_diff_lines:
            if line.startswith('~'):
                if need_newline or not cur_chunk_has_add:
                    print(cur_chunk)
                    del_chunks.append(cur_chunk)
                    cur_chunk = []
                    cur_chunk_has_add = False
                    need_newline = False
            elif line.startswith('+'):
                cur_chunk_has_add = True
            else:
                cur_chunk.append(line)
                if line.startswith('-'):
                    need_newline = True

        return (add_chunks, del_chunks)

    def filespecs(self):
        """Get the portion of code that this hunk refers to in the format
        `(old_filename:old_line, new_filename:new_line`.
        """
        old_filespec = "{}:{}".format(
            self.file_diff.old_file,
            self.old_line_start)
        new_filespec = "{}:{}".format(
            self.file_diff.abs_filename,
            self.new_line_start)
        return (old_filespec, new_filespec)

    def get_old_regions(self, view):
        """Create a `sublime.Region` for each (old) part of this hunk."""
        if not self.old_regions:
            self.parse_diff()
        return [sublime.Region(
            view.text_point(r.start_line - 1, r.start_col),
            view.text_point(r.end_line - 1, r.end_col))
            for r in self.old_regions]

    def get_new_regions(self, view):
        """Create a `sublime.Region` for each (new) part of this hunk."""
        if not self.new_regions:
            self.parse_diff()
        return [sublime.Region(
            view.text_point(r.start_line - 1, r.start_col),
            view.text_point(r.end_line - 1, r.end_col))
            for r in self.new_regions]
