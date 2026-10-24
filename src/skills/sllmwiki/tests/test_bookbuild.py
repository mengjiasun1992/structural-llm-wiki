"""Tests for lib/bookbuild.py and book.py render and build: drawing diagrams and math, and the single-file HTML
(docs/book_design.md §6.3-§6.5). Chrome and Sphinx are stand-ins here; CI's check-book builds with the real ones."""

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import helpers
from lib import book, bookbuild

# A stand-in for Chrome: reads the render page and dumps a DOM with an SVG (or an error) for each item.
CHROME = '''import html, json, os, re, sys
page = open(sys.argv[-1][len('file://'):], encoding='utf-8').read()
log = os.environ.get('STUB_LOG')
if log:
    open(log, 'a').write('drawn\\n')
if os.environ.get('STUB_EMPTY'):
    print('<html><textarea id="result"></textarea></html>'); sys.exit(0)
items = json.loads(re.search(r'const items = (.*?);\\n', page).group(1).replace('<\\\\/', '</'))
out = [{'setup': 'no mermaid'}] if os.environ.get('STUB_SETUP') else []
for it in items:
    if 'BAD' in it['source']:
        out.append({'id': it['id'], 'error': 'Parse error'})
    else:
        out.append({'id': it['id'], 'svg': '<svg xmlns="http://www.w3.org/2000/svg" id="r%s" role="graphics-document">'
                    '<rect x="1"/><g id="r%s-a"></g><g id="r%s-a"></g><text>%s</text></svg>' % (it['id'], it['id'], it['id'], it['kind'])})
print('<html><body><textarea id="result">' + html.escape(json.dumps(out)) + '</textarea></body></html>')
'''

# A stand-in for sphinx-build: writes a singlehtml folder like Sphinx's.
SPHINX = '''import os, sys
if os.environ.get('STUB_SPHINX_FAIL'):
    print('Extension error: no myst_parser', file=sys.stderr); sys.exit(2)
out, src = sys.argv[-1], sys.argv[-2]
os.makedirs(os.path.join(out, '_static'), exist_ok=True)
open(os.path.join(out, '_static', 'book.css'), 'w').write('body { color: #111; }')
open(os.path.join(out, 'fig.svg'), 'w').write('<svg/>')
args = ' '.join(sys.argv[1:])
body = open(os.path.join(src, 'chapters', 'what-is-alpha.md'), encoding='utf-8').read()
open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(
    '<html><head><link rel="stylesheet" type="text/css" href="_static/book.css?v=1" /><link rel="index" href="genindex.html" />'
    '<script src="_static/x.js"></script></head><body><div class="related" role="navigation"><ul><li>nav</li></ul></div>'
    '<a href="#document-chapters/x#what-is-alpha-1-abstract">x</a><img src="fig.svg"/><img src="https://example.com/a.png"/>'
    '<pre>' + args + '</pre><div>' + ('SVG-IN' if '<svg' in body else 'NO-SVG') + '</div></body></html>')
print('a.md:3: WARNING: something odd', file=sys.stderr)
'''


def program(folder, name, code):
    path = os.path.join(folder, name)
    with open(path, 'w') as f:
        f.write(f'#!{sys.executable}\n{code}')
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    return path


