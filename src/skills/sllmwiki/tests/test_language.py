"""Tests for lib/language.py: language packs, and the narrative checks and scripts that follow a narrative's language."""

import glob
import os
import re
import unittest

import helpers
from lib import config, figures, language, markers, metadata, narrativecheck, numbering, search, templates

NARRATIVE = 'sllmwiki/narratives/what-is-alpha.md'
ZH = {
    'Abstract': '摘要', 'Terminology': '术语', 'Background': '背景', 'The core idea': '核心思想', 'How does it work?': '它是如何工作的？',
    'Design decisions and trade-offs': '设计决策与权衡', 'Limitations and failure modes': '局限与失效模式', 'Variants': '变体',
    'References': '参考文献', 'Sources read': '已读来源', 'Citations': '引用', 'Metadata': '元数据', 'Appendix': '附录',
    '(optional)': '（可选）', 'Term': '术语', 'Definition': '定义', 'Figure': '图',
    markers.MARKERS['[→]']: '我们自己的推理：没有引用来源说明的结论、比较或例子。',
}
PACK = '# 简体中文\n\n| English | Translation |\n|---|---|\n' + ''.join(f'| {k} | {v} |\n' for k, v in ZH.items())


def chinese(text):
    """helpers.narrative_text() with its headings, labels and caption in Chinese, and its language named."""
    for english in ('Abstract', 'Terminology', 'Background', 'The core idea', 'How does it work?', 'Design decisions and trade-offs',
                    'Limitations and failure modes', 'References', 'Sources read', 'Citations', 'Metadata'):
        text = re.sub(r'^(#{2,3} [0-9.]+ )' + re.escape(english) + r'$', lambda m, english=english: m.group(1) + ZH[english], text, flags=re.M)
    text = text.replace('| Term | Definition |', '| 术语 | 定义 |')
    text = text.replace('*Figure 4-1: A failed request waits, then retries.*', '*图 4-1：失败的请求先等待，再重试。*')
    return text.replace('- **Template:** technical_brief_overview\n', '- **Template:** technical_brief_overview\n- **Language:** zh-Hans\n')


BOOK = ['Contents', 'About this book', 'See also', 'Appendix A: Sources', 'Appendix B: Glossary', 'Appendix C: Open questions',
        'Version', 'Date', 'Commit', 'Last modified', 'License', 'Published', 'Cited by', 'Original',
        'Made by {tool} and {models}, from {source}.', 'Made by {tool}, from {source}.']


