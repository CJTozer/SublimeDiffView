import sublime
import sublime_plugin

class DiffView(sublime_plugin.WindowCommand):
    last_diff = ''

    def run(self):
        print("TESTING!!!")

        # Use this as show_quick_panel doesn't allow arbitrary data
        self.window.show_input_panel("Diff parameters?", self.last_diff, self.do_diff, None, None)

    def do_diff(self, diff_args):
        print("Diff args: %s" % diff_args)
        self.last_diff = diff_args
