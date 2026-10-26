"""Tests for lib/narrativecheck.py and scripts/narrative-format.py."""

import json
import os
import unittest

import helpers
from lib import manifest, narrativecheck

NARRATIVE = 'sllmwiki/narratives/what-is-alpha.md'


class Checks(helpers.WikiTestCase):
    def codes(self, text, **settings):
        from lib import config, templates
        s = {**config.DEFAULTS, **settings}
        return [(c, n) for _, c, n, _ in narrativecheck.check(self.root, NARRATIVE, text, s, templates.available(self.root)[0])]

    def test_the_fixture_passes(self):
        self.assertEqual(self.codes(helpers.narrative_text()), [])

    def test_title_and_template(self):
        text = helpers.narrative_text()
        self.assertIn(('NO_TITLE', 1), self.codes(text.replace('# What is alpha?', 'What is alpha?', 1)))
        self.assertIn(('NO_TEMPLATE', 1), self.codes(text.replace('- **Template:** technical_brief_overview\n', '')))
        self.assertIn(('UNKNOWN_TEMPLATE', 1), self.codes(text.replace('technical_brief_overview', 'runbook')))

    def test_sections(self):
        text = helpers.narrative_text()
        missing = text.replace('## 6. Design decisions and trade-offs\n\nWaiting longer each time spares a struggling server.\n\n', '')
        self.assertIn('MISSING_SECTION', [c for c, _ in self.codes(missing)])
        swapped = text.replace('## 3. Background', '## 3. Limitations and failure modes', 1)
        self.assertIn('SECTION_ORDER', [c for c, _ in self.codes(swapped)])
        extra = text.replace('## 6. Design', '## 6. My own section\n\nText.\n\n## 7. Design', 1)
        self.assertIn('EXTRA_SECTION', [c for c, _ in self.codes(extra)])
        no_diagram = text.replace('```mermaid\ngraph LR\n    A[Request fails] --> B[Wait, then retry]\n```\n', '')
        self.assertIn('MISSING_DIAGRAM', [c for c, _ in self.codes(no_diagram)])
        diagram = '```mermaid\ngraph LR\n    A[Request fails] --> B[Wait, then retry]\n```\n'
        placeholder = text.replace(diagram, '```mermaid\n%% <the diagram that shows how it works best>\n\n```\n```text\nnot a diagram\n```\n')
        self.assertIn('MISSING_DIAGRAM', [c for c, _ in self.codes(placeholder)])
        sequence = text.replace(diagram, '```mermaid\n%% the retry\nsequenceDiagram\n    Client->>Server: request\n```\n')
        self.assertNotIn('MISSING_DIAGRAM', [c for c, _ in self.codes(sequence)])
        cut = text[:text.index('## 8. References')] + text[text.index('## 9. Metadata'):]
        self.assertEqual([c for c, _ in self.codes(cut) if c == 'MISSING_SECTION'], ['MISSING_SECTION'])
        no_end = text[:text.index('## 8. References')] + '- **Template:** technical_brief_overview\n'
        self.assertEqual([c for c, _ in self.codes(no_end) if c == 'NO_TEMPLATE'], ['NO_TEMPLATE'])  # Metadata is where the template is named

    def test_lengths(self):
        text = helpers.narrative_text()
        self.assertIn(('ABSTRACT_LENGTH', 1), self.codes(text.replace(helpers.ABSTRACT, 'Too short.')))
        long = text.replace('Requests fail, and alpha systems send them again.', ' '.join(['word'] * 1900))
        self.assertIn(('BODY_LENGTH', 1), self.codes(long))
        self.write('Config.toml', '[structural-llm-wiki-templates.technical_brief_overview]\nmax_words = 3000\n')
        self.assertNotIn(('BODY_LENGTH', 1), self.codes(long))

    def test_numbers_and_citations(self):
        text = helpers.narrative_text()
        self.assertIn('HEADING_NUMBER', [c for c, _ in self.codes(text.replace('## 3. Background', '## 9. Background'))])
        self.assertIn('CITATION_BROKEN', [c for c, _ in self.codes(helpers.narrative_text(cites=(('alpha-doc', 'nope'),)))])
        self.assertIn('CITATION_SOURCE', [c for c, _ in self.codes(helpers.narrative_text(cites=(('gamma-link', 'x'),)))])
        self.assertIn('CITATION_SOURCE', [c for c, _ in self.codes(helpers.narrative_text(cites=(('nobody', 'x'),)))])
        web = text.replace('../sources/alpha-doc.md#details', 'https://example.com/alpha')
        self.assertEqual([c for c, _ in self.codes(web) if c.startswith('CITATION')], ['CITATION_TARGET'])
        self.assertIn('CITATION_UNLISTED', [c for c, _ in self.codes(text.replace('1. [alpha-doc: details]', '- [alpha-doc: details]'))])

    def test_markers(self):
        marked = helpers.narrative_text(extra='\nDoubling the wait suits most clients. [→]\n')
        self.assertIn('MARKER_UNDEFINED', [c for c, _ in self.codes(marked)])
        self.assertIn('MARKER_OFF', [c for c, _ in self.codes(marked, markers=False)])
        heading = helpers.narrative_text().replace('## 7. Limitations and failure modes\n\nRetries', '## 7. Limitations and failure modes [→]\n\nRetries')
        self.assertEqual([c for c, _ in self.codes(heading) if c.startswith(('MISSING', 'SECTION', 'EXTRA'))], [])  # a marked heading is still its section

    def test_placeholders_and_markdown(self):
        text = helpers.narrative_text()
        self.assertIn('PLACEHOLDER', [c for c, _ in self.codes(text.replace('Requests fail', '<The problem X solves> Requests fail'))])
        ok = text.replace('Requests fail', 'See <https://e.com> and `<not a placeholder>`. Requests fail')
        self.assertEqual(self.codes(ok), [])
        self.assertIn('WIKILINK', [c for c, _ in self.codes(text.replace('Requests fail', 'See [[note]]. Requests fail'))])
        doubled = text.replace('Requests fail, and', 'Requests fail,, and')
        self.assertIn('DOUBLED_PUNCTUATION', [c for c, _ in self.codes(doubled)])
        fine = text.replace('Requests fail, and', 'Requests fail... and, see [x](../sources/alpha-doc.md#details), `a,,b` and')
        self.assertNotIn('DOUBLED_PUNCTUATION', [c for c, _ in self.codes(fine)])
        for formula in ('s_t = a x_t', 's_{t-1} is kept', 'weights α·(1 − α)', 'with = α'):
            self.assertIn('MATH_AS_TEXT', [c for c, _ in self.codes(text.replace('Requests fail', formula + '. Requests fail'))], formula)
        for fine in ('$s_t = \\alpha x_t$', '`max_quote_words`', 'snake_case_names', 'Greek α alone'):
            self.assertNotIn('MATH_AS_TEXT', [c for c, _ in self.codes(text.replace('Requests fail', fine + '. Requests fail'))], fine)
        self.assertIn('LINK_PATH', [c for c, _ in self.codes(text.replace('Requests fail', 'See [x](nowhere.md). Requests fail'))])

    def test_words(self):
        self.assertEqual(narrativecheck.words(['A [link](https://x.y/z) and `code`.', '|---|---|', '```text', 'one two']), 6)


