"""Tests for lib/book.py: the book's parts, chapter order and cited sources (docs/book_design.md §5)."""

import os
import unittest

import helpers
from lib import book, language
from lib.book import Chapter


def chapters(*specs):
    """{slug: Chapter} from (slug, template, question, built_on) tuples."""
    return {s: Chapter(s, q, t, 'leaf-a', b) for s, t, q, b in specs}


class TeachingOrder(unittest.TestCase):
    def test_ties_go_by_template_then_question(self):
        found = chapters(('c', 'comparison', 'Alpha or beta?', ()), ('t', 'technical_brief_overview', 'How does alpha work?', ()),
                         ('s', 'survey', 'What kinds of alpha are there?', ()), ('k', 'concept_brief_overview', 'What is alpha?', ()),
                         ('z', 'case_study', 'How did Acme use alpha?', ()), ('a', 'concept_brief_overview', 'Apples?', ()),
                         ('own', 'house_style', 'Anything?', ()))
        self.assertEqual(book.teaching_order(found), ['a', 'k', 's', 't', 'c', 'z', 'own'])  # a wiki's own template last

    def test_a_chapter_comes_after_what_it_is_built_on(self):
        found = chapters(('basics', 'comparison', 'Basics?', ()), ('deep', 'concept_brief_overview', 'Deep?', ('basics',)),
                         ('deeper', 'concept_brief_overview', 'Deeper?', ('deep', 'elsewhere')), ('other', 'concept_brief_overview', 'Zed?', ()))
        # a base outside the set (elsewhere) doesn't hold a chapter back
        self.assertEqual(book.teaching_order(found), ['other', 'basics', 'deep', 'deeper'])
        self.assertEqual(book.cycles(found), [])

    def test_a_cycle_goes_last_and_is_reported(self):
        found = chapters(('x', 'concept_brief_overview', 'X?', ('y',)), ('y', 'concept_brief_overview', 'Y?', ('x',)),
                         ('after', 'concept_brief_overview', 'After?', ('x',)), ('self', 'survey', 'Self?', ('self',)),
                         ('free', 'case_study', 'Free?', ()))
        self.assertEqual(book.teaching_order(found), ['self', 'free', 'after', 'x', 'y'])  # self-reference is ignored for order
        self.assertEqual(book.cycles(found), [['self'], ['x', 'y']])
        self.assertEqual(book.cycles(chapters(('a', 'survey', 'A?', ('b',)), ('b', 'survey', 'B?', ()))), [])


