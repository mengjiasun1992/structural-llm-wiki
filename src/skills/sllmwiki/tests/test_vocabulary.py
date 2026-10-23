"""Tests for lib/vocabulary.py: narrative IDs, defined and borrowed terms, links into other narratives, the terms page."""

import os
import unittest

import helpers
from lib import layout, manifest, vocabulary

ALPHA = 'sllmwiki/narratives/what-is-alpha.md'
BETA = 'sllmwiki/narratives/how-does-beta-work.md'
BORROW = '| **Retry** | From [alpha](what-is-alpha.md#2-terminology). |'


def beta(rows=BORROW, body='Retries, as [alpha explains](what-is-alpha.md#5-how-does-it-work), wait.', nid='beta'):
    text = helpers.narrative_text('How does beta work?', extra=f'\n{body}\n').replace('- **ID:** alpha', f'- **ID:** {nid}' if nid else '')
    return text.replace('| **Retry** | Sending a failed request again. |', rows)


class Vocabulary(helpers.WikiTestCase):
    def setUp(self):
        super().setUp()
        self.write(BETA, beta())
        manifest.put_narrative(self.root, 'how-does-beta-work', 'technical_brief_overview', ['leaf-a'], [], ['alpha-doc'])

    def codes(self, findings):
        return [f[1] for f in findings]

    def test_terms_and_ids(self):
        text = helpers.narrative_text().replace('| **Retry** | Sending a failed request again. |',
                                                '| **Retry** | Sending a failed request again. |\n| **$x_t$** | A sample. |\n| **[->]** | Ours. |')
        got = [(t.term, t.definition, t.owner_id) for t in vocabulary.terms(text)]
        self.assertEqual(got, [('Retry', 'Sending a failed request again.', None)])  # notation and markers aren't shared terms
        self.assertEqual([(t.term, t.owner_id, t.target) for t in vocabulary.terms(beta())], [('Retry', 'alpha', 'what-is-alpha.md#2-terminology')])
        self.assertEqual(vocabulary.narrative_id(text), 'alpha')
        self.assertEqual(vocabulary.suggest_id('what-are-the-common-design-tenets-and-principles-for-distributed-systems'),
                         'design-tenets-principles-distributed')
        self.assertEqual(vocabulary.suggest_id('what-is-it'), 'what-is-it')
        self.assertEqual(vocabulary.suggest_id('x' * 50), 'x' * 40)
        self.assertEqual(vocabulary.normalize(' Fault  / *failure*'), 'fault / failure')

    def test_sync_fills_borrowed_rows(self):
        text, n, problems = vocabulary.sync(self.root, beta(), 'how-does-beta-work')
        self.assertEqual((n, problems), (1, []))
        self.assertIn('| **Retry** | Sending a failed request again. From [alpha](what-is-alpha.md#2-terminology). |', text)
        self.assertEqual(vocabulary.sync(self.root, text, 'how-does-beta-work')[1], 0)
        _, _, problems = vocabulary.sync(self.root, beta(rows='| **Retry** | From [gamma](x.md#y). |\n| **Backoff** | From [alpha](what-is-alpha.md#2-terminology). |'),
                                         'how-does-beta-work')
        self.assertEqual([p for _, p in problems], ['"Retry" is borrowed from gamma, which no narrative has as its ID',
                                                    '"Backoff" is borrowed from alpha, which doesn\'t define it'])

    def test_check_one(self):
        self.assertEqual(vocabulary.check_one(self.root, BETA, beta()), [])
        self.assertEqual(self.codes(vocabulary.check_one(self.root, BETA, beta(nid=None))), ['NO_ID'])
        self.assertEqual(self.codes(vocabulary.check_one(self.root, BETA, beta(nid='Bad_ID'))), ['BAD_ID'])
        self.assertEqual(self.codes(vocabulary.check_one(self.root, BETA, beta(rows='| **Retry** | From [gamma](x.md#y). |'))), ['TERM_OWNER'])
        moved = vocabulary.check_one(self.root, BETA, beta(body='See [alpha](what-is-alpha.md#9-how-does-it-work) and [nothing](what-is-alpha.md#9-nope).'))
        self.assertEqual(self.codes(moved), ['NARRATIVE_ANCHOR', 'NARRATIVE_ANCHOR'])
        self.assertIn('repairs it', moved[0][3])
        self.assertNotIn('repairs it', moved[1][3])
        self.assertEqual(vocabulary.check_one(self.root, BETA, beta(body='See [gone](gone.md#x), [sources](../sources/alpha-doc.md#details), '
                                                                       'and [this one](how-does-beta-work.md#3-background).')), [])

    def test_repair_links(self):
        text, n = vocabulary.repair_links(self.root, BETA, beta(body='See [alpha](what-is-alpha.md#9-how-does-it-work), [here](what-is-alpha.md#9-nope).'))
        self.assertEqual(n, 1)
        self.assertIn('[alpha](what-is-alpha.md#5-how-does-it-work), [here](what-is-alpha.md#9-nope)', text)

    def test_wiki_check(self):
        self.write(BETA, beta(rows='| **Retry** | Trying again. From [alpha](what-is-alpha.md#2-terminology). |\n| **Backoff** | From [zeta](x.md#y). |',
                              body='See [alpha](what-is-alpha.md#9-how-does-it-work).'))
        got = [(f[1], f[2]) for f in vocabulary.check(self.root)]
        self.assertEqual(got, [('TERM_DRIFT', f'{BETA}:{beta().split(chr(10)).index(BORROW) + 1}'),
                               ('TERM_OWNER', f'{BETA}:{beta().split(chr(10)).index(BORROW) + 2}'),
                               ('NARRATIVE_ANCHOR', f'{BETA}:{beta().split(chr(10)).index("Retries, as [alpha explains](what-is-alpha.md#5-how-does-it-work), wait.") + 2}')])
        self.assertNotIn('NARRATIVE_ANCHOR', self.codes(vocabulary.check(self.root, fix=True)))
        self.assertIn('#5-how-does-it-work', helpers.read(self.root, BETA))
        self.write(BETA, beta(rows='| **Retry** | Trying again. |', nid='alpha'))
        self.assertEqual(sorted(self.codes(vocabulary.check(self.root))), ['NARRATIVE_ID_DUPLICATE', 'TERM_DEFINED_TWICE'])
        self.write(BETA, beta(nid=None))
        self.assertEqual(self.codes(vocabulary.check(self.root)), ['NARRATIVE_ID_MISSING', 'TERM_DRIFT'])  # its borrowed row isn't filled yet

    def test_terms_page(self):
        page = vocabulary.render(self.root)
        self.assertIn('| **Retry** | Sending a failed request again. | [alpha](sllmwiki/narratives/what-is-alpha.md#2-terminology) |', page)
        self.write(ALPHA, helpers.narrative_text().replace('| **Retry** | Sending a failed request again. |', '| **Retry** | See [the doc](../sources/alpha-doc.md#details). |'))
        self.assertIn('| **Retry** | See the doc. |', vocabulary.render(self.root))  # links in a definition don't resolve from the page
        os.remove(os.path.join(self.root, ALPHA))
        self.assertIn('No terms yet.', vocabulary.render(self.root))
        r = helpers.run('wiki-check.py', ['--fix', '--root', self.root])
        self.assertIn('No terms yet.', open(os.path.join(self.root, layout.TERMS), encoding='utf-8').read(), r.out)

    def test_finish_sets_the_id_and_fills_borrowed_terms(self):
        self.write(BETA, beta(nid=None))
        r = helpers.run('finish-narrative.py', ['how-does-beta-work', '--root', self.root])
        self.assertIn('has no ID yet: pass --id', r.err)
        self.assertIn('--id is a short kebab-case name', helpers.run('finish-narrative.py', ['how-does-beta-work', '--id', 'Beta!', '--root', self.root]).err)
        r = helpers.run('finish-narrative.py', ['how-does-beta-work', '--id', 'beta', '--root', self.root])
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertIn('filled 1 borrowed term(s)', r.out)
        text = open(os.path.join(self.root, BETA), encoding='utf-8').read()
        self.assertIn('- **ID:** beta\n', text)
        self.assertIn('| **Retry** | Sending a failed request again. From [alpha]', text)
        self.write(BETA, text.replace('#5-how-does-it-work', '#9-how-does-it-work'))
        self.assertIn('repaired 1 link(s)', helpers.run('finish-narrative.py', ['how-does-beta-work', '--root', self.root]).out)


if __name__ == '__main__':
    unittest.main()
