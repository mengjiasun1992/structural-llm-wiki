"""Tests for lib/pdf.py, on PDFs pdfmaker writes."""

import base64
import unittest
import zlib

import helpers  # noqa: F401  (puts scripts/ on the path)
import pdfmaker
from lib import pdf
from pdfmaker import text


def md(data):
    return pdf.markdown(pdf.read(data))


class Text(unittest.TestCase):
    def test_lines_paragraphs_and_page_headings(self):
        page = text((72, 700, b'First line of a paragraph'), (72, 686, b'and its second line.'), (72, 640, b'A new paragraph.'))
        out = md(pdfmaker.make([page, text((72, 700, b'Page two.'))], title=b'A Paper'))
        self.assertEqual(out, '# A Paper\n\n## Page 1\n\nFirst line of a paragraph\nand its second line.\n\nA new paragraph.\n\n'
                              '## Page 2\n\nPage two.\n')

    def test_runs_on_one_baseline_join_with_a_space_for_a_gap(self):
        page = b'BT /F1 10 Tf 72 700 Td (Hello) Tj 40 0 Td (world) Tj ET BT /F1 10 Tf 72 680 Td [(Ker) -30 (ned) -400 (words)] TJ ET'
        self.assertIn('Hello world\nKerned words', md(pdfmaker.make([page])))

    def test_text_operators(self):
        page = (b'BT 72 760 Td (no font) Tj ET q 1 0 0 1 0 -100 cm BT /F1 12 Tf 14 TL 2 Tc 1 Tw 100 Tz 1 0 0 1 72 700 Tm (one) Tj T* (two) Tj '
                b'(three) \' 3 0 (four) " 0 -14 TD (five) Tj ET Q '
                b'BT /F1 12 Tf 72 300 Td (sixty) Tj /Nope 12 Tf ET '
                b'BT /F1 12 Tf 72 280 Td (\\(paren\\) \\\\ \\101\\8 tab\\tx (nested) line\\\ncontinued) Tj ET '
                b'% a comment\nBT /F1 12 Tf 72 260 Td <48 69 3> Tj ET')
        out = md(pdfmaker.make([page]))
        for line in ('one', 'two', 'three', 'four', 'five', 'sixty', '(paren) \\ A8 tab x (nested) linecontinued', 'Hi0'):
            self.assertIn(line + '\n', out)
        self.assertNotIn('no font', out)

    def test_a_producers_placeholder_title_is_left_out(self):
        for title in (b'untitled', b'Microsoft Word - paper.docx', b'draft.pdf'):
            self.assertTrue(md(pdfmaker.make([text((72, 700, b'Body'))], title=title)).startswith('## Page 1'))

    def test_markdown_safe_lines_and_ligatures(self):
        page = text((72, 700, b'# not a heading'), (72, 680, b'> not a quote'), (72, 660, b'e\xef\xac\x81ne'))
        self.assertIn('\\# not a heading\n\\> not a quote', md(pdfmaker.make([page])))

    def test_a_column_jump_starts_a_paragraph(self):
        page = text((72, 700, b'Left column end.'), (320, 740, b'Right column top.'))
        self.assertIn('Left column end.\n\nRight column top.', md(pdfmaker.make([page])))

    def test_forms_and_inline_images(self):
        page = b'BT /F1 12 Tf 72 700 Td (Before) Tj ET BI /W 1 /H 1 ID \x00\xff EI q /X1 Do Q BT /F1 12 Tf 72 500 Td (After) Tj ET'
        out = md(pdfmaker.make([page], xobject=text((72, 500, b'In a form'))))
        self.assertTrue(out.index('Before') < out.index('In a form') < out.index('After'))


