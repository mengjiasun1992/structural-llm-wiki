"""Tests for lib/book.py: the book's parts, chapter order and cited sources (docs/book_design.md §5)."""

import json
import os
import shutil
import tempfile
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
[leaf a](../tags/leaf-a.md), [a tag with nothing](../tags/leaf-b.md), [the index](../.SLLMWIKI_INDICES.md),
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
        self.assertEqual(lines[:4], ['(ch--what-is-alpha)=', '# What is alpha?', '', '*Version 1.0 · 2026-10-02 · 1 min read*'])
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
        self.assertIn(f'*{pack.t("Version")} 2.0 · 2026-10-20 · 阅读约 1 分钟*', r.text)
        self.assertEqual(r.problems, [])

    def test_front_matter_is_left_out(self):
        text = helpers.read(self.root, 'sllmwiki/narratives/what-is-alpha.md')
        helpers.write(self.root, 'sllmwiki/narratives/what-is-alpha.md',
                      '---\nsllmwiki: generated\ntags:\n  - root-topic/leaf-a\n---\n\n' + text.replace('## 6. Design', 'See [x](#nope).\n\n## 6. Design'))
        r = book.rewrite(self.root, book.model(self.root), 'what-is-alpha')
        self.assertTrue(r.text.startswith('(ch--what-is-alpha)=\n# What is alpha?\n'), r.text[:80])
        self.assertNotIn('sllmwiki: generated', r.text)
        line = [i for i, l in enumerate(helpers.read(self.root, 'sllmwiki/narratives/what-is-alpha.md').split('\n'), 1) if '#nope' in l][0]
        self.assertEqual(r.problems[0][1], f'sllmwiki/narratives/what-is-alpha.md:{line}')  # lines still count the front matter

    def test_no_metadata_only_the_reading_time(self):
        helpers.add_narrative(self.root, 'bare', 'Bare?')
        helpers.write(self.root, 'sllmwiki/narratives/bare.md', '# Bare?\n\n## 1. Abstract\n\nText.\n')
        r = book.rewrite(self.root, book.model(self.root), 'bare')
        self.assertEqual(r.text, '(ch--bare)=\n# Bare?\n\n*1 min read*\n\n(bare--1-abstract)=\n## 1. Abstract\n\nText.\n')

    def test_labels(self):
        self.assertEqual((book.chapter_label('a'), book.section_label('a', '1-x'), book.source_label('s'), book.part_label('t')),
                         ('ch--a', 'a--1-x', 'src--s', 'part--t'))
        self.assertEqual(book.section_label('a', '1-é'), 'a--1-ue9')



class Pages(unittest.TestCase):
    def test_a_part_title(self):
        self.assertEqual(book.title('llm-knowledge-bases', 'Patterns that give LLMs access to knowledge'), 'LLM knowledge bases')
        self.assertEqual(book.title('amazon-dynamo', "Amazon's Dynamo key-value store"), 'Amazon Dynamo')
        self.assertEqual(book.title('rag', 'Retrieval. How does a wiki differ from retrieval (RAG)?'), 'RAG')
        self.assertEqual(book.title('data-partitioning', 'Data partitioning. Partitioning by key'), 'Data partitioning')  # a sentence's start says nothing
        self.assertEqual(book.title('ewma', ''), 'Ewma')

    def test_web_urls_and_model_names(self):
        for remote, url in [('git@github.com:o/r.git', 'https://github.com/o/r'), ('git@github-me:o/r', 'https://github.com/o/r'),
                            ('ssh://git@gitlab.com/g/s/r.git', 'https://gitlab.com/g/s/r'), ('https://u:t@github.com/o/r.git/', 'https://github.com/o/r'),
                            ('http://example.com/o/r', 'https://example.com/o/r'), ('/a/local/path', None), ('git@host:noslash', None), ('', None), (None, None)]:
            self.assertEqual(book.web_url(remote), url, remote)
        self.assertEqual(book.model_names(['claude-opus-5-5', 'claude-haiku-5', 'claude-opus-5-5', 'gpt-x']),
                         ['Claude Opus 5.5', 'Claude Haiku 5', 'gpt-x'])

    def test_head(self):
        b = book.Book([], {}, [])
        outer, inner = book.Part('outer-tag', 'Outer', 0, [], [], []), book.Part('inner', 'Inner', 1, [], [], [])
        self.assertEqual(book.head(b, 'w', [outer, inner], language.ENGLISH),
                         '<div class="headnote">\n\n<span class="crumbs">[{w 📖}](#book--cover) › [Outer tag](#part--outer-tag) › '
                         '[Inner](#part--inner)</span> <span class="to-contents">[Contents](#book--contents)</span>\n\n</div>\n\n')
        self.assertIn('<span class="crumbs">[{w 📖}](#book--cover)</span>', book.head(b, 'w', [], language.ENGLISH))

    def test_a_summary(self):
        self.assertEqual(book.summary('# Q\n\n## 1. Abstract\n\nFirst one.\nSame.\n\nSecond.\n\n(q--2-x)=\n## 2. X\n'), 'First one. Same.')
        self.assertEqual(book.summary('# Q\n'), '')

    def test_a_question_with_brackets_keeps_its_link(self):
        b = book.Book([], {'q': book.Chapter('q', 'What is [x]?', 'survey', 't')}, [])
        self.assertEqual(book._link(b, 'q'), '[What is \\[x\\]?](#ch--q)')

    def test_terms(self):
        text = ('# Q\n\n## 2. Terminology\n\n| Term | Definition |\n|---|---|\n| **A** | One `a|b` thing \\| or another. |\n'
                '| **[?]** | A gap. |\n| **B** | Two | cells |\n\n## 3. Next\n\n| X | Y |\n|---|---|\n| **C** | no |\n')
        self.assertEqual(book.terms(text), [('**A**', 'One `a|b` thing \\| or another.'), ('**B**', 'Two | cells')])
        self.assertEqual(book.terms('# Q\n'), [])


