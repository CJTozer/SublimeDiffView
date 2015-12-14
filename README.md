# SublimeDiffView
Diff Viewer for Sublime Text 3

## Usage
* `Alt + Shift + D` to run a diff
* `Alt + D` to review the last diff

## TODO
* Side-by-side view of old and new file.  See [#1](https://github.com/CJTozer/SublimeDiffView/issues/1).
* This is all Git specific; maybe even one version of Git specific - WIBNI if this worked more generally?
* Cope with `master..` as a merge base - simply treat as `master`
* Handle non-simple comparisons - i.e. `branch_a..branch_b` where `branch_b` isn't the current branch.
* Have the option to get the merge base before diffing - i.e. when the user asks for `master...` as the diff base, work out that that means compare agains the merge base...
