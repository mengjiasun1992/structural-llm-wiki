"""The instructions every run pays for in tokens (design doc §9): each file within
its word budget, and every script, subcommand and option they name real."""

import glob
import os
import re
import unittest

import helpers

SKILL = helpers.SKILL_DIR
COMMANDS = os.path.join(os.path.dirname(os.path.dirname(SKILL)), 'commands')
BUDGETS = {  # words per file; a run loads SKILL.md, a workflow, its steps, shared.md, shared-guide.md and one template with its guide
    'SKILL.md': 900,
    'workflows/*.md': 1200,
    'steps/*.md': 1200,
    'templates/narratives/shared.md': 600,
    'templates/narratives/shared-guide.md': 1000,
}
TEMPLATE_AND_GUIDE = 1400
BUILD_LOAD = 9000  # SKILL.md, build, its steps, shared.md, shared-guide.md and the largest template with its guide
QUERY_LOAD = 2500  # SKILL.md and query


def words(path):
    with open(path, encoding='utf-8') as f:
        return len(f.read().split())


def instruction_files():
    files = [os.path.join(SKILL, 'SKILL.md'), os.path.join(SKILL, 'templates', 'narratives', 'shared.md'),
             os.path.join(SKILL, 'templates', 'narratives', 'shared-guide.md')]
    files += glob.glob(os.path.join(SKILL, 'workflows', '*.md')) + glob.glob(os.path.join(SKILL, 'steps', '*.md'))
    files += glob.glob(os.path.join(SKILL, 'templates', 'narratives', '*', '*.md')) + glob.glob(os.path.join(COMMANDS, '*.md'))
    return sorted(files)


class Budgets(unittest.TestCase):
    def test_each_file(self):
        for pattern, budget in BUDGETS.items():
            for path in glob.glob(os.path.join(SKILL, pattern)):
                with self.subTest(file=os.path.relpath(path, SKILL)):
                    self.assertLessEqual(words(path), budget)

    def test_each_template_with_its_guide(self):
        for folder in glob.glob(os.path.join(SKILL, 'templates', 'narratives', '*', '')):
            with self.subTest(template=os.path.basename(os.path.dirname(folder))):
                self.assertLessEqual(words(os.path.join(folder, 'template.md')) + words(os.path.join(folder, 'guide.md')), TEMPLATE_AND_GUIDE)

    def test_what_a_run_loads(self):
        skill = words(os.path.join(SKILL, 'SKILL.md'))
        steps = sum(words(os.path.join(SKILL, 'steps', f'{s}.md')) for s in ('tags', 'ingest', 'narrative'))
        largest = max(words(os.path.join(f, 'template.md')) + words(os.path.join(f, 'guide.md'))
                      for f in glob.glob(os.path.join(SKILL, 'templates', 'narratives', '*', '')))
        build = skill + words(os.path.join(SKILL, 'workflows', 'build.md')) + steps + words(os.path.join(SKILL, 'templates', 'narratives', 'shared.md')) + largest \
            + words(os.path.join(SKILL, 'templates', 'narratives', 'shared-guide.md'))
        self.assertLessEqual(build, BUILD_LOAD)
        self.assertLessEqual(skill + words(os.path.join(SKILL, 'workflows', 'query.md')), QUERY_LOAD)


SCRIPT = re.compile(r'\b([a-z][a-z0-9-]*\.(?:py|sh))\b')
SPAN = re.compile(r'`([^`\n]+)`')


def scripts_named(text):
    """[(script, [subcommand or None], [options])] for each code span that runs a script."""
    out = []
    for span in SPAN.findall(text):
        m = SCRIPT.search(span)
        if not m:
            continue
        rest = span[m.end():].split()
        sub = rest[0] if rest and re.fullmatch(r'[a-z][a-z-]*', rest[0]) else None
        out.append((m.group(1), sub, re.findall(r'(?<![\w-])(--[a-z][a-z-]*)', span[m.end():])))
    return out


def script_path(name):
    for folder in (helpers.SCRIPTS, os.path.join(helpers.REPO, 'src', 'tools')):
        if os.path.isfile(os.path.join(folder, name)):
            return os.path.join(folder, name)
    return None


class References(unittest.TestCase):
    def test_every_script_subcommand_and_option_exists(self):
        checked = 0
        for path in instruction_files():
            with open(path, encoding='utf-8') as f:
                text = f.read()
            for name, sub, options in scripts_named(text):
                where = f'{os.path.relpath(path, os.path.dirname(SKILL))}: {name}'
                with self.subTest(where=where):
                    source_path = script_path(name)
                    self.assertIsNotNone(source_path, f'{where}: no such script')
                    with open(source_path, encoding='utf-8') as f:
                        source = f.read()
                    if sub and name.endswith('.py') and ("add_parser(" in source or "choices=" in source):
                        self.assertIn(f"'{sub}'", source, f'{where}: no subcommand {sub}')
                    for opt in options:
                        self.assertIn(f"'{opt}'", source, f'{where}: no option {opt}')
                    checked += 1
        self.assertGreater(checked, 20)  # the instructions do name scripts

    def test_the_scripts_list_in_skill_md_is_complete(self):
        with open(os.path.join(SKILL, 'SKILL.md'), encoding='utf-8') as f:
            text = f.read()
        listed = set(re.findall(r'^- `([a-z-]+\.py)`', text, re.M))
        commands = {os.path.basename(p) for p in glob.glob(os.path.join(helpers.SCRIPTS, '*.py'))} - {'review-checklist.py'}  # CI's, not the agent's
        self.assertEqual(listed, commands)

    def test_the_parser(self):
        self.assertEqual(scripts_named('Run `search.py section "x#y" --json` and `wiki-check.py`, not `x.md`.'),
                         [('search.py', 'section', ['--json']), ('wiki-check.py', None, [])])


class Commands(unittest.TestCase):
    def test_each_command_routes_to_a_file_that_exists(self):
        for path in glob.glob(os.path.join(COMMANDS, '*.md')):
            with open(path, encoding='utf-8') as f:
                text = f.read()
            with self.subTest(command=os.path.basename(path)):
                self.assertTrue(text.startswith('---\ndescription: '))
                for ref in re.findall(r'`((?:workflows|steps)/[a-z]+\.md)`', text):
                    self.assertTrue(os.path.isfile(os.path.join(SKILL, ref)), ref)


if __name__ == '__main__':
    unittest.main()
