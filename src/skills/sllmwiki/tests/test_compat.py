"""Tests for lib/compat.py: the markdown GitHub, Obsidian, mdBook and Sphinx render alike.

Every rule is a row in RULES, and the Rules tests run each row through the same
cases ("Markdown compatibility" in AGENTS.md): the line that breaks the rule is
reported with its code, severity and line, the line that follows it isn't; the
same text inside fenced code, a code span, YAML front matter and an indented
code block isn't reported (except where mdBook reads code too); and escape()
fixes what it can, once, and changes nothing else. A rule with no row fails
test_every_rule_has_a_row.

Renderers, as each row's `verified` names them: GH = github.com through the
contents API (application/vnd.github.html); OB = Obsidian; MD = mdBook 0.5.4;
MY = Sphinx 9.1 with MyST-Parser 5.1. Checked 2026-10-20, and the code cases
(indented code, % lines in paragraphs and lists) 2026-10-21.
"""

import os
import re
import shutil
import tempfile
import unittest
from collections import namedtuple

import helpers
from lib import compat
from lib.compat import check, check_links, escape, fix

Rule = namedtuple('Rule', 'code severity bad good escaped verified in_code inline bad_line')
Rule.__new__.__defaults__ = (None, '', False, True, 0)  # escaped, verified, in_code, inline, bad_line


def rule(code, severity, bad, good, **kw):
    return Rule(code, severity, bad, good, **kw)


RULES = [
    # Obsidian-only syntax, which GitHub, mdBook and MyST show as plain text
    rule('WIKILINK', 'error', 'See [[note]] here.', 'See [note](note.md) here.', verified='GH OB'),
    rule('WIKILINK', 'error', 'See [[note#Part|alias]].', 'See [alias](note.md#part).', verified='GH OB'),
    rule('EMBED', 'error', 'Look at ![[diagram.png]].', 'Look at ![diagram](diagram.png).', verified='GH OB'),
    rule('HIGHLIGHT', 'error', 'A ==key== idea.', 'If a == b, keep **key**.', verified='GH OB'),
    rule('OBSIDIAN_COMMENT', 'error', 'Text %%hidden%% here.', 'Text <!-- hidden --> here, 10% or 20%.', verified='GH OB'),
    rule('CALLOUT', 'error', '> [!info]', '> [!NOTE]', verified='GH OB', inline=False),
    rule('CALLOUT', 'error', '> [!NOTE] Title', '> [!WARNING]', verified='GH OB', inline=False),
    rule('CALLOUT', 'error', '> [!TIP]-', '> [!TIP]', verified='GH OB', inline=False),
    rule('INLINE_TAG', 'warning', 'A #tag here.', 'C# and issue no. 5.', verified='OB'),
    rule('BLOCK_ID', 'warning', 'A paragraph ^block-1', 'Two to the 2^10.', verified='GH OB'),
    rule('LINE_JOINED', 'warning', '**Q: Why?**\nA: Because.', '**Q: Why?**\n\nA: Because.', verified='GH', inline=False),
    # $$ math that GitHub's markdown changes first
    rule('DOLLAR_MATH', 'error', '$$\na\\,b\n$$', '$$\na_1 * b_2\n$$', verified='GH', inline=False),
    rule('DOLLAR_MATH', 'error', '$$ x^{*} $$', '$$ \\alpha_{t+1} $$', verified='GH', inline=False),
    # what the book renderers read differently
    rule('MDBOOK_DIRECTIVE', 'error', 'See {{#include a.md}}.', 'See \\{{#include a.md}}.', verified='MD', in_code=True),
    rule('MYST_SYNTAX', 'warning', '(label)=', '(label) is fine', verified='GH MY', inline=False),
    rule('MYST_SYNTAX', 'warning', '+++', '++ a', verified='GH MY', inline=False),
    rule('MYST_SYNTAX', 'warning', 'Use {ref}`x` here.', 'Use `{x}` or `a{b}` here.', verified='GH MY', inline=False),
    rule('MYST_SYNTAX', 'warning', '```{note}\nx\n```', '```text\nx\n```', verified='GH MD MY', inline=False),
    rule('HEADING_LEVEL', 'warning', '# T\n\n#### Skipped', '# T\n\n## A', verified='MY', inline=False, bad_line=2),
    rule('HEADING_LEVEL', 'warning', '# T\n\n# Second', '# T\n\n## Second', verified='MY', inline=False, bad_line=2),
    rule('LINE_COMMENT', 'error', '% of users agree', '10% of users agree', escaped='\\% of users agree', verified='MY'),
    rule('LINE_COMMENT', 'error', '- % more', '- 5% more', escaped='- \\% more', verified='MY'),
    rule('LINE_COMMENT', 'error', '> % quoted', '> 5% quoted', escaped='> \\% quoted', verified='MY'),
    rule('HEADING_ATTRS', 'error', '## Sets {a, b}', '## Sets of a and b', escaped='## Sets {a, b\\}', verified='MD', inline=False),
    rule('BARE_URL', 'warning', 'See https://example.com/x.', 'See <https://example.com/x>.', escaped='See <https://example.com/x>.', verified='GH OB MD MY'),
    rule('BARE_URL', 'warning', 'See https://e.com/x_(y).', 'See [x](https://e.com/x_(y)).', escaped='See <https://e.com/x_(y)>.', verified='GH MD MY'),
    rule('EMOJI_SHORTCODE', 'warning', 'Nice :smile: work.', 'At 10:30:00 sharp.', verified='GH MD MY'),
    rule('DOLLAR_SIGN', 'warning', 'Costs $5 a month.', 'Math $x$ and $2$ stay.', escaped='Costs \\$5 a month.', verified='OB MY'),
    rule('DOLLAR_SIGN', 'warning', 'Costs $1,000.', 'Costs USD 1,000.', escaped='Costs \\$1,000.', verified='OB MY'),
    rule('TILDE_STRIKE', 'warning', 'About ~approx~ here.', 'From ~5 ms to ~10 ms, ~~two~~ too.', escaped='About \\~approx~ here.', verified='GH OB MD MY'),
]

