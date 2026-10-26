"""What the plugin directory accepts in a plugin's files: none over 5 MiB, and every one either plain text the
security scan can read or an image whose extension matches its format (docs/structural_llm_wiki_design.md §11)."""

import os
import subprocess
import unittest

import helpers

LIMIT = 5 * 1024 * 1024  # the directory refuses a file this size or larger
IMAGES = {'.png': b'\x89PNG\r\n\x1a\n', '.jpg': b'\xff\xd8\xff', '.jpeg': b'\xff\xd8\xff', '.gif': b'GIF8'}


def tracked():
    out = subprocess.run(['git', 'ls-files', '-z'], cwd=helpers.REPO, capture_output=True, check=True).stdout
    return [f for f in out.decode('utf-8').split('\0') if f and os.path.isfile(os.path.join(helpers.REPO, f))]


class PluginFiles(unittest.TestCase):
    def test_no_file_over_the_size_limit(self):
        big = [f'{f}: {os.path.getsize(os.path.join(helpers.REPO, f)):,} bytes' for f in tracked()
               if os.path.getsize(os.path.join(helpers.REPO, f)) >= LIMIT]
        self.assertEqual(big, [], 'the plugin directory takes no file of 5 MiB or more: split it into plain-text parts '
                                  '(src/actions/release-book/vendor/split.py) or leave it out')

    def test_every_file_is_text_or_a_true_image(self):
        unreadable = []
        for f in tracked():
            with open(os.path.join(helpers.REPO, f), 'rb') as fh:
                data = fh.read()
            magic = IMAGES.get(os.path.splitext(f)[1].lower())
            if magic is not None:
                if not data.startswith(magic):
                    unreadable.append(f'{f}: not the image its extension says')
                continue
            try:
                data.decode('utf-8')
            except UnicodeDecodeError:
                unreadable.append(f'{f}: not UTF-8 text')
                continue
            if b'\0' in data:
                unreadable.append(f'{f}: holds NUL bytes')
        self.assertEqual(unreadable, [], 'the directory\'s scan reads only plain text and real images; a binary, '
                                         'bytecode or packed file holds the plugin for review')


if __name__ == '__main__':
    unittest.main()