class Model(helpers.WikiTestCase):
    git = False

    def test_the_fixture_wiki(self):
        b = book.model(self.root)
        self.assertEqual([(p.tag, p.depth) for p in b.parts[0].walk()], [('root-topic', 0), ('leaf-a', 1)])  # leaf-b has nothing
        self.assertEqual(b.parts[0].description, 'The root topic')
        self.assertEqual(b.order(), ['what-is-alpha'])
        c = b.chapters['what-is-alpha']
        self.assertEqual((c.question, c.template, c.tag, c.sources), ('What is alpha?', 'technical_brief_overview', 'leaf-a', ['alpha-doc']))
        self.assertEqual((b.problems, b.cited_by()), ([], {'alpha-doc': ['what-is-alpha']}))

    def test_order_parts_and_see_also(self):
        helpers.add_narrative(self.root, 'how-is-beta-built', 'How is beta built?', primary=('leaf-b',), built_on=('what-is-beta',),
                              cites=(('beta-doc', 'beta'), ('alpha-doc', 'details'), ('beta-doc', 'other')))
        helpers.add_narrative(self.root, 'what-is-beta', 'What is beta?', 'comparison', primary=('leaf-b',), supporting=('leaf-a',))
        helpers.add_narrative(self.root, 'beta-or-alpha', 'Beta or alpha?', 'concept_brief_overview', primary=('leaf-a', 'leaf-b'))
        helpers.add_narrative(self.root, 'the-whole-topic', 'The whole topic?', 'survey', primary=('root-topic',))
        b = book.model(self.root)
        parts = {p.tag: p for p in b.parts[0].walk()}
        self.assertEqual(list(parts), ['root-topic', 'leaf-a', 'leaf-b'])
        self.assertEqual(parts['root-topic'].chapters, ['the-whole-topic'])
        self.assertEqual(parts['leaf-a'].chapters, ['beta-or-alpha', 'what-is-alpha'])
        self.assertEqual(parts['leaf-a'].see_also, ['what-is-beta'])
        self.assertEqual(parts['leaf-b'].chapters, ['what-is-beta', 'how-is-beta-built'])  # its base first, despite templates
        self.assertEqual(parts['leaf-b'].see_also, ['beta-or-alpha'])  # a second primary tag lists it, too
        self.assertEqual(b.order(), ['the-whole-topic', 'beta-or-alpha', 'what-is-alpha', 'what-is-beta', 'how-is-beta-built'])
        self.assertEqual(b.chapters['how-is-beta-built'].sources, ['beta-doc', 'alpha-doc'])  # first cited first, once
        self.assertEqual(b.cited_by()['alpha-doc'], ['the-whole-topic', 'beta-or-alpha', 'what-is-alpha', 'what-is-beta', 'how-is-beta-built'])
        self.assertEqual(b.cited_by()['beta-doc'], ['how-is-beta-built'])

    def test_cycles_are_problems(self):
        helpers.add_narrative(self.root, 'x', 'X?', built_on=('y',))
        helpers.add_narrative(self.root, 'y', 'Y?', built_on=('x',))
        b = book.model(self.root)
        self.assertEqual(b.problems, [('BOOK_CYCLE', 'x', 'narratives built on each other in a cycle: x, y')])
        self.assertEqual(b.order(), ['what-is-alpha', 'x', 'y'])

    def test_what_is_left_out(self):
        helpers.add_narrative(self.root, 'no-tag', 'No tag?', primary=('gone',))  # wiki-check reports the unknown tag
        helpers.add_narrative(self.root, 'no-file', 'No file?')
        os.remove(os.path.join(self.root, 'sllmwiki/narratives/no-file.md'))
        self.assertEqual(book.model(self.root).order(), ['what-is-alpha'])

    def test_a_tag_cycle_does_not_loop(self):
        tags = helpers.read(self.root, 'sllmwiki/tags/tags.yaml')
        helpers.write(self.root, 'sllmwiki/tags/tags.yaml', tags + '''
loop-x:
  description: Loop x
  parent: loop-y

loop-y:
  description: Loop y
  parent: loop-x
''')
        helpers.add_narrative(self.root, 'in-a-loop', 'In a loop?', primary=('loop-y',))
        b = book.model(self.root)
        self.assertEqual([[p.tag for p in part.walk()] for part in b.parts], [['root-topic', 'leaf-a'], ['loop-x', 'loop-y']])
        self.assertEqual(b.order(), ['what-is-alpha', 'in-a-loop'])

    def test_a_question_falls_back_to_the_slug(self):
        helpers.add_narrative(self.root, 'untitled', 'Untitled?')
        helpers.write(self.root, 'sllmwiki/narratives/untitled.md', 'No title here.\n')
        self.assertEqual(book.model(self.root).chapters['untitled'].question, 'untitled')



LINKS = """
See [the background](#3-background), [nothing](#nope), [alpha](what-is-alpha.md),
[how alpha works](what-is-alpha.md#5-how-does-it-work), [alpha's metadata](what-is-alpha.md#9-metadata),
[a ghost](ghost.md), [beta's doc](../sources/beta-doc.md), [no such source](../sources/nope.md#x),
[leaf a](../tags/leaf-a.md), [a tag with nothing](../tags/leaf-b.md), [the index](../../SLLMWIKI_INDICES.md),
[the README](../../README.md), [the web](https://example.com/x.md), `[code](what-is-alpha.md)`.

![A flow](figures/how-is-beta-built/flow.svg) ![Gone](figures/how-is-beta-built/gone.png)

```text
[fenced](what-is-alpha.md)
```
"""

ZH = """# 什么是环？

## 1. 摘要

见[第三节](#3-环如何工作)和[同一节](#3-%E7%8E%AF%E5%A6%82%E4%BD%95%E5%B7%A5%E4%BD%9C)。

## 2. 重复

## 3. 环如何工作

键落在顺时针方向的第一个节点上。

## 4. 元数据

- **Version:** 2.0
- **Language:** zh-Hans
- **Last modified:** 2026-10-20
"""