INTRO = 'Intro.\n\n'  # so a finding's line number is checked, not just its presence


def found(text, code):
    return [(sev, n) for sev, c, n, _ in check(text) if c == code]


class Rules(unittest.TestCase):
    def each(self):
        for r in RULES:
            with self.subTest(code=r.code, bad=r.bad):
                yield r

    def test_bad_is_reported(self):
        for r in self.each():
            self.assertIn((r.severity, 3 + r.bad_line), found(INTRO + r.bad, r.code))

    def test_good_is_not(self):
        for r in self.each():
            self.assertEqual(found(INTRO + r.good, r.code), [])

    def test_fenced_code(self):
        for r in self.each():
            for fence in ('````', '~~~'):
                self.assertEqual(bool(found(f'{fence}text\n{r.bad}\n{fence}\n', r.code)), r.in_code, fence)

    def test_code_span(self):
        for r in self.each():
            if r.inline:
                self.assertEqual(bool(found(f'Code `{r.bad}` here.', r.code)), r.in_code)

    def test_front_matter(self):
        for r in self.each():
            self.assertEqual(bool(found(f'---\n{r.bad}\n---\n# T\n', r.code)), r.in_code)

    def test_indented_code(self):
        for r in self.each():
            indented = '\n'.join('    ' + line for line in r.bad.split('\n'))
            self.assertEqual(bool(found(INTRO + indented + '\n', r.code)), r.in_code)

    def test_escape(self):
        for r in self.each():
            text, n = escape(r.bad)
            if r.escaped is None:
                self.assertEqual((text, n), (r.bad, 0))  # escape() changes nothing it can't fix
                continue
            self.assertEqual(text, r.escaped)
            self.assertGreaterEqual(n, 1)
            self.assertEqual(found(text, r.code), [])  # the escaped text is no longer reported
            self.assertEqual(escape(text), (text, 0))  # a second run changes nothing
            self.assertEqual(escape(r.good), (r.good, 0))

    def test_every_row_names_its_renderers(self):
        for r in self.each():
            self.assertTrue(set(r.verified.split()) <= {'GH', 'OB', 'MD', 'MY'} and r.verified)

    def test_every_rule_has_a_row(self):
        with open(compat.__file__, encoding='utf-8') as f:
            source = f.read()
        codes = set(re.findall(r"'(?:error|warning)', '([A-Z_]+)'", source))
        links = {'LINK_SPACES', 'LINK_PATH', 'LINK_FOLDER'}  # check_links, tested in Links
        self.assertEqual(codes - links, {r.code for r in RULES})


