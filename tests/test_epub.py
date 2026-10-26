"""Tests for lib/epub.py: an EPUB book as markdown, and long ones in slices."""

import io
import unittest
import zipfile

import epubmaker
import helpers  # noqa: F401 (puts the scripts on the path)
from lib import epub

CH1 = '<h1>Retries</h1><p>A retry costs a <a href="ch2.xhtml#budget">budget</a>, see <a href="https://example.com/x">the paper</a>.</p>'
CH2 = '<section><h2 id="budget">Budgets</h2><h3>Why</h3><p>Ten percent.</p><img src="img/cap.png" alt="the cap"/><pre><code># not a heading</code></pre></section>'
TOC = [(0, 'Retries', 'ch1.xhtml'), (0, 'Budgets', 'ch2.xhtml'), (1, 'Why', 'ch2.xhtml#why')]


def book(**kw):
    return epub.read(epubmaker.make([('ch1.xhtml', CH1), ('ch2.xhtml', CH2)], TOC, **kw))


class Epub(unittest.TestCase):
    def test_chapters_in_reading_order_under_the_title(self):
        text = epub.markdown(book(title='Budgets &amp; Retries'))
        self.assertEqual(text, '# Budgets & Retries\n\n## Retries\n\nA retry costs a budget, see [the paper](<https://example.com/x>).\n\n'
                               '## Budgets\n\n### Why\n\nTen percent.\n\n\\[image: the cap\\]\n\n```\n# not a heading\n```\n')

    def test_epub2_ncx_and_a_chapter_without_a_heading(self):
        b = epub.read(epubmaker.make([('a.xhtml', '<p>Opening words.</p>'), ('b.xhtml', '<h4>Deep</h4><h5>Deeper</h5>')],
                                     [(0, 'Prologue', 'a.xhtml'), (0, 'Body', 'b.xhtml')], version=2, title=''))
        self.assertEqual(b.toc, [(0, 'Prologue', 'OEBPS/a.xhtml', ''), (0, 'Body', 'OEBPS/b.xhtml', '')])
        self.assertEqual(epub.markdown(b), '## Prologue\n\nOpening words.\n\n## Deep\n\n### Deeper\n')

    def test_what_is_left_out(self):
        b = epub.read(epubmaker.make([('cover.xhtml', '<img src="cover.jpg" alt=""/>'), ('note.xhtml', '<p>Aside.</p>'), ('a.xhtml', '<p>Text.</p>')],
                                     linear_no=('note.xhtml',)))
        self.assertEqual([p for p, _ in b.chapters], ['OEBPS/cover.xhtml', 'OEBPS/a.xhtml'])  # not the non-linear note
        self.assertEqual(epub.markdown(b), '# Book\n\n\\[image: \\]\n\nText.\n')
        self.assertEqual(epub.read(epubmaker.make([('a.xhtml', '<p>x</p>')], folder='')).chapters[0][0], 'a.xhtml')

    def test_encrypted_chapters_are_refused_obfuscated_fonts_are_not(self):
        with self.assertRaisesRegex(epub.EpubError, 'encrypted \\(DRM\\); never get around it'):
            book(encrypted=[('ch2.xhtml', epubmaker.ENC)])
        self.assertEqual(len(book(encrypted=[('font.otf', epubmaker.ENC), ('ch1.xhtml', epubmaker.FONTS)]).chapters), 2)

    def test_broken_books(self):
        def zipped(files):
            out = io.BytesIO()
            with zipfile.ZipFile(out, 'w') as z:
                for name, text in files.items():
                    z.writestr(name, text)
            return out.getvalue()
        container = '<container><rootfiles><rootfile full-path="p.opf"/></rootfiles></container>'
        for data, msg in ((b'PK not a zip', 'not a zip archive'), (zipped({}), 'no META-INF/container.xml'),
                          (zipped({'META-INF/container.xml': '<container'}), 'container.xml isn\'t XML'),
                          (zipped({'META-INF/container.xml': '<container/>'}), 'names no package'),
                          (zipped({'META-INF/container.xml': container, 'p.opf': '<package><spine/></package>'}), 'lists no chapters')):
            with self.assertRaisesRegex(epub.EpubError, msg):
                epub.read(data)

    def test_long_books_in_slices(self):
        words = ' '.join(['word'] * (epub.SLICE_WORDS // 2))
        chapters = [('front.xhtml', '<p>Copyright page.</p>'), ('p1.xhtml', f'<h1>Part One</h1><p>{words}</p>'),
                    ('c1.xhtml', '<h1>Chapter 1</h1><p>One.</p>'), ('p2.xhtml', f'<h1>Part Two</h1><p>{words}</p>'),
                    ('end.xhtml', '<h1>Colophon</h1><p>Set in type.</p>')]
        toc = [(0, 'Part One', 'p1.xhtml'), (1, 'Chapter 1', 'c1.xhtml'), (0, 'Part Two', 'p2.xhtml'), (0, 'Colophon', 'end.xhtml')]
        b = epub.read(epubmaker.make(chapters, toc))
        text = epub.markdown(b)
        self.assertIn('## Part One', text)
        self.assertIn('### Chapter 1', text)  # a heading takes its depth from the contents
        parts = epub.slices(b, text)
        self.assertEqual([(t, f) for t, f, _ in parts], [('Part One', 'chapter=1'), ('Part Two', 'chapter=2')])
        self.assertTrue(parts[0][2].startswith('Copyright page.\n\n## Part One'))  # the front matter opens the first
        self.assertTrue(parts[1][2].rstrip().endswith('Set in type.'))  # the short colophon joins the last
        self.assertEqual(epub.slices(b, 'short'), [])
        one = epub.read(epubmaker.make(chapters[1:3], toc[:2]))
        self.assertEqual(epub.slices(one, ' '.join(['w'] * (epub.SLICE_WORDS + 1))), [])  # one entry: nothing to cut

    def test_an_entry_too_long_is_cut_by_its_chapters_run_together(self):
        quarter = ' '.join(['word'] * (epub.SLICE_WORDS // 4))
        chapters = [('intro.xhtml', f'<h1>Introduction</h1><p>{quarter}</p>'), ('half.xhtml', '<h1>The Novel</h1>')]
        chapters += [(f'c{n}.xhtml', f'<h1>Chapter {n}</h1><p>{quarter}</p>') for n in range(1, 6)]
        toc = [(0, 'Introduction', 'intro.xhtml'), (0, 'The Novel', 'half.xhtml')] + [(1, f'Chapter {n}', f'c{n}.xhtml') for n in range(1, 6)]
        b = epub.read(epubmaker.make(chapters, toc))
        parts = epub.slices(b, epub.markdown(b))
        self.assertEqual([t for t, _, _ in parts], ['Introduction', 'Chapter 1 – Chapter 3', 'Chapter 4 – Chapter 5'])
        self.assertTrue(parts[1][2].startswith('## The Novel\n\n### Chapter 1'))  # the half-title opens the first run


if __name__ == '__main__':
    unittest.main()
