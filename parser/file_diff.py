import re

from .hunk_diff import HunkDiff
from ..util.constants import Constants


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
        self.new_file = 'UNDEFINED'
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

    def add_old_regions(self, view):
        """Add all highlighted regions to the view for this (old) file."""
        view.add_regions(
            Constants.ADD_REGION_KEY,
            [r for h in self.hunks for r in h.get_old_regions(view)
                if h.hunk_type == "ADD"],
            Constants.ADD_REGION_STYLE,
            flags=Constants.ADD_REGION_FLAGS)
        view.add_regions(
            Constants.MOD_REGION_KEY,
            [r for h in self.hunks for r in h.get_old_regions(view)
                if h.hunk_type == "MOD"],
            Constants.MOD_REGION_STYLE,
            flags=Constants.MOD_REGION_FLAGS)
        view.add_regions(
            Constants.DEL_REGION_KEY,
            [r for h in self.hunks for r in h.get_old_regions(view)
                if h.hunk_type == "DEL"],
            Constants.DEL_REGION_STYLE,
            flags=Constants.DEL_REGION_FLAGS)

    def add_new_regions(self, view):
        """Add all highlighted regions to the view for this (new) file."""
        view.add_regions(
            Constants.ADD_REGION_KEY,
            [r for h in self.hunks for r in h.get_new_regions(view)
                if h.hunk_type == "ADD"],
            Constants.ADD_REGION_STYLE,
            flags=Constants.ADD_REGION_FLAGS)
        view.add_regions(
            Constants.MOD_REGION_KEY,
            [r for h in self.hunks for r in h.get_new_regions(view)
                if h.hunk_type == "MOD"],
            Constants.MOD_REGION_STYLE,
            flags=Constants.MOD_REGION_FLAGS)
        view.add_regions(
            Constants.DEL_REGION_KEY,
            [r for h in self.hunks for r in h.get_new_regions(view)
                if h.hunk_type == "DEL"],
            Constants.DEL_REGION_STYLE,
            flags=Constants.DEL_REGION_FLAGS)
