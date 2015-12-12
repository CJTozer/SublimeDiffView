# SublimeDiffView
Diff Viewer for Sublime Text 3

## Usage
* `Alt + Shift + D` to run a diff
* `Alt + D` to review the last diff

## TODO
* Try side-by-side
    - Push the 'old' version into a temporary file.  See [old rev 1a16c41d](https://github.com/CJTozer/SublimeDiffView/blob/1a16c41d029c0919a94f177be6904d307840698e/DiffView.py) - but note that it looks like open_file can take a group parameter.  That was the missing factor earlier, as messing with the "active" group interrupted the plugin.
* More detail - i.e. using the `--word-diff=porcelain` output to go finer-grained than just line-by-line diffs.
* This is all Git specific; maybe even one version of Git specific - WIBNI if this worked more generally?
