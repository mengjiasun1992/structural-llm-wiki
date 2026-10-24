"""Tests for lib/book.py: the book's parts, chapter order and cited sources (docs/book_design.md §5)."""

import os
import unittest

import helpers
from lib import book
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


if __name__ == '__main__':
    unittest.main()
