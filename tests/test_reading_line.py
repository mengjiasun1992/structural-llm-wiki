"""Tests for the reading-time line under a narrative's title (issue #182): finish-narrative keeps its minutes those of
Metadata's Words, narrative-format reports a stale one, the count leaves it out, and the book drops it."""

import os

import helpers
from sllmwiki.lib import book, metadata

ALPHA = 'sllmwiki/narratives/what-is-alpha.md'


def with_line(text, line):
    """text with line under its # title."""
    title, rest = text.split('\n', 1)
    return f'{title}\n\n{line}\n{rest}'


class Line(helpers.WikiTestCase):
    def text(self):
        return helpers.read(self.root, ALPHA)

    def test_kept_in_step(self):
        plain = self.text()
        minutes = metadata.reading(plain)[1]
        stale = with_line(plain, '*About 42 min read.*')
        self.assertEqual(metadata.reading(stale), metadata.reading(plain))  # the line isn't counted
        fresh = metadata.with_reading_line(stale)
        self.assertEqual(fresh, with_line(plain, f'*About {minutes} min read.*'))
        self.assertEqual(metadata.with_reading_line(fresh), fresh)  # a second run changes nothing
        self.assertEqual(metadata.with_reading_line(plain), plain)  # no line: none added

    def test_only_the_line_under_the_title(self):
        cases = [
            ('*About 9 min read.*\n', 'directly under the title'),
            ('\n\n*About 9 min read.*\n', 'past blank lines'),
        ]
        for gap, why in cases:
            with self.subTest(why=why):
                text = '# Q?\n' + gap + '\n## 1. Abstract\n\nText.\n'
                self.assertIn('*About 1 min read.*', metadata.with_reading_line(text))
        for text in ('# Q?\n\n## 1. Abstract\n\n*About 9 min read.*\n',  # in the body: someone's text
                     '# Q?\n\nAbout 9 min read.\n',  # not the line's form
                     '# Q?\n\n*Roughly 9 min read.*\n',
                     'No title\n\n*About 9 min read.*\n'):
            with self.subTest(text=text):
                self.assertEqual(metadata.with_reading_line(text), text)

    def test_in_the_narratives_language(self):
        text = '# 问题？\n\n*阅读约 9 分钟。*\n\n## 1. 摘要\n\n文字。\n'
        self.assertEqual(metadata.with_reading_line(text), '# 问题？\n\n*阅读约 1 分钟。*\n\n## 1. 摘要\n\n文字。\n')
        self.assertEqual(metadata.with_reading_line(text.replace('阅读约', '閱讀約').replace('分钟', '分鐘')),
                         '# 问题？\n\n*閱讀約 1 分鐘。*\n\n## 1. 摘要\n\n文字。\n')

    def test_finish_narrative_and_narrative_format(self):
        helpers.write(self.root, ALPHA, with_line(self.text(), '*About 42 min read.*'))
        r = helpers.run('narrative-format.py', ['--root', self.root, os.path.join(self.root, ALPHA)])
        self.assertIn('READING_TIME_OUTDATED', r.out)
        self.assertIn('About 1 min read.', r.out)
        r = helpers.run('finish-narrative.py', ['what-is-alpha', '--root', self.root])
        self.assertNotIn('READING_TIME_OUTDATED', r.out)
        text = self.text()
        self.assertIn('\n*About 1 min read.*\n', text)
        self.assertEqual(metadata.read(text)['words'], metadata.reading_label(text))
        self.assertNotIn('READING_TIME_OUTDATED', helpers.run('narrative-format.py', ['--root', self.root, os.path.join(self.root, ALPHA)]).out)

    def test_the_book_drops_it(self):
        plain = book.rewrite(self.root, book.model(self.root), 'what-is-alpha').text
        helpers.write(self.root, ALPHA, with_line(self.text(), '*About 1 min read.*'))
        self.assertEqual(book.rewrite(self.root, book.model(self.root), 'what-is-alpha').text, plain)  # the version line has it
        self.assertEqual(metadata.without_reading_line('# Q?\n\n*About 1 min read.*'), '# Q?\n')  # the last line
