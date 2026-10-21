"""Tests for scripts/cited-sections.py."""

import json
import unittest

import helpers
from lib import plaintext

EXTRA = '''
Doubling bounds the load. Each wait doubles. [\\[1\\]](../sources/alpha-doc.md#details) [\\[2\\]](../sources/alpha-doc.md#alpha)

| Setting | Value |
|---|---|
| Base wait | 100 ms [\\[3\\]](../sources/alpha-code.md#L1-L2) |

- Retries stop after a budget. [\\[4\\]](../sources/alpha-doc.md#nope)
- **Whole file.** A claim. [\\[5\\]](../sources/beta-doc.md) And a gone one. [\\[6\\]](../sources/gone.md#x)
'''


class CitedSections(helpers.WikiTestCase):
    def setUp(self):
        super().setUp()
        self.write('sllmwiki/sources/alpha-code.md', plaintext.code('base = 100\nfactor = 2\nlimit = 5\n', 'retry.py'))
        self.write('sllmwiki/narratives/what-is-alpha.md', helpers.narrative_text(extra=EXTRA))

    def run_it(self, *argv):
        return helpers.run('cited-sections.py', [*argv, '--root', self.root])

    def test_each_section_once_with_its_claims(self):
        r = self.run_it('what-is-alpha', '--json')
        self.assertEqual(r.code, 0, r.err)
        cited = json.loads(r.out)['cited']
        by = {c['target']: c for c in cited}
        details = by['../sources/alpha-doc.md#details']
        self.assertEqual([(c['n'], c['claim']) for c in details['claims']],
                         [(1, 'Alpha systems retry, each time waiting twice as long.'), (1, 'Each wait doubles.')])
        self.assertEqual(details['text'], '## Details\n\nEach retry waits twice as long as the last.\n')
        self.assertEqual(by['../sources/alpha-doc.md#alpha']['claims'][0]['claim'], 'Each wait doubles.')  # two citations, one claim
        self.assertEqual(by['../sources/alpha-code.md#L1-L2']['text'], '1: base = 100\n2: factor = 2\n')
        self.assertEqual(by['../sources/alpha-code.md#L1-L2']['claims'][0]['claim'], 'Base wait | 100 ms')
        self.assertEqual(by['../sources/alpha-doc.md#nope']['problem'], 'sllmwiki/sources/alpha-doc.md has no section #nope')
        self.assertEqual(by['../sources/beta-doc.md']['problem'], 'cites the whole file, not a section')
        self.assertEqual(by['../sources/gone.md#x']['problem'], 'no such file')
        self.assertEqual(by['../sources/beta-doc.md']['claims'][0]['claim'], 'A claim.')

    def test_text_and_claims_only(self):
        out = self.run_it('sllmwiki/narratives/what-is-alpha.md').out
        self.assertIn('## ../sources/alpha-doc.md#details\n\n- line ', out)
        self.assertIn('[1]: Each wait doubles.\n\n## Details\n\nEach retry waits twice as long as the last.\n', out)
        self.assertIn('## ../sources/gone.md#x  (no such file)', out)
        self.assertNotIn('Each retry waits', self.run_it('what-is-alpha', '--claims-only').out)

    def test_refusals_and_nothing_cited(self):
        self.assertIn('no narrative nope', self.run_it('nope').err)
        self.assertIn('no narrative alpha-doc', self.run_it('alpha-doc').err)  # a source isn't a narrative
        self.write('sllmwiki/narratives/what-is-alpha.md', helpers.narrative_text(cites=()))
        self.assertIn('cites nothing', self.run_it('what-is-alpha').out)


if __name__ == '__main__':
    unittest.main()
