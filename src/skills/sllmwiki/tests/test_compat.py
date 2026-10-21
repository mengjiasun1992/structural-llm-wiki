"""Tests for lib/compat.py: markdown GitHub, Obsidian, mdBook and Sphinx render alike.

Every rule is a row in RULES, and Rules runs each row through the cases
AGENTS.md ("Markdown compatibility") asks for: the line that breaks the rule is
reported with its code, severity and line, and its good form isn't; the same
text inside fenced code, a code span, front matter and indented code isn't
reported (only mdBook directives are, since mdBook reads code too); escape()
fixes what it can, once, the result is no longer reported, and it changes
nothing it can't fix. A rule with no row fails test_every_rule_has_a_row.

`verified` names where each behavior was rendered: GH = github.com through the
contents API (application/vnd.github.html); OB = Obsidian; MD = mdBook 0.5.4;
MY = Sphinx 9.1 with MyST-Parser 5.1. Rendered 2026-10-20; indented code and
% lines in paragraphs and lists on 2026-10-21.
"""

import os
import re
import shutil
import tempfile
import unittest

import helpers
from lib import compat
from lib.compat import check, check_links, escape


class Rule:
    def __init__(self, code, severity, bad, good, verified, fixed=None, in_code=False, inline=True, line=0):
        self.code, self.severity, self.bad, self.good, self.verified = code, severity, bad, good, verified
        self.fixed, self.in_code, self.inline, self.line = fixed, in_code, inline, line


RULES = [
    # Obsidian-only syntax: plain text on GitHub and in the books
    Rule('WIKILINK', 'error', 'See [[note]] here.', 'See [note](note.md) here.', 'GH OB'),
    Rule('WIKILINK', 'error', 'See [[note#Part|alias]].', 'See [alias](note.md#part).', 'GH OB'),
    Rule('EMBED', 'error', 'Look at ![[diagram.png]].', 'Look at ![diagram](diagram.png).', 'GH OB'),
    Rule('CITATION_BRACKETS', 'error', 'Claim. [[3]](../sources/a.md#x)', 'Claim. [\\[3\\]](../sources/a.md#x)', 'GH OB',
         fixed='Claim. [\\[3\\]](../sources/a.md#x)'),
    Rule('HIGHLIGHT', 'error', 'A ==key== idea.', 'If a == b, keep **key**.', 'GH OB'),
    Rule('OBSIDIAN_COMMENT', 'error', 'Text %%hidden%% here.', 'Text <!-- hidden --> here, 10% or 20%.', 'GH OB'),
    Rule('CALLOUT', 'error', '> [!info]', '> [!NOTE]', 'GH OB', inline=False),
    Rule('CALLOUT', 'error', '> [!NOTE] A title', '> [!WARNING]', 'GH OB', inline=False),
    Rule('CALLOUT', 'error', '> [!TIP]-', '> [!TIP]', 'GH OB', inline=False),
    Rule('INLINE_TAG', 'warning', 'A #tag here.', 'C# and issue no. 5, #5.', 'OB'),
    Rule('BLOCK_ID', 'warning', 'A paragraph ^block-1', 'Two to the 2^10.', 'GH OB'),
    Rule('LINE_JOINED', 'warning', '**Q: Why?**\nA: Because.', '**Q: Why?**\n\nA: Because.', 'GH', inline=False),
    # $$ math GitHub's markdown changes first, and ```math Obsidian shows as code
    Rule('DOLLAR_MATH', 'error', '$$\na\\,b\n$$', '$$\na_1 * b_2\n$$', 'GH', inline=False),
    Rule('DOLLAR_MATH', 'error', '$$ x^{*} $$', '$$ \\alpha_{t+1} $$', 'GH', inline=False),
    Rule('MATH_FENCE', 'warning', '```math\nx_{t+1} = a_t\n```', '```math\na \\\\ b\n```', 'GH OB', fixed='$$\nx_{t+1} = a_t\n$$',
         inline=False),
    # what the book renderers read as their own syntax
    Rule('MDBOOK_DIRECTIVE', 'error', 'See {{#include a.md}}.', 'See \\{{#include a.md}}.', 'MD', in_code=True),
    Rule('MYST_SYNTAX', 'warning', '(label)=', '(label) is fine', 'GH MY', inline=False),
    Rule('MYST_SYNTAX', 'warning', '+++', '++ a', 'GH MY', inline=False),
    Rule('MYST_SYNTAX', 'warning', 'Use {ref}`x` here.', 'Use `{x}` or `a{b}` here.', 'GH MY', inline=False),
    Rule('MYST_SYNTAX', 'warning', '```{note}\nx\n```', '```text\nx\n```', 'GH MD MY', inline=False),
    Rule('HEADING_LEVEL', 'warning', '# T\n\n#### Skipped', '# T\n\n## A', 'MY', inline=False, line=2),
    Rule('HEADING_LEVEL', 'warning', '# T\n\n# Second', '# T\n\n## Second', 'MY', inline=False, line=2),
    Rule('LINE_COMMENT', 'error', '% of users agree', '10% of users agree', 'MY', fixed='\\% of users agree'),
    Rule('LINE_COMMENT', 'error', '- % more', '- 5% more', 'MY', fixed='- \\% more'),
    Rule('LINE_COMMENT', 'error', '> % quoted', '> 5% quoted', 'MY', fixed='> \\% quoted'),
    Rule('HEADING_ATTRS', 'error', '## Sets {a, b}', '## Sets of a and b', 'MD', fixed='## Sets {a, b\\}', inline=False),
    Rule('BARE_URL', 'warning', 'See https://example.com/x.', 'See <https://example.com/x>.', 'GH OB MD MY', fixed='See <https://example.com/x>.'),
    Rule('BARE_URL', 'warning', 'See https://e.com/x_(y).', 'See [x](https://e.com/x_(y)).', 'GH MD MY', fixed='See <https://e.com/x_(y)>.'),
    Rule('BARE_URL', 'warning', 'Visit www.example.com today.', 'Visit <https://www.example.com> today.', 'GH OB MD MY',
         fixed='Visit <www.example.com> today.'),
    Rule('EMOJI_SHORTCODE', 'warning', 'Nice :smile: work.', 'At 10:30:00 sharp.', 'GH MD MY'),
    Rule('DOLLAR_SIGN', 'warning', 'Costs $5 a month.', 'Math $x$ stays.', 'OB MY', fixed='Costs \\$5 a month.'),
    Rule('DOLLAR_SIGN', 'warning', 'Costs $1,000.', 'Costs USD 1,000.', 'OB MY', fixed='Costs \\$1,000.'),
    Rule('TILDE_STRIKE', 'warning', 'About ~approx~ here.', 'From ~5 ms to ~10 ms, ~~two~~ too.', 'GH OB MD MY',
         fixed='About \\~approx~ here.'),
]

