"""Tests for scripts/check-upstream.py, over a local server."""

import json
import unittest
from unittest import mock

import helpers
import pdfmaker
from lib import manifest, pdf, policy

ROUTES = {
    '/budget.md': (200, {'Content-Type': 'text/markdown'}, b'# Budgets\n\nTen percent.\n'),
    '/backoff.md': (200, {'Content-Type': 'text/markdown'}, b'# Backoff\n\nDouble it.\n'),
    '/book.pdf': (200, {'Content-Type': 'application/pdf'}, pdfmaker.make(
        [pdfmaker.text((72, 700, b'Text of page %d.' % i)) for i in range(pdf.SLICE_PAGES + 1)],
        [(0, b'Part One', 0, None), (0, b'Part Two', 50, None)])),
}


class CheckUpstream(helpers.WikiTestCase):
    def setUp(self):
        super().setUp()
        self.routes = dict(ROUTES)
        self.server = helpers.LocalServer(self.routes).__enter__()
        self.seen_by = mock.patch.object(policy, 'visibility', return_value='private')
        self.seen_by.start()
        for slug in ('alpha-doc', 'beta-doc'):  # the fixture's own sources: never the real network
            e = manifest.load(self.root, 'sources')[slug]
            manifest.save(self.root, 'sources', slug, dict(e, url=self.server.url('/gone-' + slug)))
        for slug, path, tag in (('alpha-budget', '/budget.md', 'leaf-a'), ('beta-backoff', '/backoff.md', 'leaf-b'), ('alpha-book', '/book.pdf', 'leaf-a')):
            r = helpers.run('fetch-source.py', [slug, '--url', self.server.url(path), '--tags', tag, '--license', 'CC-BY-4.0', '--root', self.root])
            self.assertEqual(r.code, 0, r.err)

    def tearDown(self):
        self.seen_by.stop()
        self.server.__exit__(None, None, None)
        super().tearDown()

    def check(self, *argv):
        return helpers.run('check-upstream.py', [*argv, '--root', self.root])

    def test_unchanged_changed_and_cleared(self):
        r = self.check()
        self.assertEqual(r.code, 0, r.err)
        self.assertIn('unchanged    alpha-budget', r.out)
        self.assertIn('unchanged    alpha-book-2-part-two', r.out)
        self.assertIn('unreachable  alpha-doc: ', r.out)
        self.assertIn('6 checked, 0 changed', r.out)
        self.routes['/budget.md'] = (200, {'Content-Type': 'text/markdown'}, b'# Budgets\n\nFive percent.\n')
        self.routes['/book.pdf'] = (200, {'Content-Type': 'application/pdf'}, pdfmaker.make(
            [pdfmaker.text((72, 700, b'Text of page %d.' % i)) for i in range(pdf.SLICE_PAGES + 1)],
            [(0, b'Part One', 0, None), (0, b'Part Two', 60, None)]))
        out = json.loads(self.check('--json').out)['sources']
        status = {s['slug']: s['status'] for s in out}
        self.assertEqual((status['alpha-budget'], status['beta-backoff'], status['alpha-book-1-part-one'], status['alpha-book-2-part-two']),
                         ('changed', 'unchanged', 'changed', 'changed'))
        self.assertEqual([s['detail'] for s in out if s['slug'] == 'alpha-book-2-part-two'], ['no slice starts on page 51 any more'])
        sources = manifest.load(self.root, 'sources')
        self.assertTrue(sources['alpha-budget'].get('upstream_changed'))
        wiki = helpers.run('wiki-check.py', ['--root', self.root])
        self.assertIn('SOURCE_UPSTREAM_CHANGED', wiki.out)
        self.routes['/budget.md'] = ROUTES['/budget.md']  # back as it was: the mark goes
        self.assertIn('unchanged    alpha-budget', self.check('alpha-budget').out)
        self.assertNotIn('upstream_changed', manifest.load(self.root, 'sources')['alpha-budget'])

    def test_unreachable_and_choosing(self):
        self.routes['/backoff.md'] = (403, {}, b'')
        self.routes['/budget.md'] = (200, {'Content-Type': 'image/png'}, b'\x89PNG')
        r = self.check('--tags', 'leaf-b')
        self.assertIn('unreachable  beta-backoff:', r.out)
        self.assertNotIn('alpha-budget', r.out)
        self.assertIn('unreachable  alpha-budget: the text isn\'t UTF-8', self.check('alpha-budget').out)
        self.assertNotIn('upstream_changed', manifest.load(self.root, 'sources')['beta-backoff'])
        self.assertIn('no such source or tag: nope', self.check('nope').err)


if __name__ == '__main__':
    unittest.main()