class Packs(helpers.WikiTestCase):
    def setUp(self):
        super().setUp()
        self.write('templates/languages/zh-Hans.md', PACK)
        self.assertEqual(language.use(self.root), [])

    def tearDown(self):
        language._loaded.clear()
        super().tearDown()

    def codes(self, text, **settings):
        s = {**config.DEFAULTS, **settings}
        return [(c, n) for _, c, n, _ in narrativecheck.check(self.root, NARRATIVE, text, s, templates.available(self.root)[0])]

    def test_packs_load_and_fall_back(self):
        self.assertEqual(language.pack('zh-Hans').name, '简体中文')
        self.assertEqual(language.pack('zh-hans-CN').tag, 'zh-Hans')  # a region falls back to its language
        self.assertIsNone(language.pack('fr'))
        self.assertEqual(language.pack('en').t('Abstract'), 'Abstract')  # the English pack lists every string, untranslated
        self.assertEqual(language.for_narrative('- **Language:** fr\n'), ('fr', language.ENGLISH))
        self.assertEqual(language.for_narrative('no field', 'zh-Hans')[1].tag, 'zh-Hans')
        self.assertIn('摘要', language.names('Abstract'))

    def test_a_pack_that_does_not_parse(self):
        for text, why in (('| Abstract | 摘要 |\n', 'heading'), ('# 中文\n\n| a | b | c |\n', 'a row is'),
                          ('# 中文\n\n| Abstract | 摘要 |\n| Abstract | 提要 |\n', 'twice')):
            with self.assertRaisesRegex(ValueError, why):
                language.parse('zh', text, 'wiki')
        self.write('templates/languages/zh.md', '| Abstract | 摘要 |\n')
        self.write('templates/languages/chinese.md', '# 中文\n')
        problems = language.use(self.root)
        self.assertTrue(any('zh.md' in p for p in problems) and any('chinese.md' in p for p in problems), problems)
        r = helpers.run('wiki-check.py', ['--json'], cwd=self.root)
        self.assertIn('LANGUAGE_PACK_INVALID', r.out)

    def test_the_english_pack_lists_every_string(self):
        """Copying en.md is how a pack starts, so it names every heading of the bundled templates and every label."""
        strings = language.pack('en').strings
        for f in [templates.SHARED_SKELETON] + glob.glob(os.path.join(templates.BUNDLED, '*', 'template.md')):
            for h in numbering.headings(helpers.read(os.path.dirname(f), os.path.basename(f))):
                title = templates.OPTIONAL.sub('', h.title)
                if h.level >= 2 and '<' not in title:
                    self.assertIn(title, strings, f)
        for label in ['(optional)', 'Term', 'Definition', 'Figure'] + list(markers.MARKERS.values()):
            self.assertIn(label, strings)
        for label in BOOK:  # the book's (docs/book_design.md §5)
            self.assertIn(label, strings)

    def test_the_skeleton_in_a_language(self):
        t = templates.get(self.root, 'technical_brief_overview')
        skel = t.skeleton('zh-Hans')
        self.assertIn('## 1. 摘要', skel)
        self.assertIn('| 术语 | 定义 |', skel)
        self.assertIn('（可选）', skel)
        self.assertRegex(skel, r'## [0-9]+\. 元数据')
        self.assertIn('- **Template:** technical_brief_overview\n- **Language:** zh-Hans', skel)  # Metadata stays English
        self.assertIn('- **Language:** en', t.skeleton())
        self.assertIn('## 1. Abstract', t.skeleton('fr'))  # no pack: English headings
        r = helpers.run('narrative-format.py', ['--skeleton', 'technical_brief_overview', '--language', 'fr'], cwd=self.root)
        self.assertIn('no language pack for fr', r.err)
        r = helpers.run('narrative-format.py', ['--skeleton', 'technical_brief_overview', '--language', 'zh-Hans'], cwd=self.root)
        self.assertEqual(r.code, 0, r)
        self.assertIn('## 1. 摘要', r.out)

    def test_a_narrative_in_its_language_passes(self):
        text = chinese(helpers.narrative_text())
        self.assertEqual(self.codes(text), [])
        self.assertEqual(metadata.read(text)['language'], 'zh-Hans')
        self.assertTrue(metadata.abstract(text))
        mixed = text.replace('## 3. 背景', '## 3. Background')
        self.assertEqual(self.codes(mixed), [('HEADING_LANGUAGE', mixed.split('\n').index('## 3. Background') + 1)])
        english = self.codes(helpers.narrative_text(), language='zh-Hans')  # no Language field: the wiki's language
        self.assertEqual({c for c, _ in english}, {'HEADING_LANGUAGE'})
        self.assertGreater(len(english), 5)
        fr = helpers.narrative_text().replace('- **Template:** technical_brief_overview\n', '- **Template:** technical_brief_overview\n- **Language:** fr\n')
        self.assertEqual(self.codes(fr), [('LANGUAGE_PACK', 1)])

    def test_a_language_with_no_pack_in_config(self):
        self.write('Config.toml', '[structural-llm-wiki-settings]\nlanguage = "fr"\n')
        r = helpers.run('wiki-check.py', ['--json'], cwd=self.root)
        self.assertIn('LANGUAGE_PACK', r.out)
        self.write('Config.toml', '[structural-llm-wiki-settings]\nlanguage = "zh_CN"\n')
        self.assertTrue(any('language tag' in p for p in config.problems(self.root)))

    def test_words_count_cjk_characters(self):
        self.assertEqual(language.words('Retries add load.'), 3)
        self.assertEqual(language.words('一致性哈希'), 3)  # five characters, at 1.6 a word
        self.assertEqual(language.words('一致性哈希，一种 hashing 方法。'), 1 + round(9 / language.CJK_CHARACTERS_PER_WORD))
        self.assertEqual(narrativecheck.words(['| a | b |', '|---|---|', '中文中文']), 2 + 2)

    def test_figures_and_markers_in_a_language(self):
        text = '## 3. 背景\n\n```mermaid\ngraph LR\n  A --> B\n```\n\n*图 3-2：说明。*\n\n见图 3-2。\n'
        self.assertEqual([c for _, c, _, _ in figures.check_captions(text)], ['FIGURE_NUMBER'])
        fixed, n = figures.renumber(text)
        self.assertEqual(n, 1)
        self.assertIn('*图 3-1：说明。*', fixed)
        self.assertIn('见图 3-1。', fixed)
        self.assertEqual(figures.check_captions(fixed), [])
        doc = '# 问题\n\n## 1. 摘要\n\n文字。\n\n## 2. 术语\n\n## 3. 背景\n\n一个结论 [→]。\n'
        out, n = markers.add_rows(doc, language.pack('zh-Hans'))
        self.assertEqual(n, 1)
        self.assertIn('| 术语 | 定义 |', out)
        self.assertIn('| **[→]** | 我们自己的推理', out)
        self.assertEqual([c for _, c, _, _ in markers.check(out)], [])

    def test_search_matches_cjk_text(self):
        self.assertEqual(search.tokens('一致性哈希 ring'), ['ring', '一致', '致性', '性哈', '哈希'])
        self.assertEqual(search.tokens('环'), ['环'])

    def test_finish_narrative_records_the_language(self):
        r = helpers.run('finish-narrative.py', ['what-is-alpha'], cwd=self.root)
        self.assertEqual(r.code, 0, r)
        self.assertIn('- **Language:** en', self.read(NARRATIVE))