class Units(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='sllmwiki-test-')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_finding_chrome(self):
        chrome = program(self.tmp, 'chrome', '')
        self.assertEqual(bookbuild.find_chrome(chrome), chrome)
        with mock.patch.dict(os.environ, {'CHROME': chrome}):
            self.assertEqual(bookbuild.find_chrome(), chrome)
        with mock.patch.dict(os.environ, {'CHROME': ''}), mock.patch('shutil.which', return_value=None), \
                mock.patch('os.path.isfile', return_value=False):
            self.assertIsNone(bookbuild.find_chrome())
        self.assertIsNone(bookbuild.find_chrome(os.path.join(self.tmp, 'nothing')))  # given, so nothing else is tried

    def test_the_page_and_its_results(self):
        vendor = helpers.write(self.tmp, 'v/mermaid.min.js', 'm') and os.path.join(self.tmp, 'v')
        helpers.write(self.tmp, 'v/tex-svg-full.js', 't')
        page = bookbuild.page([{'id': 'a1', 'kind': 'inline', 'source': '</script>x'}], vendor)
        self.assertIn(f'file://{vendor}/mermaid.min.js', page)
        self.assertIn('<\\/script>x', page)  # the items can't close the script
        self.assertNotIn('"</script>x"', page)
        before = bookbuild.libraries(vendor)
        helpers.write(self.tmp, 'v/tex-svg-full.js', 't2')
        self.assertNotEqual(bookbuild.libraries(vendor), before)
        dom = '<textarea id="result">' + json.dumps([{'id': 'a', 'svg': '<svg/>'}, {'id': 'b', 'error': 'bad'}]).replace('"', '&quot;') + '</textarea>'
        self.assertEqual(bookbuild.results(dom), {'a': '<svg/>', 'b': {'error': 'bad'}})
        for broken in ('', '<textarea id="result"></textarea>'):
            with self.assertRaisesRegex(ValueError, 'no results'):
                bookbuild.results(broken)
        with self.assertRaisesRegex(ValueError, 'failed to start: no mermaid'):
            bookbuild.results('<textarea id="result">[{"setup": "no mermaid"}]</textarea>')

    def test_draw_with_a_stand_in(self):
        chrome = program(self.tmp, 'chrome', CHROME)
        found = bookbuild.draw([{'id': 'a', 'kind': 'mermaid', 'source': 'graph LR'}, {'id': 'b', 'kind': 'inline', 'source': 'BAD'}],
                               self.tmp, chrome, self.tmp)
        self.assertIn('<text>mermaid</text>', found['a'])
        self.assertEqual(found['b'], {'error': 'Parse error'})
        self.assertFalse(os.path.exists(os.path.join(self.tmp, '_render.html')))

    def test_clean(self):
        svg = ('<svg id="r1" role="graphics-document" aria-roledescription="flowchart">\n<rect x="1"/><rect width="2" height="3"/>'
               '<g id="r1-a"></g><g id="r1-a"></g><text>a<br>b</text></svg>')
        self.assertEqual(bookbuild.clean(svg, 'a | b\n"c"'),
                         '<svg id="r1" role="img" aria-label="a &#124; b&#10;&quot;c&quot;"> <rect height="0" width="0" x="1"/>'
                         '<rect width="2" height="3"/><g id="r1-a"></g><g id="r1-a-x"></g><text>a<br/>b</text></svg>')

    def test_put_in(self):
        rid = book.render_id
        text = 'Inline $a$ and $b$.\n\n$$\nx\n$$\n\n```mermaid\ngraph LR\n```\n\n```mermaid\ngraph LR\n```\n\nAgain $a$.\n'
        svgs = {rid('inline', 'a'): '<svg id="ra">A</svg>', rid('display', 'x'): '<svg>X</svg>',
                rid('mermaid', 'graph LR'): f'<svg id="r{rid("mermaid", "graph LR")}">M</svg>', rid('inline', 'b'): {'error': 'no'}}
        counts = {}
        out = bookbuild.put_in(text, svgs, rid, counts)
        m = rid('mermaid', 'graph LR')
        self.assertEqual(out, 'Inline <span class="math"><svg id="ra">A</svg></span> and $b$.\n\n\n<div class="math display"><svg>X</svg></div>\n\n\n\n'
                              f'<div class="diagram"><svg id="r{m}">M</svg></div>\n\n\n\n<div class="diagram"><svg id="r{m}-1">M</svg></div>\n\n\n'
                              'Again <span class="math"><svg id="ra">A</svg></span>.\n')
        self.assertEqual(counts[m], 2)

    def test_sphinx_language(self):
        self.assertEqual([bookbuild.sphinx_language(t) for t in ('en', 'zh-Hans', 'zh-Hant', 'pt-BR', 'de-CH', None)],
                         ['en', 'zh_CN', 'zh_TW', 'pt_BR', 'de_CH', 'en'])

    def test_self_contained(self):
        out = os.path.join(self.tmp, 'sh')
        os.environ.pop('STUB_SPHINX_FAIL', None)
        helpers.write(self.tmp, 'src/chapters/what-is-alpha.md', 'x')
        subprocess.run([program(self.tmp, 'sphinx', SPHINX), os.path.join(self.tmp, 'src'), out], check=True, capture_output=True)
        text = bookbuild.self_contained(out)
        self.assertIn('<style>\nbody { color: #111; }\n</style>', text)
        self.assertIn('href="#what-is-alpha-1-abstract"', text)
        self.assertIn('src="data:image/svg+xml;base64,PHN2Zy8+"', text)
        self.assertIn('src="https://example.com/a.png"', text)  # a remote image is the narrative's own link, left alone
        for gone in ('<script', 'rel="index"', 'class="related"', '#document-'):
            self.assertNotIn(gone, text)


