# DiffView for Sublime Text 3
*Git and SVN Diff Viewer for Sublime Text 3*  
[![Build Status](https://travis-ci.org/CJTozer/SublimeDiffView.svg)](https://travis-ci.org/CJTozer/SublimeDiffView)

## Features
* Side-by-side view with differences highlighted
* Quick navigation from one change to the next, or search for diffs in a specific file
* Auto-detects the repository to use from the current active file
* Flexible diffs for both Git and SVN (see below for the full set of options)
* The most common diff (uncommitted changes) is the quickest to use

## Screenshot

![Screenshot](https://raw.githubusercontent.com/CJTozer/SublimeDiffView/master/img/screen_1.png "Screenshot from Git diff")

## Installation

1. Install the Sublime Text [Package Control](https://packagecontrol.io/installation) plugin if you don't have it already
2. Open the command palette and start typing `Package Control: Install Package`
3. Enter `DiffView`

## Usage
* See options under "DiffView" in the Command Palette, and also the following keyboard shortcuts
* `Alt + Shift + D` to run a diff
    * *See below for supported diff options*
    * This lists all the changes, and shows you a preview as you move down the list
    * You can search for a particular file in the list of changes, which will filter the results
    * Hit `Enter` to jump to the currently selected change
    * hit `Esc` to cancel the DiffView, and return to where you were
* `Alt + D` to review the last diff
    * This will show the list of changes from the last diff, starting from the last change you previewed

## Supported Diff Options

### Git
* *Default* (when there's no input): comparison of wc against `HEAD` - i.e. show unstaged changes
* `HEAD` or `branch` or `SHA` or `tag`
    * compare working copy against `HEAD`/`branch`/`SHA`/`tag`
* `branch..`
    * compare `branch` with wc
* `..branch`
    * compare working copy with `branch`
* `branch_a..branch_b`
    * compare `branch_a` with `branch_b`
* `branch...`
    * compare the merge-base of the working copy and `branch` with the working copy
* `branch_a...branch_b`
    * compare the merge-base of `branch_a` and `branch_b` with `branch_b`

### SVN
* *Default* (when there's no input): show uncommitted changes
* `-r 123`
    * compare revision 123 with the latest revision (not the working copy)
* `-r 123:234`
    * compare revision 123 with revision 234
* `-c 234`
    * show changes made in commit 234
* `--cl issue1234`
    * show uncommitted changes on changelist `issue1234`

## Feedback

This plugin is still in active development.  If you have any issues, comments, or feature suggestions, please raise them [on GitHub](https://github.com/CJTozer/SublimeDiffView/issues).  All feedback gratefully received.
