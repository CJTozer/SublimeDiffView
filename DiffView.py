import sublime
import sublime_plugin
import subprocess
import re

class DiffView(sublime_plugin.WindowCommand):
    last_diff = ''

    def run(self):
        print("TESTING!!!")

        # Use this as show_quick_panel doesn't allow arbitrary data
        self.window.show_input_panel("Diff parameters?", self.last_diff, self.do_diff, None, None)

    def do_diff(self, diff_args):
        if diff_args == '':
            diff_args = 'HEAD'
        print("Diff args: %s" % diff_args)
        self.last_diff = diff_args

        parser = DiffParser(diff_args)

        for f in parser.changed_files():
            print("File {} has changed".format(f))

class DiffParser(object):
    STAT_CHANGED_FILE = re.compile('\s*([\w\.]+)\s*\|')

    def __init__(self, diff_args):
        self.diff_args = diff_args

    def changed_files(self):
        for line in git_command(['diff', '--stat', self.diff_args]).split('\n'):
            match = self.STAT_CHANGED_FILE.match(line)
            if match:
                yield match.group(1)

def git_command(args):
    p = subprocess.Popen(['git'] + args,
                         stdout=subprocess.PIPE)
    out, err = p.communicate()
    return out.decode('utf-8')