INTRO = 'Intro.\n\n'  # so the reported line number is checked, not just the finding


def found(text, code):
    return [(sev, n) for sev, c, n, _ in check(text) if c == code]


class Rules(unittest.TestCase):
    def rows(self):
        for r in RULES:
            with self.subTest(code=r.code, bad=r.bad):
                yield r

    def test_bad_is_reported(self):
        for r in self.rows():
            self.assertIn((r.severity, 3 + r.line), found(INTRO + r.bad, r.code))

    def test_good_is_not(self):
        for r in self.rows():
            self.assertEqual(found(INTRO + r.good, r.code), [])

    def test_fenced_code(self):
        for r in self.rows():
            for fence in ('````', '~~~~'):
                self.assertEqual(bool(found(f'{fence}text\n{r.bad}\n{fence}\n', r.code)), r.in_code, fence)

    def test_code_span(self):
        for r in self.rows():
            if r.inline:
                self.assertEqual(bool(found(f'Code `{r.bad}` here.', r.code)), r.in_code)

    def test_front_matter(self):
        for r in self.rows():
            self.assertEqual(bool(found(f'---\n{r.bad}\n---\n# T\n', r.code)), r.in_code)

    def test_indented_code(self):
        for r in self.rows():
            indented = '\n'.join('    ' + line for line in r.bad.split('\n'))
            self.assertEqual(bool(found(INTRO + indented + '\n', r.code)), r.in_code)

    def test_escape(self):
        for r in self.rows():
            text, n = escape(r.bad)
            self.assertEqual(escape(r.good), (r.good, 0))
            if r.fixed is None:
                self.assertEqual((text, n), (r.bad, 0))  # nothing it can't fix is changed
                continue
            self.assertEqual((text, n), (r.fixed, 1))
            self.assertEqual(found(text, r.code), [])
            self.assertEqual(escape(text), (text, 0))  # a second run changes nothing

    def test_every_row_names_its_renderers(self):
        for r in self.rows():
            self.assertTrue(r.verified and set(r.verified.split()) <= {'GH', 'OB', 'MD', 'MY'})

    def test_every_rule_has_a_row(self):
        with open(compat.__file__, encoding='utf-8') as f:
            source = f.read()
        codes = set(re.findall(r"add\('(?:error|warning)', '([A-Z_]+)'", source))
        self.assertEqual(codes, {r.code for r in RULES})


