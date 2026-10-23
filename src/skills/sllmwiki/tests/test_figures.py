"""Tests for lib/figures.py: the figures a narrative embeds, their captions, and wiki-check's unused ones."""

import os
import unittest

import helpers
from lib import config, figures, narrativecheck, templates

NARRATIVE = 'sllmwiki/narratives/what-is-alpha.md'
SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10" fill="#fff"/></svg>\n'
DIAGRAM = '```mermaid\ngraph LR\n    A[Request fails] --> B[Wait, then retry]\n```\n\n*Figure 4-1: A failed request waits, then retries.*\n'


def png(width, extra=0):
    return figures.PNG + b'\x00\x00\x00\x0dIHDR' + width.to_bytes(4, 'big') + (10).to_bytes(4, 'big') + b'\x00' * extra


class Figures(helpers.WikiTestCase):
    def codes(self, text, **settings):
        s = {**config.DEFAULTS, **settings}
        return [(c, n) for _, c, n, _ in narrativecheck.check(self.root, NARRATIVE, text, s, templates.available(self.root)[0])]

    def figure(self, name='waits.svg', body=SVG):
        path = os.path.join(self.root, 'sllmwiki/narratives/figures/what-is-alpha', name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(body.encode() if isinstance(body, str) else body)

    def with_image(self, line, label='4-2'):
        caption = '*Figure 4-1: A failed request waits, then retries.*\n'
        return helpers.narrative_text().replace(caption, f'{caption}\n{line}\n\n*Figure {label}: Each wait twice the last.*\n')

    def test_a_figure_passes_and_stands_in_for_a_diagram(self):
        self.figure()
        text = self.with_image('![Each wait twice the last](figures/what-is-alpha/waits.svg)')
        self.assertEqual(self.codes(text), [])
        self.assertEqual(self.codes(text.replace(DIAGRAM, '').replace('Figure 4-2', 'Figure 4-1')), [])  # a figure is the section's picture
        self.assertEqual(figures.images(text + '\n```text\n![not](an/image.svg)\n```\n')[0][1:], ('Each wait twice the last', 'figures/what-is-alpha/waits.svg'))
        self.figure('waits.png', png(800))
        self.assertEqual(self.codes(self.with_image('![x](figures/what-is-alpha/waits.png)')), [])

    def test_problems(self):
        self.figure()
        self.figure('waits.png', 'png')
        self.figure('fake.png', 'not a png at all, but long enough')
        self.figure('fake.svg', '<html><svg/></html>')
        self.figure('dark.svg', '<?xml version="1.0"?>\n<!-- made by hand -->\n<svg xmlns="http://www.w3.org/2000/svg"><text>x</text></svg>')
        self.figure('script.svg', '<svg><rect fill="#fff"/><script>alert(1)</script></svg>')
        self.figure('remote.svg', '<svg><rect fill="#fff"/><image href="data:image/png;base64,AAAA"/></svg>')
        self.figure('big.svg', SVG + ' ' * figures.MAX_SVG_BYTES)
        self.figure('wide.png', png(figures.MAX_PNG_WIDTH + 1))
        self.figure('heavy.png', png(800, figures.MAX_PNG_BYTES))
        cases = [
            ('![x](figures/what-is-alpha/waits.svg)', {'images': False}, 'IMAGE_OFF'),
            ('![x](waits.svg)', {}, 'IMAGE_PLACE'),
            ('![x](figures/other/waits.svg)', {}, 'IMAGE_PLACE'),
            ('![x](figures/what-is-alpha/waits.gif)', {}, 'IMAGE_PLACE'),
            ('![x](https://example.com/waits.svg)', {}, 'IMAGE_PLACE'),
            ('![ ](figures/what-is-alpha/waits.svg)', {}, 'IMAGE_ALT'),
            ('![x](figures/what-is-alpha/gone.svg)', {}, 'LINK_PATH'),
            ('![x](figures/what-is-alpha/waits.png)', {}, 'IMAGE_FORMAT'),
            ('![x](figures/what-is-alpha/fake.png)', {}, 'IMAGE_FORMAT'),
            ('![x](figures/what-is-alpha/fake.svg)', {}, 'IMAGE_FORMAT'),
            ('![x](figures/what-is-alpha/dark.svg)', {}, 'IMAGE_BACKGROUND'),
            ('![x](figures/what-is-alpha/script.svg)', {}, 'IMAGE_UNSAFE'),
            ('![x](figures/what-is-alpha/remote.svg)', {}, 'IMAGE_UNSAFE'),
            ('![x](figures/what-is-alpha/big.svg)', {}, 'IMAGE_SIZE'),
            ('![x](figures/what-is-alpha/wide.png)', {}, 'IMAGE_SIZE'),
            ('![x](figures/what-is-alpha/heavy.png)', {}, 'IMAGE_SIZE'),
        ]
        for line, settings, code in cases:
            with self.subTest(line=line):
                self.assertEqual([c for c, _ in self.codes(self.with_image(line), **settings) if c != 'LINK_PATH' or code == 'LINK_PATH'], [code])

    def test_captions(self):
        text = helpers.narrative_text()
        line = text.split('\n').index('*Figure 4-1: A failed request waits, then retries.*') + 1
        cases = [
            (text.replace('*Figure 4-1: A failed request waits, then retries.*\n', ''), [('FIGURE_CAPTION', line - 5)]),
            (text.replace('*Figure 4-1: A failed request waits, then retries.*', '*Figure 4-1:*'), [('FIGURE_CAPTION', line)]),
            (text.replace('Figure 4-1:', 'Figure 2-7:'), [('FIGURE_NUMBER', line)]),
            (text.replace('Wait longer after each failure.', 'Wait longer, as Figure 4-1 shows, not Figure 9-9.'), [('FIGURE_REF', line - 7)]),
            (text.replace('```mermaid\ngraph', '```text\nnot a diagram\n```\n\n```mermaid\ngraph'), []),
        ]
        for got, want in cases:
            with self.subTest(want=want):
                self.assertEqual([f for f in self.codes(got) if f[0].startswith('FIGURE')], want)

    def test_renumber(self):
        text = helpers.narrative_text().replace('Figure 4-1:', 'Figure 3-2:').replace(
            'Wait longer after each failure.', 'Wait longer after each failure, as Figure 3-2 shows; Figure 7-7 is elsewhere.')
        text += '\n```mermaid\ngraph LR\n    A --> B\n```\n\n*Figure 1-1: Another.*\n\n```mermaid\ngraph LR\n    C --> D\n```\n\n*Figure 9-9*\n'  # a malformed caption stays as it is
        fixed, n = figures.renumber(text)
        self.assertEqual(n, 2)
        self.assertIn('*Figure 4-1: A failed request waits, then retries.*', fixed)
        self.assertIn('as Figure 4-1 shows; Figure 7-7 is elsewhere.', fixed)
        self.assertIn('*Figure 9-1: Another.*', fixed)
        self.assertEqual(figures.renumber(fixed), (fixed, 0))
        self.write(NARRATIVE, text)
        self.assertIn('fixed', helpers.run('narrative-format.py', [os.path.join(self.root, NARRATIVE), '--fix-numbering', '--root', self.root]).out)
        with open(os.path.join(self.root, NARRATIVE), encoding='utf-8') as f:
            self.assertIn('*Figure 4-1:', f.read())

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