class Fonts(unittest.TestCase):
    def test_a_to_unicode_map_with_two_byte_codes(self):
        def font(w):
            cmap = w.stream(b'/CIDInit /ProcSet findresource begin 1 begincodespacerange <0000> <FFFF> endcodespacerange\n'
                            b'2 beginbfchar <0001> <0048> <0002> <00690021> endbfchar\n'
                            b'2 beginbfrange <0010> <0012> <0061> <0020> <0021> [<00D7> <2192>] endbfrange end')
            desc = w.add(b'<< /Type /Font /Subtype /CIDFontType2 /DW 600 /W [1 [500 300] 16 18 450 32] >>')
            return b'<< /Type /Font /Subtype /Type0 /Encoding /Identity-H /DescendantFonts [%d 0 R] /ToUnicode %d 0 R >>' % (desc, cmap)
        page = b'BT /F2 12 Tf 72 700 Td <000100020010001100120020002100FF> Tj ET'
        self.assertIn('Hi!abc×→\n', md(pdfmaker.make([page], fonts={'F2': font})))

    def test_differences_and_glyph_names(self):
        def font(w):
            return (b'<< /Type /Font /Subtype /Type1 /FirstChar 65 /Widths [500 500] /Encoding << /BaseEncoding /MacRomanEncoding '
                    b'/Differences [1 /fi /quoteright /uni0041 /uni00420043 /u1F600 /eacute /Alpha /a.sc /seven /x /nosuchglyph] >> >>')
        page = b'BT /F3 12 Tf 72 700 Td <0102030405060708090A0B0C8E> Tj ET'
        self.assertIn('fi’ABC\U0001F600éΑa7xé\n', md(pdfmaker.make([page], fonts={'F3': font})))

    def test_glyph(self):
        self.assertEqual([pdf.glyph(n) for n in ('Eacute', 'omega', 'Zcaron', 'Q', 'ring', 'g123')], ['É', 'ω', 'Ž', 'Q', '', ''])


class Structure(unittest.TestCase):
    OUTLINE = [(0, b'Introduction', 0, None), (1, b'Background', 0, 650), (0, b'Design', 1, 720), (1, b'Not on the page', 1, None)]

    def pages(self):
        return [text((72, 720, b'1 Introduction'), (72, 700, b'Intro text.'), (72, 640, b'Some background.')),
                text((72, 700, b'3 Design'), (72, 680, b'Design text.'))]

    def test_the_outline_becomes_headings_where_it_points(self):
        for names in (None, 'dests', 'tree', 'action'):
            with self.subTest(names=names):
                out = md(pdfmaker.make(self.pages(), self.OUTLINE, names=names))
                self.assertEqual(out, '## Introduction\n\nIntro text.\n\n### Background\n\nSome background.\n\n'
                                      '## Design\n\n### Not on the page\n\nDesign text.\n')

    def test_compressed_object_streams_and_filters(self):
        for packed, compress in ((True, True), (True, False), (False, False)):
            with self.subTest(packed=packed, compress=compress):
                out = md(pdfmaker.make(self.pages(), self.OUTLINE, packed=packed, compress=compress, title=b'\xfe\xff\x00T\x00i'))
                self.assertTrue(out.startswith('# Ti\n\n## Introduction\n'))
        page = text((72, 700, b'Hex'))
        for name, raw in ((b'/ASCIIHexDecode', page.hex().encode() + b'>'), (b'[/ASCII85Decode]', b'<~' + base64.a85encode(page) + b'~>'),
                          (b'[/ASCII85Decode /FlateDecode]', base64.a85encode(zlib.compress(page)) + b'~>')):
            self.assertIn('Hex', md(pdfmaker.make([page], stream_filters=(name, raw))))
        bad = (b'/ASCII85Decode', b'zz~>'), (b'/LZWDecode', b'x'), (b'/FlateDecode', b'not zlib')
        for f in bad:
            with self.assertRaises(pdf.PdfError):
                pdf.read(pdfmaker.make([page], stream_filters=f))

    def test_a_later_revision_wins_and_a_stream_length_by_reference(self):
        data = pdfmaker.make([text((72, 700, b'Old'))], compress=False)
        content = b'BT /F1 12 Tf 72 700 Td (New) Tj ET'
        data += b'4 0 obj\n<< /Length 99 0 R >>\nstream\n' + content + b'\nendstream\nendobj\ntrailer\n<< /Root 1 0 R >>\n'
        self.assertIn('New', md(data))

    def test_slices(self):
        many = [text((72, 700, b'Chapter %d' % i if i in (0, 60) else b'Body %d' % i)) for i in range(SLICE_PAGES + 1)]
        outline = [(0, b'Chapter 0', 0, None), (1, b'Section', 1, None), (0, b'Chapter 60', 60, None)]
        doc = pdf.read(pdfmaker.make(many, outline, title=b'Book'))
        parts = pdf.slices(doc, pdf.markdown(doc))
        self.assertEqual([(t, p) for t, p, _ in parts], [('Chapter 0', 0), ('Chapter 60', 60)])
        self.assertTrue(parts[0][2].startswith('# Book\n\n## Chapter 0\n\nBody 1') or parts[0][2].startswith('# Book\n\n## Chapter 0'))
        self.assertIn('### Section', parts[0][2])
        self.assertTrue(parts[1][2].startswith('## Chapter 60\n\nBody 61'))
        self.assertEqual(pdf.slices(pdf.read(pdfmaker.make(many[:SLICE_PAGES], outline[:2])), ''), [])  # short
        self.assertEqual(pdf.slices(pdf.read(pdfmaker.make(many)), ''), [])  # no outline