class Code(unittest.TestCase):
    """What the table can't show about code and lists."""

    def test_indented_code_needs_a_blank_line(self):
        self.assertEqual(found('A paragraph\n\n    % code\n', 'LINE_COMMENT'), [])
        # MY: four spaces into a paragraph is its text; up to three, a comment that splits it
        self.assertEqual(found('A paragraph\n    % continues it\nend.\n', 'LINE_COMMENT'), [])
        self.assertEqual(escape('A paragraph\n    % continues it\n'), ('A paragraph\n    % continues it\n', 0))
        self.assertEqual(found('A paragraph\n  % two spaces\nend.\n\n   % three\n', 'LINE_COMMENT'), [('error', 2), ('error', 5)])

    def test_indented_code_runs_across_blank_lines(self):
        self.assertEqual(found('Intro.\n\n    % one\n\n    % two\n\nAfter.\n% three\n', 'LINE_COMMENT'), [('error', 8)])

    def test_inside_a_list_the_indent_continues_the_item(self):
        # GH, MD, MY: indented after a blank line inside a list continues the item; MY drops a % line there
        text = '- item\n\n    % in the item\n\nBack at the margin.\n\n    % code again\n'
        self.assertEqual(found(text, 'LINE_COMMENT'), [('error', 3)])
        self.assertEqual(escape(text), (text.replace('    % in', '    \\% in'), 1))
        self.assertEqual(found('1. item\n\n    % in the item\n', 'LINE_COMMENT'), [('error', 3)])
        self.assertEqual(found('- item\n  % lazy in the item\n', 'LINE_COMMENT'), [('error', 2)])

    def test_a_tab_indents_code(self):
        self.assertEqual(found('Intro.\n\n\t% code\n', 'LINE_COMMENT'), [])

    def test_unclosed_front_matter_and_fences(self):
        self.assertEqual(found('---\n% not front matter\n', 'LINE_COMMENT'), [('error', 2)])
        self.assertEqual(found('```text\n% never closed\n', 'LINE_COMMENT'), [])
        self.assertEqual(found('```text\n```not a close\n% inside\n```\n% after\n', 'LINE_COMMENT'), [('error', 5)])

    def test_math_is_not_prose(self):
        self.assertEqual(check('$$\na ==b== c\n$$\n'), [])
        self.assertEqual(escape('$$\n% x\n$$\n'), ('$$\n% x\n$$\n', 0))
        self.assertEqual(found('Intro.\n\n    $$\n    a\\,b\n    $$\n', 'DOLLAR_MATH'), [])

    def test_a_directive_fence_inside_code(self):
        self.assertEqual(found('````text\n```{note}\n```\n````\n', 'MYST_SYNTAX'), [])

    def test_math_fences_left_alone(self):
        unsafe = '```math\na \\\\ b\n```\n'
        self.assertEqual(escape(unsafe), (unsafe, 0))
        unclosed = '```math\nx\n'
        self.assertEqual(escape(unclosed), (unclosed, 0))
        indented = '  ```math\n  x\n  ```\n'
        self.assertEqual(escape(indented), ('  $$\n  x\n  $$\n', 1))


