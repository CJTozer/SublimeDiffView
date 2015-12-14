# SublimeDiffView
Diff Viewer for Sublime Text 3

## Usage
* `Alt + Shift + D` to run a diff
* `Alt + D` to review the last diff

## TODO
* Side-by-side view of old and new file.  See [#1](https://github.com/CJTozer/SublimeDiffView/issues/1).
* This is all Git specific; maybe even one version of Git specific - WIBNI if this worked more generally?
* More diff options:
    * Cope with `master..` as a merge base - simply treat as `master`
    * Handle non-simple comparisons - i.e. `branch_a..branch_b` where `branch_b` isn't the current branch.
    * Have the option to get the merge base before diffing - i.e. when the user asks for `master...` as the diff base, work out that that means compare agains the merge base...
    * Most of these mostly work - the changes required are for when the RHS isn't `HEAD` - in which case we need to show a different version of the file for the preview.  And in that case it probably makes sense to do something different when selecting from the list - maintain the highlighting and open read-only maybe?