class Stage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='sllmwiki-test-')
        self.root = helpers.make_book_wiki(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_staged_book(self):
        helpers.write(self.root, 'sllmwiki/narratives/manifest.yaml', helpers.read(self.root, 'sllmwiki/narratives/manifest.yaml').replace(
            'what-is-alpha:\n  template: technical_brief_overview\n', 'what-is-alpha:\n  template: technical_brief_overview\n'
            '  models:\n    1.0: claude-opus-5-5\n    1.1: some-model\n'))
        st = book.stage(self.root, 'my-wiki', 'v2026.10.24', '2026-10-24', 'abc1234', 'https://github.com/o/my-wiki')
        self.assertEqual(sorted(st.files), ['appendix-glossary.md', 'appendix-questions.md', 'appendix-sources.md',
                                            'chapters/how-does-beta-work.md', 'chapters/what-is-alpha.md', 'chapters/zh-what-is-retry.md',
                                            'index.md', 'parts/leaf-a.md', 'parts/leaf-b.md', 'parts/root-topic.md'])
        self.assertEqual(st.figures, ['figures/how-does-beta-work/cache.svg'])
        index = st.files['index.md']
        self.assertTrue(index.startswith('(book--cover)=\n# {my-wiki 📖}\n\n*Made by [sllmwiki](https://github.com/mengjiasun1992/structural-llm-wiki) '
                                         'and Claude Opus 5.5, some-model, from [my-wiki](https://github.com/o/my-wiki).*\n\n'
                                         '**Version:** v2026.10.24 · **Date:** 2026-10-24 · **Commit:** `abc1234`\n'), index[:400])
        self.assertIn("## About this book\n\nThe narratives in this book are the wiki owner's work.", index)
        self.assertIn('- **[?]**: A gap', index)
        self.assertIn('## Contents\n\n- [Root topic](#part--root-topic)\n  - [Leaf a](#part--leaf-a)\n    - [什么是重试？](#ch--zh-what-is-retry)\n'
                      '    - [What is alpha?](#ch--what-is-alpha)\n  - [Leaf b](#part--leaf-b)\n    - [How does beta work?](#ch--how-does-beta-work)\n'
                      '- [Appendix A: Sources](#book--sources)\n- [Appendix B: Glossary](#book--glossary)\n- [Appendix C: Open questions](#book--questions)\n\n'
                      '```{toctree}\n:hidden:\n\nparts/root-topic\nappendix-sources\nappendix-glossary\nappendix-questions\n```\n', index)
        def head(*crumbs):
            trail = ''.join(f' › [{t}](#part--{tag})' for tag, t in crumbs)
            return (f'<div class="headnote">\n\n<span class="crumbs">[{{my-wiki 📖}}](#book--cover){trail}</span> '
                    '<span class="to-contents">[Contents](#book--contents)</span>\n\n</div>\n\n')
        summary = helpers.ABSTRACT
        def summ(text):
            return f' <span class="summary">— {text}</span>'
        zh = summ('重试就是再次发送失败的请求 [\\[1\\]](#src--alpha-doc)，见[第三节](#zh-what-is-retry--3-u5b83u662fu5982u4f55u5de5u4f5cu7684)。')
        self.assertEqual(st.files['parts/root-topic.md'],
                         f'{head()}(part--root-topic)=\n# Root topic\n\nThe root topic\n\n'
                         f'- [Leaf a](#part--leaf-a){summ("First leaf, about alpha systems")}\n'
                         f'  - [什么是重试？](#ch--zh-what-is-retry) · 1 min{zh}\n'
                         f'  - [What is alpha?](#ch--what-is-alpha) · 1 min{summ(summary)}\n'
                         f'- [Leaf b](#part--leaf-b){summ("Second leaf, about beta caching")}\n'
                         f'  - [How does beta work?](#ch--how-does-beta-work) · 1 min{summ(summary)}\n\n'
                         '```{toctree}\n:hidden:\n\nleaf-a\nleaf-b\n```\n')
        self.assertTrue(st.files['parts/leaf-a.md'].startswith(head(('root-topic', 'Root topic')) + '(part--leaf-a)=\n# Leaf a\n'))
        alpha = st.files['chapters/what-is-alpha.md']
        self.assertTrue(alpha.startswith(head(('root-topic', 'Root topic'), ('leaf-a', 'Leaf a'))
                                         + '(ch--what-is-alpha)=\n# What is alpha?\n\n*Version 1.0 · 2026-10-02 · 1 min read*\n\n'), alpha[:500])
        self.assertTrue(alpha.endswith('\n\n<div class="endmark">\n\n[sllmwiki](https://github.com/mengjiasun1992/structural-llm-wiki)\n\n</div>\n'))
        self.assertTrue(st.files['appendix-glossary.md'].startswith(head() + '(book--glossary)=\n# Appendix B: Glossary\n'))
        self.assertEqual((st.manifest['source'], st.manifest['models']), ('https://github.com/o/my-wiki', ['Claude Opus 5.5', 'some-model']))
        self.assertIn('```{toctree}\n:hidden:\n\n../chapters/zh-what-is-retry\n../chapters/what-is-alpha\n```\n\n'
                      '**See also:** [How does beta work?](#ch--how-does-beta-work)\n', st.files['parts/leaf-a.md'])
        sources = st.files['appendix-sources.md']
        self.assertIn('(src--alpha-doc)=\n## alpha-doc\n\nAlpha systems and how they retry failed requests.\n\n- **License:** CC-BY-4.0\n'
                      '- **Published:** 2026-09-01\n- **Original:** <https://example.com/alpha>\n'
                      '- **Cited by:** [什么是重试？](#ch--zh-what-is-retry), [What is alpha?](#ch--what-is-alpha)\n', sources)
        self.assertIn('(src--beta-doc)=\n## beta-doc\n\nBeta caching keeps hot data close to readers.\n\n- **License:** CC0-1.0\n- **Original:**', sources)
        self.assertNotIn('gamma-link', sources)  # no chapter links to it
        self.assertIn('| **Retry** | Sending a failed request again. ([What is alpha?](#ch--what-is-alpha), '
                      '[How does beta work?](#ch--how-does-beta-work)) |\n', st.files['appendix-glossary.md'])
        self.assertLess(st.files['appendix-glossary.md'].index('**Retry**'), st.files['appendix-glossary.md'].index('**重试**'))
        self.assertEqual([line for line in st.files['appendix-questions.md'].split('\n') if line.startswith('- ')], [
            '- Whether beta keeps a shadow copy is unknown ([How does beta work?](#how-does-beta-work--5-how-does-it-work))',
            '- Weights (Beta): not covered ([How does beta work?](#how-does-beta-work--5-how-does-it-work))'])
        m = st.manifest
        self.assertEqual((m['name'], m['version'], m['date'], m['commit'], m['problems']), ('my-wiki', 'v2026.10.24', '2026-10-24', 'abc1234', []))
        self.assertEqual(m['order'], ['zh-what-is-retry', 'what-is-alpha', 'how-does-beta-work'])  # a concept first
        self.assertEqual(m['parts'], [{'tag': 'root-topic', 'depth': 0, 'chapters': []}, {'tag': 'leaf-a', 'depth': 1, 'chapters': ['zh-what-is-retry', 'what-is-alpha']},
                                      {'tag': 'leaf-b', 'depth': 1, 'chapters': ['how-does-beta-work']}])
        self.assertIn('book--contents', m['anchors'])
        self.assertIn('zh-what-is-retry--3-u5b83u662fu5982u4f55u5de5u4f5cu7684', m['anchors'])
        renders = {(r['kind'], r['source']): r['files'] for r in m['renders']}
        self.assertEqual(renders[('mermaid', 'graph LR\n    A[Request fails] --> B[Wait, then retry]')],
                         ['chapters/how-does-beta-work.md', 'chapters/what-is-alpha.md'])  # one id for the same diagram
        self.assertEqual(renders[('display', 'w_j = \\alpha (1 - \\alpha)^j')], ['chapters/how-does-beta-work.md'])
        self.assertIn(('inline', 't'), renders)
        self.assertEqual(len({r['id'] for r in m['renders']}), len(m['renders']))

    def test_a_question_marked_on_a_heading_and_empty_appendices(self):
        text = helpers.read(self.root, 'sllmwiki/narratives/what-is-alpha.md').replace('## 3. Background', '## 3. Background [?]')
        text = text.replace('## 6. Design', 'Ours [→].\n\n| Odd [?] | x |\n|---|---|\n| y | z |\n\n## 6. Design')
        helpers.write(self.root, 'sllmwiki/narratives/what-is-alpha.md', text)
        st = book.stage(self.root, 'w', 'v', 'd', '')
        # GitHub's anchor keeps the hyphen left by the marker
        self.assertIn('- Background ([What is alpha?](#what-is-alpha--3-background-))', st.files['appendix-questions.md'])
        self.assertIn('- Odd ([What is alpha?](#what-is-alpha--5-how-does-it-work))', st.files['appendix-questions.md'])  # a header cell
        self.assertNotIn('Ours', st.files['appendix-questions.md'])  # reasoning isn't a question
        self.assertIn('**Version:** v · **Date:** d\n', st.files['index.md'])  # no commit, no field
        self.assertIn('# {w 📖}\n\n*Made by [sllmwiki](https://github.com/mengjiasun1992/structural-llm-wiki), from w.*\n', st.files['index.md'])
        root = helpers.make_wiki(tempfile.mkdtemp(dir=self.tmp), git=False)
        helpers.write(root, 'sllmwiki/narratives/what-is-alpha.md', '# What is alpha?\n\nNothing cited.\n')
        st = book.stage(root, 'w', 'v', 'd', 'c')
        self.assertEqual(sorted(st.files), ['chapters/what-is-alpha.md', 'index.md', 'parts/leaf-a.md', 'parts/root-topic.md'])
        self.assertIn(':hidden:\n\nparts/root-topic\n```', st.files['index.md'])

    def book_cmd(self, *argv):
        return helpers.run('book.py', list(argv), cwd=self.root)

    def test_the_command(self):
        out = os.path.join(self.tmp, 'out')
        r = helpers.run('book.py', ['stage', out, '--version', 'v1', '--date', '2026-10-24'], cwd=self.root)
        self.assertEqual(r.code, 0, r.err)
        self.assertIn('3 chapters, 4 diagrams and formulas, 0 problems', r.out)
        self.assertTrue(os.path.isfile(os.path.join(out, 'chapters/figures/how-does-beta-work/cache.svg')))
        data = json.loads(helpers.read(out, 'book.json'))
        commit = helpers.git(self.root, 'rev-parse', '--short', 'HEAD').stdout.strip()
        self.assertEqual((data['name'], data['version'], data['commit']), (os.path.basename(self.root), 'v1', commit))
        self.assertIsNone(data['source'])  # no origin remote
        out2 = os.path.join(self.tmp, 'out2')
        helpers.git(self.root, 'remote', 'add', 'origin', 'git@github.com:o/wiki.git')
        self.book_cmd('stage', out2)
        self.assertEqual(json.loads(helpers.read(out2, 'book.json'))['source'], 'https://github.com/o/wiki')
        out3 = os.path.join(self.tmp, 'out3')
        self.book_cmd('stage', out3, '--source', '')
        self.assertIsNone(json.loads(helpers.read(out3, 'book.json'))['source'])  # asked for none
        self.assertTrue(helpers.read(out, 'index.md').startswith('(book--cover)='))
        r = helpers.run('book.py', ['stage', out], cwd=self.root)
        self.assertEqual(r.code, 2)
        self.assertIn('must be an empty folder', r.err)

    def test_problems_fail_the_command_and_the_book_is_still_written(self):
        helpers.add_narrative(self.root, 'x', 'X?', built_on=('y',))
        helpers.add_narrative(self.root, 'y', 'Y?', built_on=('x',))
        helpers.write(self.root, 'sllmwiki/narratives/y.md', helpers.read(self.root, 'sllmwiki/narratives/y.md').replace('## 6.', 'See [nothing](#nope).\n\n## 6.'))
        out = os.path.join(self.tmp, 'out')
        os.makedirs(out)  # an empty folder is fine
        r = helpers.run('book.py', ['stage', out, '--commit', '', '--json', '--root', self.root])
        self.assertEqual(r.code, 1)
        data = json.loads(r.out)
        self.assertEqual([p['code'] for p in data['problems']], ['BOOK_CYCLE', 'BOOK_LINK'])
        self.assertEqual(data['chapters'], 5)
        self.assertTrue(os.path.isfile(os.path.join(out, 'chapters/y.md')))
        r = helpers.run('book.py', ['stage', os.path.join(self.tmp, 'out2'), '--root', self.root])
        self.assertIn('BOOK_LINK sllmwiki/narratives/y.md:', r.out)
        self.assertIn('2 problems', r.out)


if __name__ == '__main__':
    unittest.main()