class Details(unittest.TestCase):
    def test_messages_name_the_fix(self):
        msgs = {c: m for _, c, _, m in check('% x\n\nSee https://a.com and $5.\n\n## H {x}\n\n$$ x^{*} $$\n')}
        self.assertIn('write \\%', msgs['LINE_COMMENT'])
        self.assertIn('<https://a.com>', msgs['BARE_URL'])
        self.assertIn('\\}', msgs['HEADING_ATTRS'])
        self.assertIn('\\ast for *', msgs['DOLLAR_MATH'])

    def test_findings_are_in_line_order(self):
        lines = [n for _, _, n, _ in check('% a\n\n{{#include x}}\n\n$$\na\\,b\n$$\n')]
        self.assertEqual(lines, sorted(lines))

    def test_heading_levels(self):
        self.assertEqual(found('# T\n\n## A\n\n### B\n\n## C\n\n#### D\n', 'HEADING_LEVEL'), [('warning', 9)])
        self.assertEqual(found('## A\n\n### B\n', 'HEADING_LEVEL'), [])
        self.assertEqual(found('# % of users\n', 'LINE_COMMENT'), [])  # a heading, not a comment

    def test_line_joined_only_before_prose(self):
        for fine in ('**Steps**\n- one\n', '**Steps**\n1. one\n', '**Table**\n| a |\n', '**Q:** inline. A: here.\n', '**Note**\n```text\nx\n```\n',
                     '**Last**'):
            self.assertEqual(found(fine, 'LINE_JOINED'), [], fine)
        self.assertEqual(found('**Goal:**\nKeep it.\n', 'LINE_JOINED'), [('warning', 1)])

    def test_urls_inside_links_and_code_are_fine(self):
        text = '<https://ok.com> [https://l.com](https://l.com) [x](https://y.com) `https://code` ![i](https://img.png)'
        self.assertEqual(found(text, 'BARE_URL'), [])

    def test_escape_counts_every_fix(self):
        text = '% a\n## H {x}\nSee https://a.com, $5 and ~b~ and [[2]](s.md).\n'
        self.assertEqual(escape(text), ('\\% a\n## H {x\\}\nSee <https://a.com>, \\$5 and \\~b~ and [\\[2\\]](s.md).\n', 6))

    def test_escape_leaves_code_spans_and_links(self):
        text = 'Keep `$5 ~a~ https://x.com [[1]](y)` and [$5](https://e.com/$5).\n'
        self.assertEqual(escape(text), (text, 0))


class Links(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='compat-links-')
        helpers.write(self.root, 'notes/a.md', '# A\n')
        helpers.write(self.root, 'notes/My Note.md', '# M\n')
        helpers.write(self.root, 'other/deep/b.md', '# B\n')
        helpers.write(self.root, '.hidden/b2.md', '# hidden\n')
        self.dir = os.path.join(self.root, 'notes')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def codes(self, text):
        return [(c, n) for _, c, n, _ in check_links(text, self.dir, self.root)]

    def test_links_that_resolve_everywhere(self):
        text = ('[a](a.md) [a](./a.md#a) [m](My%20Note.md) [b](../other/deep/b.md "title") [web](https://x.com) [anchor](#a) '
                '[mail](mailto:x@y.z) [p](<a.md>) [q](a.md?x=1) [only a query](?x=1) [](  )\n```text\n[x](missing.md)\n```\n')
        self.assertEqual(self.codes(text), [])

    def test_spaces(self):
        findings = check_links('[m](My Note.md)\n', self.dir, self.root)
        self.assertEqual([(c, n) for _, c, n, _ in findings], [('LINK_SPACES', 1)])
        self.assertIn('My%20Note.md', findings[0][3])

    def test_paths_github_does_not_resolve(self):
        findings = check_links('[b](b.md)\n[b](/other/deep/b.md)\n[r](other/deep/b.md)\n[x](nowhere.md)\n[h](b2.md)\n', self.dir, self.root)
        self.assertEqual([(c, n) for _, c, n, _ in findings], [('LINK_PATH', 1), ('LINK_PATH', 3), ('LINK_PATH', 4), ('LINK_PATH', 5)])
        self.assertIn('write ../other/deep/b.md', findings[0][3])  # found by its name
        self.assertIn('write ../other/deep/b.md', findings[1][3])  # found from the repository root
        self.assertNotIn('write', findings[2][3])
        self.assertNotIn('write', findings[3][3])  # hidden folders aren't searched

    def test_folders(self):
        self.assertEqual(self.codes('[o](../other/deep)\n'), [('LINK_FOLDER', 1)])

    def test_placeholders(self):
        self.assertEqual(self.codes('[t](<slug>.md) [t]({{x}}.md) [t](…)\n'), [])


if __name__ == '__main__':
    unittest.main()