SLICE_PAGES = pdf.SLICE_PAGES


class Refusals(unittest.TestCase):
    def test_what_it_cant_read(self):
        page = text((72, 700, b'x'))
        for data, msg in ((b'<html>', 'not a PDF'), (pdfmaker.make([page], encrypt=True), 'encrypted'),
                          (pdfmaker.make([b'0 0 m 10 10 l S']), 'no text layer'),
                          (b'%PDF-1.4\n1 0 obj\n<< /Type /Pages >>\nendobj\n', 'no catalog'),
                          (b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n', 'no pages'),
                          (b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n2 0 obj\n(unclosed\n', 'no pages')):
            with self.subTest(msg=msg), self.assertRaises(pdf.PdfError) as e:
                pdf.read(data)
            self.assertIn(msg, str(e.exception))

    def test_broken_objects_are_left_out(self):
        content = b'BT /F1 12 Tf 72 700 Td (Kept) Tj /F1 bad Tz /F2 12 Tf 72 680 Td <0001> Tj ET'
        objs = {
            1: b'<< /Type /Catalog /Pages 2 0 R /Outlines 6 0 R /Dests << /d << /D [3 0 R /FitH 650] >> >> >>',
            2: b'<< /Type /Pages /Kids [3 0 R 20 0 R 14 0 R] >>',
            3: b'<< /Type /Page /Contents 4 0 R /Resources << /Font << /F1 15 0 R /F2 5 0 R >> >> >>',
            4: b'<< /Length %d >>\nstream\n%s\nendstream' % (len(content), content),
            5: b'<< /Subtype /Type0 /ToUnicode 9 0 R /DescendantFonts [10 0 R] >>',
            6: b'<< /First 7 0 R >>',
            7: b'<< /Title (Kept) /Dest /d /Next 8 0 R >>',
            8: b'<< /Title (Nowhere) /Dest [] /Next 11 0 R /First 12 0 R >>',
            9: b'<< /Filter /LZWDecode /Length 1 >>\nstream\nx\nendstream',
            10: b'<< /W [1 [500] 2 3] >>',
            11: b'<< /Title (Loop) /Dest [3 0 R /Fit] /Next 11 0 R >>',
            12: b'(not a dictionary)',
            13: b'<< /Type /ObjStm /N 1 /First 4 >>',
            14: b'<< /Length 5 >>\nstream\nno end',
            15: pdfmaker.HELVETICA,
        }
        data = b'%PDF-1.4\n' + b''.join(b'%d 0 obj\n%s\nendobj\n' % kv for kv in objs.items()) + b'trailer\n<< /Root 1 0 R >>\n'
        doc = pdf.read(data)
        self.assertEqual([e[1] for e in doc.outline], ['Kept', 'Loop'])
        self.assertEqual(doc.outline[0][3], 650)
        self.assertEqual(pdf.markdown(doc), '## Kept\n\n## Loop\n')  # the line is the heading; the two-byte code has no text

    def test_broken_pieces_are_skipped(self):
        lx = pdf.Lexer(b'<4> ) } [1 2 R] <</A 1 /B>> /N#41me 1.5 -.5 true null')
        self.assertEqual([lx.value() for _ in range(7)], [b'\x40', [pdf.Ref((1, 2))], {'A': 1}, 'NAme', 1.5, -0.5, True])
        with self.assertRaises(pdf.PdfError):
            pdf.Lexer(b'<41').token()
        with self.assertRaises(pdf.PdfError):
            pdf.Lexer(b'(open').token()
        self.assertEqual(pdf.text_string(b'Latin \xe9'), 'Latin é')
        self.assertEqual(pdf.text_string(None), '')


if __name__ == '__main__':
    unittest.main()