class CodeIsNeverChecked(unittest.TestCase):
    """The code cases the table can't express."""

    def test_indented_code_needs_a_blank_line(self):
        self.assertEqual(found('A paragraph\n\n    % code\n', 'LINE_COMMENT'), [])
        # MY: four spaces into a paragraph is its text, not a comment; up to three, a comment that splits it
        self.assertEqual(found('A paragraph\n    % continues it\nend.\n', 'LINE_COMMENT'), [])
        self.assertEqual(escape('A paragraph\n    % continues it\n'), ('A paragraph\n    % continues it\n', 0))
        self.assertEqual(found('A paragraph\n  % two spaces\nend.\n\n   % three\n', 'LINE_COMMENT'), [('error', 2), ('error', 5)])

    def test_indented_code_runs_across_blank_lines(self):
        text = 'Intro.\n\n    % one\n\n    % two\n\nAfter.\n% three\n'
        self.assertEqual(found(text, 'LINE_COMMENT'), [('error', 8)])

    def test_a_list_continues_instead(self):
        # GH, MD and MY: an indented line after a blank line inside a list continues the item; MyST drops a % line there
        text = '- item\n\n    % in the item\n\nBack at the margin.\n\n    % code again\n'
        self.assertEqual(found(text, 'LINE_COMMENT'), [('error', 3)])
        self.assertEqual(escape(text), (text.replace('    % in the item', '    \\% in the item'), 1))
        self.assertEqual(found('1. item\n\n    % in the item\n', 'LINE_COMMENT'), [('error', 3)])
        self.assertEqual(found('- item\n  % lazy in the item\n', 'LINE_COMMENT'), [('error', 2)])

    def test_a_tab_indents_code(self):
        self.assertEqual(found('Intro.\n\n\t% code\n', 'LINE_COMMENT'), [])

    def test_unclosed_front_matter_is_prose(self):
        self.assertEqual(found('---\n% not front matter\n', 'LINE_COMMENT'), [('error', 2)])

    def test_math_is_not_prose(self):
        self.assertEqual(check('$$\na ==b== c\n$$\n'), [])
        self.assertEqual(escape('$$\n% x\n$$\n'), ('$$\n% x\n$$\n', 0))

    def test_dollar_math_ignores_indented_code(self):
        self.assertEqual(found('Intro.\n\n    $$\n    a\\,b\n    $$\n', 'DOLLAR_MATH'), [])


class Details(unittest.TestCase):
    """What a row can't show: messages, several findings on a line, and boundaries."""

    def test_messages_name_the_fix(self):
        msgs = {c: m for _, c, _, m in check('% x\n\nSee https://a.com and $5.\n\n## H {x}\n\n$$ x^{*} $$\n')}
        self.assertIn('write \\%', msgs['LINE_COMMENT'])
        self.assertIn('<https://a.com>', msgs['BARE_URL'])
        self.assertIn('\\}', msgs['HEADING_ATTRS'])
        self.assertIn('\\ast for *', msgs['DOLLAR_MATH'])

    def test_heading_levels(self):
        self.assertEqual(found('# T\n\n## A\n\n### B\n\n## C\n\n#### D\n', 'HEADING_LEVEL'), [('warning', 9)])  # only a skip going down
        self.assertEqual(found('## A\n\n### B\n', 'HEADING_LEVEL'), [])

    def test_line_joined_only_before_prose(self):
        for fine in ('**Steps**\n- one\n', '**Steps**\n1. one\n', '**Table**\n| a |\n', '**Q:** inline. A: same line.\n', '**Note**\n```text\nx\n```\n'):
            self.assertEqual(found(fine, 'LINE_JOINED'), [], fine)
        self.assertEqual(found('**Goal:**\nKeep it.\n', 'LINE_JOINED'), [('warning', 1)])

    def test_urls_inside_links_and_autolinks(self):
        text = '<https://ok.com> [https://l.com](https://l.com) [x](https://y.com) `https://code` www.example.com.'
        self.assertEqual([m for _, c, _, m in check(text) if c == 'BARE_URL'], [
            '"www.example.com": GitHub and Obsidian link a bare URL, mdBook and Sphinx show it as text; write <www.example.com> or [text](url) (narrative-format --fix-style)'])

    def test_escape_counts_every_fix(self):
        text = '% a\n## H {x}\nSee https://a.com, $5 and ~b~.\n'
        self.assertEqual(escape(text), ('\\% a\n## H {x\\}\nSee <https://a.com>, \\$5 and \\~b~.\n', 5))

    def test_a_heading_starting_with_percent_is_not_a_comment(self):
        self.assertEqual(found('# % of users\n', 'LINE_COMMENT'), [])


