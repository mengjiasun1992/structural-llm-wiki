"""Tests for scripts/fetch-source.py: saving a source verbatim under the source policy.
The page comes from a local server; who can see the wiki is mocked."""

import json
import os
import unittest
from unittest import mock

import helpers
import pdfmaker
from lib import footer, manifest, pdf, policy
from lib.util import read_bytes, source_hash

MD = b'# Retry budgets\n\nA retry budget caps retries at a share of requests.\n\n## How\n\nTen percent.\n'
HTML = (b'<html><head><title>Backoff</title></head><body><nav>Menu</nav><main><h1>Backoff</h1>'
        b'<p>Each retry waits <em>twice</em> as long.</p></main><footer>Foot</footer></body></html>')
ROUTES = {
    '/budget.md': (200, {'Content-Type': 'text/markdown; charset=utf-8'}, MD),
    '/backoff': (200, {'Content-Type': 'text/html; charset=utf-8'}, HTML),
    '/paper.pdf': (200, {'Content-Type': 'application/pdf'}, b'%PDF-1.4'),
    '/real.pdf': (200, {'Content-Type': 'application/pdf'}, pdfmaker.make(
        [pdfmaker.text((72, 700, b'1 Introduction'), (72, 680, b'Why retries need a budget.'))], [(0, b'Introduction', 0, None)], title=b'Budgets')),
    '/book.pdf': (200, {'Content-Type': 'application/pdf'}, pdfmaker.make(
        [pdfmaker.text((72, 700, b'Text of page %d.' % i)) for i in range(pdf.SLICE_PAGES + 1)],
        [(0, b'Part One', 0, None), (0, b'Part Two', 50, None), (0, b'', 60, None)])),
    '/image': (200, {'Content-Type': 'image/png'}, b'\x89PNG'),
    '/paper.tex': (200, {'Content-Type': 'application/x-tex'}, b'\\section{Budgets}\nCap at $r \\le 0.1$.\n'),
    '/empty': (200, {'Content-Type': 'text/plain'}, b'   \n'),
    '/latin1': (200, {'Content-Type': 'text/plain'}, 'café'.encode('latin-1')),
    '/login': (403, {}, b''),
}