class Command(helpers.WikiTestCase):
    def nf(self, *argv):
        return helpers.run('narrative-format.py', ['--root', self.root, *argv])

    def test_all_narratives(self):
        r = self.nf()
        self.assertEqual((r.code, r.out), (0, 'narrative-format: 0 error(s), 0 warning(s) in 1 narrative(s)\n'))

    def test_findings_json_and_exit_code(self):
        self.write(NARRATIVE, helpers.narrative_text().replace('## 3. Background', '## Background'))
        r = self.nf('--json')
        self.assertEqual(r.code, 1)
        data = json.loads(r.out)
        self.assertEqual((data['errors'], data['findings'][0]['code']), (1, 'HEADING_UNNUMBERED'))
        r = self.nf(f'{self.root}/{NARRATIVE}')
        self.assertIn('error    HEADING_UNNUMBERED   sllmwiki/narratives/what-is-alpha.md:', r.out)

    def test_fixes(self):
        self.write(NARRATIVE, helpers.narrative_text().replace('## 3. Background', '## Background').replace('Requests fail', 'Costs $5. Requests fail'))
        r = self.nf('--fix-numbering', '--fix-style')
        self.assertEqual(r.code, 0, r.out)
        self.assertIn('fixed sllmwiki/narratives/what-is-alpha.md', r.out)
        text = self.read(NARRATIVE)
        self.assertIn('## 3. Background', text)
        self.assertIn('Costs \\$5.', text)
        r = helpers.run('narrative-format.py', ['--root', self.root, 'sllmwiki/narratives/what-is-alpha.md'], cwd=self.root)
        self.assertEqual(r.code, 0)

    def test_warnings_dont_fail(self):
        self.write(NARRATIVE, helpers.narrative_text().replace('Requests fail', 'See https://e.com. Requests fail'))
        r = self.nf()
        self.assertEqual(r.code, 0)
        self.assertIn('BARE_URL', r.out)

    def test_stats(self):
        manifest.put_narrative(self.root, 'what-is-alpha', 'technical_brief_overview', ['leaf-a'], [], ['alpha-doc'],
                               {'alpha-doc': {'relevance': 'high', 'authority': 'A'}})
        self.write(NARRATIVE, helpers.narrative_text(cites=(('alpha-doc', 'details'), ('beta-doc', 'beta')),
                                                     extra='\nMine. [→]\n').replace('## 7. Limitations and failure modes', '## 7. Limitations and failure modes [→]'))
        path = os.path.join(self.root, NARRATIVE)
        r = self.nf(path, '--stats', '--json')
        s = json.loads(r.out)['narratives'][0]
        self.assertEqual((s['template'], s['budget'], s['citations'], s['markers'], s['pictures']),
                         ('technical_brief_overview', 1800, {'A': 1, 'B': 0, 'C': 0, 'ungraded': 1}, {'statements': 1, 'headings': 1}, 1))
        self.assertEqual([x['section'] for x in s['sections']], ['Background', 'The core idea', 'How does it work?',
                                                                 'Design decisions and trade-offs', 'Limitations and failure modes'])
        out = self.nf(path, '--stats').out
        self.assertIn('(technical_brief_overview): body', out)
        self.assertIn('  The core idea: ', out)
        how = next(x for x in s['sections'] if x['section'] == 'How does it work?')
        self.assertEqual((how['citations'], how['markers']), (2, 1))
        self.assertIn('no such file', self.nf('nope.md', '--stats').err)

    def test_templates_and_skeleton(self):
        r = self.nf('--templates')
        self.assertEqual(r.code, 0)
        self.assertIn('technical_brief_overview (bundled, body up to 1800 words; aim: concise, authoritative, depth over breadth)', r.out)
        rows = json.loads(self.nf('--templates', '--json').out)['templates']
        self.assertEqual([t['name'] for t in rows], ['case_study', 'comparison', 'concept_brief_overview', 'survey', 'technical_brief_overview'])
        skel = self.nf('--skeleton', 'concept_brief_overview').out
        self.assertTrue(skel.startswith('# <The question, exactly as asked>\n'))
        self.assertIn('## 3. Overview', skel)
        self.assertEqual(self.nf('--skeleton', 'nope').code, 1)

    def test_template_problems(self):
        helpers.write(self.root, 'sllmwiki/templates/broken/template.md', 'no header\n')
        r = self.nf('--templates')
        self.assertEqual(r.code, 1)
        self.assertIn('problem: wiki template broken', r.out)
        r = self.nf()
        self.assertEqual(r.code, 1)
        self.assertIn('TEMPLATE_INVALID', r.out)

    def test_missing_file(self):
        r = self.nf('nope.md')
        self.assertEqual((r.code, r.err), (1, 'narrative-format.py: no such file: nope.md\n'))


if __name__ == '__main__':
    unittest.main()