class Bundled(helpers.WikiTestCase):
    """The packs the skill ships, with no pack of the wiki's own."""

    def setUp(self):
        super().setUp()
        language.use(self.root)

    def tearDown(self):
        language._loaded.clear()
        super().tearDown()

    def test_every_bundled_pack_translates_every_string(self):
        keys = set(language.pack('en').strings)
        for tag in language.bundled() - {'en'}:
            p = language.pack(tag)
            self.assertEqual({k for k in keys if not p.strings.get(k)}, set(), tag)
            self.assertEqual(set(p.strings) - keys, set(), tag)  # nothing en.md doesn't list
            self.assertTrue(p.writing, f'{tag} has a ## Writing section')

    def test_simplified_chinese(self):
        self.assertIn('zh-Hans', language.bundled())
        r = helpers.run('narrative-format.py', ['--skeleton', 'concept_brief_overview', '--language', 'zh-Hans'], cwd=self.root)
        self.assertEqual(r.code, 0, r)
        self.assertIn('## 1. 摘要', r.out)
        self.assertIn('follow the Writing section of', r.err)
        self.assertNotIn('evaluated', r.err)

    def test_a_wiki_pack_for_a_language_the_skill_does_not_ship(self):
        self.write('templates/languages/fr.md', '# Français\n\n| English | Translation |\n|---|---|\n| Abstract | Résumé |\n')
        r = helpers.run('narrative-format.py', ['--skeleton', 'concept_brief_overview', '--language', 'fr'], cwd=self.root)
        self.assertIn('## 1. Résumé', r.out)
        self.assertIn("hasn't evaluated", r.err)


if __name__ == '__main__':
    unittest.main()