class Fix(unittest.TestCase):
    """fix(): older citations and math fences rewritten to the forms both render alike."""

    def test_citations(self):
        text = 'Claim. [[1]](../ingested/a.md#x) and [[12]](b.md), code `[[3]](c.md)` stays, [\\[4\\]](d.md) is new.'
        self.assertEqual(fix(text), ('Claim. [\\[1\\]](../ingested/a.md#x) and [\\[12\\]](b.md), code `[[3]](c.md)` stays, [\\[4\\]](d.md) is new.', 2, 0))
        self.assertEqual(fix('[[note]] and [[1]] alone'), ('[[note]] and [[1]] alone', 0, 0))  # not citations

    def test_code_keeps_older_citations(self):
        for text in ('---\nx: [[1]](a)\n---\n', 'Intro.\n\n    [[1]](a)\n', '$$\n[[1]](a)\n$$\n'):
            self.assertEqual(fix(text), (text, 0, 0), text)

    def test_math_and_fences(self):
        text = ('a [[1]](x)\n\n```math\nx_{t+1} = [[2]](not a citation)\n```\n\n  ```text\n  [[3]](y)\n  ```\n\n````math\ny\n````\n'
                '\n~~~\n```\n[[4]](z)\n~~~\n')
        fixed, cites, maths = fix(text)
        self.assertEqual((cites, maths), (1, 2))
        self.assertEqual(fixed, ('a [\\[1\\]](x)\n\n$$\nx_{t+1} = [[2]](not a citation)\n$$\n\n  ```text\n  [[3]](y)\n  ```\n\n$$\ny\n$$\n'
                                 '\n~~~\n```\n[[4]](z)\n~~~\n'))  # inside other fences: unchanged
        self.assertEqual(fix(fixed), (fixed, 0, 0))  # running it again changes nothing

    def test_math_github_would_change_stays_fenced(self):
        # what github.com changes inside $$ (2026-10-20): a backslash before punctuation, a * next to a character
        for formula in ('a \\\\ b', 'a\\,b', '\\{x\\}', '\\_x', 'x^{*} y^{*}', 'a*b'):
            text = f'```math\n{formula}\n```\n'
            self.assertEqual(fix(text), (text, 0, 0), formula)
        for formula in ('\\alpha_{t+1}', 'a &= b', 'a_1 * b_2', '\\text{a_b_c}', '\\left( x \\right)'):  # unchanged by github.com
            self.assertEqual(fix(f'```math\n{formula}\n```\n'), (f'$$\n{formula}\n$$\n', 0, 1), formula)
        self.assertEqual(fix('```math\nx\n'), ('```math\nx\n', 0, 0))  # never closed: left alone


class Links(unittest.TestCase):
    """check_links(): links GitHub, Obsidian and the books resolve differently."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='compat-links-')
        helpers.write(self.root, 'notes/a.md', '# A\n')
        helpers.write(self.root, 'notes/My Note.md', '# M\n')
        helpers.write(self.root, 'other/deep/b.md', '# B\n')
        self.dir = os.path.join(self.root, 'notes')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def codes(self, text, resolve=True):
        return [(c, n) for _, c, n, _ in check_links(text, self.dir, self.root, resolve)]

    def test_links_that_resolve_everywhere(self):
        text = ('[a](a.md) [a](./a.md#a) [m](My%20Note.md) [b](../other/deep/b.md "title") [web](https://x.com) '
                '[anchor](#a) [mail](mailto:x@y.z) [p](<a.md>) [](  )\n```text\n[x](missing.md)\n```\n')
        self.assertEqual(self.codes(text), [])

    def test_spaces(self):
        findings = check_links('[m](My Note.md)\n', self.dir, self.root)
        self.assertEqual([(c, n) for _, c, n, _ in findings], [('LINK_SPACES', 1)])
        self.assertIn('My%20Note.md', findings[0][3])
        self.assertEqual(self.codes('[m](My Note.md)\n', resolve=False), [('LINK_SPACES', 1)])

    def test_paths_obsidian_resolves_and_github_doesnt(self):
        findings = check_links('[b](b.md)\n[b](/other/deep/b.md)\n[r](other/deep/b.md)\n[x](nowhere.md)\n', self.dir, self.root)
        self.assertEqual([(c, n) for _, c, n, _ in findings], [('LINK_PATH', 1), ('LINK_PATH', 3), ('LINK_PATH', 4)])
        self.assertIn('write ../other/deep/b.md', findings[0][3])  # found by name
        self.assertIn('write ../other/deep/b.md', findings[1][3])  # found from the vault root
        self.assertIn("doesn't resolve", findings[2][3])

    def test_folders(self):
        self.assertEqual(self.codes('[o](../other/deep)\n'), [('LINK_FOLDER', 1)])

    def test_placeholders_and_no_resolve(self):
        self.assertEqual(self.codes('[t](<slug>.md) [t]({{x}}.md) [t](…)\n'), [])
        self.assertEqual(self.codes('[x](nowhere.md)\n', resolve=False), [])


if __name__ == '__main__':
    unittest.main()
