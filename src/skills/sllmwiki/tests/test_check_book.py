"""Tests for src/tools/check-book.py, the check CI runs on a built book."""

import json
import os
import shutil
import tempfile
import unittest

import helpers

TOOL = os.path.join(helpers.REPO, 'src', 'tools', 'check-book.py')

GOOD = ('<html><head><style>body{}</style></head><body><section id="ch-a"><h1>A</h1>'
        '<p><a href="#ch-b">B</a> <a href="https://example.com/source">the original</a></p>'
        '<div class="diagram"><svg role="img" aria-label="graph LR"></svg></div>'
        '<img src="data:image/svg+xml;base64,PHN2Zy8+"/></section><section id="ch-b"><h1>B</h1>'
        '<span class="math"><svg role="img" aria-label="x"></svg></span><a href="#ch-a">A</a></section></body></html>')
BAD = ('<html><head><link rel="stylesheet" href="https://cdn.example.com/x.css"><script>1</script></head><body>'
       '<p id="x"></p><p id="x"></p><a href="#nowhere">?</a><img src="//cdn.example.com/a.png"/>'
       '<div class="highlight-mermaid notranslate"><pre>graph LR</pre></div><mjx-container data-mjx-error="Undefined control sequence">'
       '</mjx-container></body></html>')


class CheckBook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='sllmwiki-test-')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, text, *argv, book=None):
        helpers.write(self.tmp, 'book.html', text)
        extra = []
        if book is not None:
            helpers.write(self.tmp, 'book.json', json.dumps(book))
            extra = ['--book', os.path.join(self.tmp, 'book.json')]
        return helpers.run(TOOL, [os.path.join(self.tmp, 'book.html'), *extra, *argv])

    def test_a_good_book(self):
        r = self.run_tool(GOOD, '--max-bytes', '100000', '--seconds', '30', '--max-seconds', '240',
                          book={'renders': [{}, {}], 'problems': [], 'warnings': []})
        self.assertEqual(r.code, 0, r.out)
        self.assertRegex(r.out, r'check-book: 0 error\(s\) in .*book\.html \([0-9,]+ bytes\)')

    def test_a_bad_book(self):
        r = self.run_tool(BAD, '--json', '--max-bytes', '10', '--seconds', '300', '--max-seconds', '240',
                          book={'renders': [{}], 'problems': [{'code': 'BOOK_LINK', 'where': 'chapters/a.md:3', 'message': '#x: no section'}],
                                'warnings': [{'code': 'BOOK_RENDER', 'where': 'chapters/a.md', 'message': 'a mermaid that does not draw'}]})
        self.assertEqual(r.code, 1)
        found = json.loads(r.out)
        codes = [f['code'] for f in found['findings']]
        self.assertEqual(codes, ['LINK_UNRESOLVED', 'ID_DUPLICATE', 'UNRENDERED', 'UNRENDERED', 'SCRIPT', 'REMOTE', 'REMOTE',
                                 'SIZE', 'TIME', 'SVG_COUNT', 'BOOK_PROBLEM', 'BOOK_PROBLEM'])
        self.assertEqual(found['errors'], 12)
        messages = ' '.join(f['message'] for f in found['findings'])
        for says in ('#nowhere', 'id "x" is used 2 times', 'highlight-mermaid', 'https://cdn.example.com/x.css', '//cdn.example.com/a.png',
                     'built in 300 s, over 240 s', '0 drawn, but book.json lists 1', 'BOOK_LINK chapters/a.md:3', 'BOOK_RENDER'):
            self.assertIn(says, messages)

    def test_text_output_and_usage(self):
        r = self.run_tool('<a href="#gone">x</a>')
        self.assertEqual(r.code, 1)
        self.assertIn('error  LINK_UNRESOLVED  #gone: no element has this id', r.out)
        r = helpers.run(TOOL, [os.path.join(self.tmp, 'missing.html')])
        self.assertEqual((r.code, 'no file' in r.err), (2, True))


if __name__ == '__main__':
    unittest.main()
