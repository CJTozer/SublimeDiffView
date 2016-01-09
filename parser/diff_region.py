class DiffRegion(object):
    """Class representing a region that's changed."""

    def __init__(self, diff_type, start_line, start_col, end_line, end_col):
        """Constructor.

        Args:
            type: "ADD", "MOD" or "DEL"
            start_line: The line where the region starts
            start_col: The column where the region starts
            end_line: The line where the region ends
            end_col: The column where the region ends
        """
        self.diff_type = diff_type
        self.start_line = start_line
        self.start_col = start_col
        self.end_line = end_line
        self.end_col = end_col
