"""Tests for lib/figures.py: the figures a narrative embeds, and wiki-check's unused ones."""

import os
import unittest

import helpers
from lib import config, figures, narrativecheck, templates

NARRATIVE = 'sllmwiki/narratives/what-is-alpha.md'
SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10" fill="#fff"/></svg>\n'
DIAGRAM = '```mermaid\ngraph LR\n    A[Request fails] --> B[Wait, then retry]\n```\n'


class Figures(helpers.WikiTestCase):
    def codes(self, text, **settings):
        s = {**config.DEFAULTS, **settings}
        return [(c, n) for _, c, n, _ in narrativecheck.check(self.root, NARRATIVE, text, s, templates.available(self.root)[0])]

    def figure(self, name='waits.svg', body=SVG):
        self.write(f'sllmwiki/narratives/figures/what-is-alpha/{name}', body)

    def with_image(self, line):
        return helpers.narrative_text().replace('Wait longer after each failure.\n', f'Wait longer after each failure.\n\n{line}\n')

    def test_a_figure_passes_and_stands_in_for_a_diagram(self):
        self.figure()
        text = self.with_image('![Each wait twice the last](figures/what-is-alpha/waits.svg)')
        self.assertEqual(self.codes(text), [])
        self.assertEqual(self.codes(text.replace(DIAGRAM, '')), [])  # a figure is the section's picture
        self.assertEqual(figures.images(text + '\n```text\n![not](an/image.svg)\n```\n')[0][1:], ('Each wait twice the last', 'figures/what-is-alpha/waits.svg'))

    def test_problems(self):
        self.figure()
        self.figure('waits.png', 'png')
        self.figure('dark.svg', '<svg xmlns="http://www.w3.org/2000/svg"><text>x</text></svg>')
        self.figure('script.svg', '<svg><rect fill="#fff"/><script>alert(1)</script></svg>')
        self.figure('remote.svg', '<svg><rect fill="#fff"/><image href="https://example.com/x.png"/></svg>')
        self.figure('big.svg', SVG + ' ' * figures.MAX_BYTES)
        cases = [
            ('![x](figures/what-is-alpha/waits.svg)', {'images': False}, 'IMAGE_OFF'),
            ('![x](waits.svg)', {}, 'IMAGE_PLACE'),
            ('![x](figures/other/waits.svg)', {}, 'IMAGE_PLACE'),
            ('![x](figures/what-is-alpha/waits.gif)', {}, 'IMAGE_PLACE'),
            ('![x](https://example.com/waits.svg)', {}, 'IMAGE_PLACE'),
            ('![ ](figures/what-is-alpha/waits.png)', {}, 'IMAGE_ALT'),
            ('![x](figures/what-is-alpha/gone.svg)', {}, 'LINK_PATH'),
            ('![x](figures/what-is-alpha/dark.svg)', {}, 'IMAGE_BACKGROUND'),
            ('![x](figures/what-is-alpha/script.svg)', {}, 'IMAGE_UNSAFE'),
            ('![x](figures/what-is-alpha/remote.svg)', {}, 'IMAGE_UNSAFE'),
            ('![x](figures/what-is-alpha/big.svg)', {}, 'IMAGE_SIZE'),
        ]
        for line, settings, code in cases:
            with self.subTest(line=line):
                self.assertEqual([c for c, _ in self.codes(self.with_image(line), **settings) if c != 'LINK_PATH' or code == 'LINK_PATH'], [code])

    def test_unused_figures(self):
        self.assertEqual(figures.unused(self.root), [])
        self.figure()
        self.figure('old.svg')
        self.write('sllmwiki/narratives/figures/gone-question/x.svg', SVG)
        self.write('sllmwiki/narratives/figures/stray.svg', SVG)  # not in a narrative's folder: no slug to judge it by
        self.write(NARRATIVE, self.with_image('![Each wait](figures/what-is-alpha/waits.svg)'))
        got = [(c, f) for _, c, f, _ in figures.unused(self.root)]
        self.assertEqual(got, [('FIGURE_UNUSED', 'sllmwiki/narratives/figures/gone-question/x.svg'),
                               ('FIGURE_UNUSED', 'sllmwiki/narratives/figures/what-is-alpha/old.svg')])
        r = helpers.run('wiki-check.py', ['--root', self.root])
        self.assertIn('FIGURE_UNUSED', r.out)
        self.assertTrue(os.path.isfile(os.path.join(self.root, 'sllmwiki/narratives/figures/stray.svg')))


if __name__ == '__main__':
    unittest.main()