class FetchSource(helpers.WikiTestCase):
    def setUp(self):
        super().setUp()
        self.server = helpers.LocalServer(ROUTES).__enter__()
        self.seen_by = mock.patch.object(policy, 'visibility', return_value='private')
        self.seen_by.start()

    def tearDown(self):
        self.seen_by.stop()
        self.server.__exit__(None, None, None)
        super().tearDown()

    def fetch(self, slug, path, *extra, license='CC-BY-4.0'):
        return helpers.run('fetch-source.py', [slug, '--url', self.server.url(path), '--tags', 'leaf-a', '--license', license,
                                               '--root', self.root, *extra])

    def entry(self, slug):
        return manifest.load(self.root, 'sources')[slug]

    def test_markdown_byte_for_byte_with_its_footer(self):
        r = self.fetch('retry-budget', '/budget.md', '--published', '2026-05-01', '--license-url', 'https://e.com/l')
        self.assertEqual(r.code, 0, r.err)
        self.assertIn('saved sllmwiki/sources/retry-budget.md (text,', r.out)
        self.assertIn('manifest.py set-abstract retry-budget', r.out)
        data = read_bytes(os.path.join(self.root, 'sllmwiki/sources/retry-budget.md'))
        self.assertTrue(data.startswith(MD))
        self.assertEqual(source_hash(data), helpers.md5(MD))
        self.assertEqual(footer.read(data), {'url': self.server.url('/budget.md'), 'license': 'CC-BY-4.0'})
        e = self.entry('retry-budget')
        self.assertEqual((e['file'], e['kind'], e['published'], e['license_url'], e['tags'], e['abstract_draft']),
                         ('sources/retry-budget.md', 'text', '2026-05-01', 'https://e.com/l', ['leaf-a'], True))
        self.assertEqual(e['abstract'], 'A retry budget caps retries at a share of requests. Ten percent.')
        self.assertIn('[retry-budget](../sources/retry-budget.md)', self.read('sllmwiki/tags/leaf-a.md'))  # tag page rewritten

    def test_html_main_content(self):
        r = self.fetch('backoff', '/backoff', '--json')
        self.assertEqual(r.code, 0, r.err)
        result = json.loads(r.out)
        self.assertEqual((result['kind'], result['abstract_draft']), ('html', True))
        text = self.read('sllmwiki/sources/backoff.md')
        self.assertTrue(text.startswith('# Backoff\n\nEach retry waits *twice* as long.\n'))
        self.assertNotIn('Menu', text)

    def test_a_local_copy(self):
        local = helpers.write(self.tmp, 'incoming/notes.md', '# Notes\n\nLocal.\n')
        r = helpers.run('fetch-source.py', ['local-notes', '--url', 'https://intranet.example.com/notes', '--tags', 'leaf-b', '--license', 'proprietary',
                                            '--file', local, '--root', self.root])
        self.assertEqual(r.code, 0, r.err)
        self.assertTrue(self.read('sllmwiki/sources/local-notes.md').startswith('# Notes\n\nLocal.\n'))
        r = helpers.run('fetch-source.py', ['x', '--url', 'https://e.com', '--tags', 'leaf-b', '--license', 'MIT', '--file', '/nope.md', '--root', self.root])
        self.assertEqual((r.code, r.err), (1, 'fetch-source.py: no such file: /nope.md\n'))

    def test_refresh_keeps_a_written_abstract(self):
        self.assertEqual(self.fetch('retry-budget', '/budget.md').code, 0)
        manifest.set_abstract(self.root, 'retry-budget', 'Written by the agent.')
        r = self.fetch('retry-budget', '/budget.md')
        self.assertEqual(r.code, 1)
        self.assertIn('pass --refresh', r.err)
        r = self.fetch('retry-budget', '/budget.md', '--refresh')
        self.assertEqual(r.code, 0, r.err)
        self.assertIn('refreshed', r.out)
        self.assertNotIn('set-abstract', r.out)
        e = self.entry('retry-budget')
        self.assertEqual((e['abstract'], 'abstract_draft' in e), ('Written by the agent.', False))

    def test_refresh_refusals(self):
        self.assertIn('no source new-one to refresh', self.fetch('new-one', '/budget.md', '--refresh').err)
        self.assertIn('is a link', self.fetch('gamma-link', '/budget.md', '--refresh').err)

    def test_unknown_tag(self):
        r = helpers.run('fetch-source.py', ['x', '--url', self.server.url('/budget.md'), '--tags', 'nope', '--license', 'MIT', '--root', self.root])
        self.assertIn('no such tag(s): nope', r.err)

    def test_what_cant_be_saved(self):
        for path, msg in (('/paper.pdf', 'a broken PDF: no catalog; record it as a link'), ('/image', 'not markdown, text, HTML or PDF'),
                          ('/empty', 'nothing to save'), ('/latin1', 'isn\'t UTF-8'), ('/login', 'never get around it')):
            r = self.fetch('x', path)
            self.assertEqual(r.code, 1, path)
            self.assertIn(msg, r.err)
            self.assertNotIn('x', manifest.load(self.root, 'sources'))
            self.assertFalse(os.path.exists(os.path.join(self.root, 'sllmwiki/sources/x.md')))

    def test_a_pdf(self):
        r = self.fetch('alpha-budgets', '/real.pdf', '--json')
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(json.loads(r.out)['kind'], 'pdf')
        saved = read_bytes(os.path.join(self.root, 'sllmwiki/sources/alpha-budgets.md')).decode()
        self.assertTrue(saved.startswith('# Budgets\n\n## Introduction\n\nWhy retries need a budget.\n'))
        self.assertEqual(manifest.load(self.root, 'sources')['alpha-budgets']['abstract'], 'Why retries need a budget.')

    def test_a_long_outlined_pdf_is_saved_in_slices(self):
        r = self.fetch('alpha-book', '/book.pdf')
        self.assertEqual(r.code, 0, r.err)
        self.assertIn('saved alpha-book in 2 slices', r.out)
        sources = manifest.load(self.root, 'sources')
        one, two = sources['alpha-book-1-part-one'], sources['alpha-book-2-part-two']
        self.assertEqual((one['url'].split('#')[1], two['url'].split('#')[1], one['abstract_draft']), ('page=1', 'page=51', True))
        self.assertEqual(two['abstract'].split(':')[0], 'Part Two')
        self.assertNotIn('alpha-book', sources)
        self.assertIn('already saved: alpha-book-1-part-one', self.fetch('alpha-book', '/book.pdf').err)
        manifest.save(self.root, 'sources', 'alpha-long', dict(one, file='sources/alpha-long.md'))
        helpers.write(self.root, 'sllmwiki/sources/alpha-long.md', 'x')
        self.assertIn('would be saved in slices', self.fetch('alpha-long', '/book.pdf', '--refresh').err)
        r = self.fetch('alpha-other', '/book.pdf', '--json')
        self.assertEqual([s['slug'] for s in json.loads(r.out)['slices']], ['alpha-other-1-part-one', 'alpha-other-2-part-two'])
        self.assertEqual(helpers.load_script('fetch-source.py').slice_slug('x', 3, '!!!'), 'x-3')

    def test_a_latex_source(self):
        self.assertEqual(self.fetch('alpha-tex', '/paper.tex').code, 0)
        saved = read_bytes(os.path.join(self.root, 'sllmwiki/sources/alpha-tex.md')).decode()
        self.assertTrue(saved.startswith('## Budgets\n\nCap at $r \\le 0.1$.\n'))
        self.assertEqual(manifest.load(self.root, 'sources')['alpha-tex']['kind'], 'tex')
        folder = os.path.join(self.tmp, 'paper')
        helpers.write(folder, 'main.tex', '\\begin{document}\\input{intro}\\input{../secret}\\input{gone}\\end{document}')
        helpers.write(folder, 'intro.tex', '\\section{Intro}Read from beside it.')
        helpers.write(self.tmp, 'secret.tex', 'Outside the folder.')
        r = helpers.run('fetch-source.py', ['alpha-main', '--url', 'https://e.com/main.tex', '--tags', 'leaf-a', '--license', 'CC-BY-4.0',
                                            '--file', os.path.join(folder, 'main.tex'), '--root', self.root])
        self.assertEqual(r.code, 0, r.err)
        saved = read_bytes(os.path.join(self.root, 'sllmwiki/sources/alpha-main.md')).decode()
        self.assertTrue(saved.startswith('## Intro\n\nRead from beside it.\n'))
        self.assertNotIn('Outside', saved)

    def test_public_wiki_keeps_only_open_licenses(self):
        with mock.patch.object(policy, 'visibility', return_value='public'):
            r = self.fetch('closed', '/budget.md', license='proprietary')
            self.assertEqual(r.code, 1)
            self.assertIn('openly licensed sources only', r.err)
            self.assertIn('--allow-restricted', r.err)
            self.assertEqual(self.fetch('open', '/budget.md', license='CC-BY-4.0').code, 0)
            r = self.fetch('granted', '/budget.md', '--allow-restricted', 'Jane Doe, 2026-10-21', license='proprietary')
            self.assertEqual(r.code, 0, r.err)
            self.assertEqual(self.entry('granted')['permission'], 'Jane Doe, 2026-10-21')

    def test_links_only_keeps_no_copies(self):
        self.write('Config.toml', '[structural-llm-wiki-settings]\nsource_copies = "links-only"\n')
        r = self.fetch('x', '/budget.md', license='CC0-1.0')
        self.assertEqual(r.code, 1)
        self.assertIn('links-only', r.err)

    def test_invalid_config_refuses(self):
        self.write('Config.toml', '[structural-llm-wiki-settings]\nsource_copies = "some"\n')
        r = self.fetch('x', '/budget.md')
        self.assertEqual(r.code, 1)
        self.assertIn('Config.toml is invalid', r.err)

    def test_a_bad_entry_writes_nothing(self):
        r = self.fetch('x', '/budget.md', '--published', 'last week')
        self.assertEqual(r.code, 1)
        self.assertIn('published must be a date', r.err)
        self.assertFalse(os.path.exists(os.path.join(self.root, 'sllmwiki/sources/x.md')))


class DraftAbstract(unittest.TestCase):
    def test_opening_words(self):
        mod = helpers.load_script('fetch-source.py')
        self.assertEqual(mod.draft_abstract('# T\n\n```\ncode\n```\n| t |\n\nSome *real* text.\n'), 'code Some real text.')
        long = ' '.join(['w'] * 80)
        self.assertEqual(mod.draft_abstract(long), ' '.join(['w'] * 60) + '…')
        self.assertEqual(mod.draft_abstract('# Only a title\n'), 'No text found.')


if __name__ == '__main__':
    unittest.main()
