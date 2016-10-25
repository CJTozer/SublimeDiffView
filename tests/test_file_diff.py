import sys
from unittest import TestCase

diffview = sys.modules["DiffView"]
FileDiff = diffview.parser.file_diff.FileDiff


class test_FileDiff(TestCase):

    def test_file_diff_parsing(self):
        # From #41 (https://github.com/CJTozer/SublimeDiffView/issues/41)
        diff_output = """Index: test.html
===================================================================
--- test.html   (版本 97694)
+++ test.html   (工作副本)
@@ -6,5 +6,6 @@
 </head>
 <body>
 <h1>test</h1>
+<h2>this is new line</h2>
 </body>
 </html>
\ No newline at end of file
"""
        file_diff = FileDiff('test.html', '/path/to/test.html', diff_output)
        hunks = file_diff.get_hunks()
        self.assertEquals(1, len(hunks))
