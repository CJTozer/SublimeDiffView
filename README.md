# DiffView for Sublime Text 3
*Git and SVN Diff Viewer for Sublime Text 3*
[![Build Status](https://travis-ci.org/CJTozer/SublimeDiffView.svg)](https://travis-ci.org/CJTozer/SublimeDiffView)

## Features
* Side-by-side view with differences highlighted
* Quick navigation from one change to the next, or search for diffs in a specific file
* Flexible diffs for both Git and SVN (see below for the full set of options)
* The most common diff (uncommitted changes) is the quickest to use

## Screenshot

![Screenshot](https://raw.githubusercontent.com/CJTozer/SublimeDiffView/master/img/screen_1.png "Screenshot from Git diff")

## Usage
* `Alt + Shift + D` to run a diff
    * *See below for supported diff options*
    * This lists all the changed hunks, and shows you a preview as you move down the list
    * You can search for a particular file in the list of hunks, which will filter the results
    * Hit `Enter` to jump to the currently selected diff
    * hit `Esc` to cancel the Diff View, and return to where you were
* `Alt + D` to review the last diff
    * This will show the list of hunks from the last diff, starting from the last hunk you selected

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
* `-c 234`
    * show changes made in commit 234