class Rewrite(helpers.WikiTestCase):
    git = False

    def test_the_fixture_chapter(self):
        b = book.model(self.root)
        r = book.rewrite(self.root, b, 'what-is-alpha')
        lines = r.text.split('\n')
        self.assertEqual(lines[:4], ['(ch--what-is-alpha)=', '# What is alpha?', '', '*Version 1.0 · Last modified 2026-10-02*'])
        self.assertIn('(what-is-alpha--5-how-does-it-work)=\n## 5. How does it work?', r.text)
        self.assertIn('twice as long [\\[1\\]](#src--alpha-doc).', r.text)  # a citation goes to Appendix A
        self.assertIn('1. [alpha-doc: details](#src--alpha-doc)', r.text)
        self.assertNotIn('Metadata', r.text)
        self.assertNotIn('../', r.text)
        self.assertEqual((r.problems, r.sources, r.figures), ([], ['alpha-doc'], []))

    def test_every_kind_of_link(self):
        helpers.write(self.root, 'sllmwiki/narratives/figures/how-is-beta-built/flow.svg', '<svg/>')
        helpers.add_narrative(self.root, 'how-is-beta-built', 'How is beta built?', primary=('leaf-a',))
        text = helpers.read(self.root, 'sllmwiki/narratives/how-is-beta-built.md').replace('## 6. Design', LINKS + '\n## 6. Design')
        helpers.write(self.root, 'sllmwiki/narratives/how-is-beta-built.md', text)
        b = book.model(self.root)
        r = book.rewrite(self.root, b, 'how-is-beta-built')
        for kept in ['[the background](#how-is-beta-built--3-background)', ' nothing,', '[alpha](#ch--what-is-alpha)',
                     '[how alpha works](#what-is-alpha--5-how-does-it-work)', " alpha's metadata,", '\na ghost,',
                     "[beta's doc](#src--beta-doc)", ' no such source,', '[leaf a](#part--leaf-a)', ' a tag with nothing,',
                     '[the index](#book--contents)', '\nthe README,', '[the web](https://example.com/x.md)',
                     '`[code](what-is-alpha.md)`', '[fenced](what-is-alpha.md)', '![A flow](figures/how-is-beta-built/flow.svg)']:
            self.assertIn(kept, r.text)
        where = [p[1].split(':')[0] for p in r.problems]
        self.assertEqual(set(where), {'sllmwiki/narratives/how-is-beta-built.md'})
        self.assertEqual([(p[0], p[2].split(':')[0]) for p in r.problems], [
            ('BOOK_LINK', '#nope'), ('BOOK_LINK', 'what-is-alpha.md#9-metadata'), ('BOOK_LINK', 'ghost.md'),
            ('BOOK_LINK', '../sources/nope.md#x'), ('BOOK_FIGURE', 'figures/how-is-beta-built/gone.png')])
        self.assertEqual(r.sources, ['alpha-doc', 'beta-doc'])
        self.assertEqual(r.figures, ['figures/how-is-beta-built/flow.svg'])

    def test_a_chinese_chapter(self):
        helpers.add_narrative(self.root, 'zh-ring', 'x')
        helpers.write(self.root, 'sllmwiki/narratives/zh-ring.md', ZH)
        b = book.model(self.root)
        r = book.rewrite(self.root, b, 'zh-ring')
        label = 'zh-ring--3-u73afu5982u4f55u5de5u4f5c'  # docutils drops non-ASCII from ids
        self.assertIn(f'({label})=\n## 3. 环如何工作', r.text)
        self.assertIn(f'[第三节](#{label})和[同一节](#{label})', r.text)
        pack = language.pack('zh-Hans')
        self.assertIn(f'*{pack.t("Version")} 2.0 · {pack.t("Last modified")} 2026-10-20*', r.text)
        self.assertEqual(r.problems, [])

    def test_no_metadata_no_version_line(self):
        helpers.add_narrative(self.root, 'bare', 'Bare?')
        helpers.write(self.root, 'sllmwiki/narratives/bare.md', '# Bare?\n\n## 1. Abstract\n\nText.\n')
        r = book.rewrite(self.root, book.model(self.root), 'bare')
        self.assertEqual(r.text, '(ch--bare)=\n# Bare?\n\n(bare--1-abstract)=\n## 1. Abstract\n\nText.\n')

    def test_labels(self):
        self.assertEqual((book.chapter_label('a'), book.section_label('a', '1-x'), book.source_label('s'), book.part_label('t')),
                         ('ch--a', 'a--1-x', 'src--s', 'part--t'))
        self.assertEqual(book.section_label('a', '1-é'), 'a--1-ue9')


if __name__ == '__main__':
    unittest.main()