class Commands(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='sllmwiki-test-')
        self.root = helpers.make_book_wiki(os.path.join(self.tmp, 'wiki'))
        self.vendor = os.path.join(self.tmp, 'vendor')
        helpers.write(self.vendor, 'mermaid.min.js', '// mermaid')
        helpers.write(self.vendor, 'tex-svg-full.js', '// mathjax')
        self.chrome = program(self.tmp, 'chrome', CHROME)
        self.sphinx = f'{sys.executable} {program(self.tmp, "sphinx", SPHINX)}'
        self.log = os.path.join(self.tmp, 'drawn.log')
        os.environ['STUB_LOG'] = self.log

    def tearDown(self):
        for k in ('STUB_LOG', 'STUB_EMPTY', 'STUB_SETUP', 'STUB_SPHINX_FAIL'):
            os.environ.pop(k, None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def book(self, *argv, cwd=None):
        return helpers.run('book.py', list(argv), cwd=cwd or self.root)

    def test_render(self):
        staged, cache = os.path.join(self.tmp, 'staged'), os.path.join(self.tmp, 'cache')
        self.assertEqual(self.book('stage', staged).code, 0)
        r = self.book('render', staged, '--vendor', self.vendor, '--chrome', self.chrome, '--cache', cache)
        self.assertEqual(r.code, 0, r.err)
        self.assertIn('0 warnings', r.out)
        alpha = helpers.read(staged, 'chapters/what-is-alpha.md')
        beta = helpers.read(staged, 'chapters/how-does-beta-work.md')
        self.assertNotIn('```mermaid', alpha + beta)
        self.assertIn('<div class="diagram"><svg', alpha)
        self.assertIn('role="img" aria-label="graph LR&#10;', alpha)
        self.assertIn('<span class="math"><svg', beta)
        self.assertIn('<div class="math display"><svg', beta)
        self.assertEqual(len(os.listdir(cache)), 4)
        with open(self.log) as f:
            self.assertEqual(f.read(), 'drawn\n')
        # a second staging draws nothing: every SVG is in the cache, so no Chrome is needed
        staged2 = os.path.join(self.tmp, 'staged2')
        self.book('stage', staged2)
        r = self.book('render', staged2, '--vendor', self.vendor, '--chrome', os.path.join(self.tmp, 'no-chrome'), '--cache', cache)
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(helpers.read(staged2, 'chapters/what-is-alpha.md'), alpha)
        with open(self.log) as f:
            self.assertEqual(f.read(), 'drawn\n')

    def test_what_does_not_draw_is_a_warning(self):
        text = helpers.read(self.root, 'sllmwiki/narratives/what-is-alpha.md').replace('Wait longer after each failure.', 'Wait $BAD$ longer.')
        helpers.write(self.root, 'sllmwiki/narratives/what-is-alpha.md', text)
        staged = os.path.join(self.tmp, 'staged')
        self.book('stage', staged)
        r = self.book('render', staged, '--vendor', self.vendor, '--chrome', self.chrome, '--json')
        self.assertEqual(r.code, 0, r.err)
        warnings = json.loads(r.out)['warnings']
        self.assertEqual([(w['code'], w['where']) for w in warnings], [('BOOK_RENDER', 'chapters/what-is-alpha.md')])
        self.assertIn('Parse error: BAD', warnings[0]['message'])
        self.assertIn('Wait $BAD$ longer.', helpers.read(staged, 'chapters/what-is-alpha.md'))  # left as written
        self.assertEqual(json.loads(helpers.read(staged, 'book.json'))['warnings'], warnings)

    def test_render_failures(self):
        staged = os.path.join(self.tmp, 'staged')
        self.book('stage', staged)
        r = self.book('render', staged, '--vendor', self.vendor, '--chrome', os.path.join(self.tmp, 'none'))
        self.assertEqual((r.code, 'no Chrome found' in r.err), (1, True))
        os.environ['STUB_EMPTY'] = '1'
        r = self.book('render', staged, '--vendor', self.vendor, '--chrome', self.chrome)
        self.assertEqual((r.code, 'wrote no results' in r.err), (1, True))
        del os.environ['STUB_EMPTY']
        os.environ['STUB_SETUP'] = '1'
        r = self.book('render', staged, '--vendor', self.vendor, '--chrome', self.chrome)
        self.assertEqual((r.code, 'failed to start' in r.err), (1, True))

    def test_usage(self):
        staged = os.path.join(self.tmp, 'staged')
        for argv, says in [(['render', staged], 'needs --vendor'), (['render', staged, '--vendor', self.tmp], 'needs --vendor'),
                           (['render', staged, '--vendor', self.vendor], "isn't a staged book"),
                           (['build', staged, '--vendor', self.vendor, '--formats', 'pdf'], 'only be html'),
                           (['build', staged, '--vendor', self.vendor, '--formats', ','], 'only be html')]:
            r = self.book(*argv)
            self.assertEqual(r.code, 2, argv)
            self.assertIn(says, r.err, argv)

    def test_build(self):
        out = os.path.join(self.tmp, 'out')
        r = self.book('build', out, '--vendor', self.vendor, '--chrome', self.chrome, '--sphinx', self.sphinx, '--version', 'v1')
        self.assertEqual(r.code, 0, r.err)
        name = os.path.basename(self.root)
        html = os.path.join(out, f'{name}-v1.html')
        self.assertIn(f'html: {html} (', r.out)
        text = helpers.read(out, f'{name}-v1.html')
        self.assertIn('SVG-IN', text)  # Sphinx read the rendered pages
        for arg in ('-b singlehtml', f'-c {os.path.join(helpers.SKILL_DIR, "templates", "book")}', f'project={name}',
                    'version=v1', 'release=v1', 'language=en'):
            self.assertIn(arg, text)
        data = json.loads(helpers.read(out, 'staged/book.json'))
        self.assertEqual(data['files'], {'html': html})
        self.assertEqual([w['code'] for w in data['warnings']], ['BOOK_SPHINX'])
        self.assertIn('WARNING: something odd', data['warnings'][0]['message'])
        r = self.book('build', out, '--vendor', self.vendor)
        self.assertEqual(r.code, 2)  # not empty

    def test_build_in_chinese_and_as_json(self):
        helpers.write(self.root, 'Config.toml', '[structural-llm-wiki-settings]\nlanguage = "zh-Hans"\n')
        out = os.path.join(self.tmp, 'out')
        r = self.book('build', out, '--vendor', self.vendor, '--chrome', self.chrome, '--sphinx', self.sphinx, '--json')
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(list(json.loads(r.out)['files']), ['html'])
        self.assertIn('language=zh_CN', helpers.read(out, os.path.basename(json.loads(r.out)['files']['html'])))

    def test_a_format_that_fails(self):
        os.environ['STUB_SPHINX_FAIL'] = '1'
        out = os.path.join(self.tmp, 'out')
        r = self.book('build', out, '--vendor', self.vendor, '--chrome', self.chrome, '--sphinx', self.sphinx)
        self.assertEqual(r.code, 1)
        self.assertIn('html failed: Sphinx failed: Extension error: no myst_parser', r.out)
        self.assertIn('Sphinx failed', json.loads(helpers.read(out, 'staged/book.json'))['failed']['html'])
        r = self.book('build', os.path.join(self.tmp, 'out2'), '--vendor', self.vendor, '--chrome', self.chrome,
                      '--sphinx', os.path.join(self.tmp, 'no-sphinx'))
        self.assertEqual(r.code, 1)
        self.assertIn("didn't run", r.out)


if __name__ == '__main__':
    unittest.main()
