"""Tests for src/tools/bump-version.py: every file naming the release version moves to the next one together."""

import os
import shutil
import tempfile
import unittest

import helpers

TOOL = os.path.join(helpers.REPO, 'src', 'tools', 'bump-version.py')
FILES = ('plugin/.claude-plugin/plugin.json', 'src/sllmwiki/__init__.py', 'plugin/skills/sllmwiki/SKILL.md',
         'src/actions/review-checklist/action.yml', 'src/actions/wiki-checks/action.yml', 'src/sllmwiki/lib/mermaid.py')


class Bump(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        for rel in FILES:  # copies of the real files, so a new place the version hides in is caught here too
            os.makedirs(os.path.dirname(os.path.join(self.root, rel)), exist_ok=True)
            shutil.copy(os.path.join(helpers.REPO, rel), os.path.join(self.root, rel))
        self.tool = helpers.load_script(TOOL)
        self.old = self.tool.current(self.root)

    def read(self, rel):
        with open(os.path.join(self.root, rel), encoding='utf-8') as f:
            return f.read()

    def run_tool(self, *argv):
        return helpers.run(TOOL, ['--root', self.root, *argv])

    def test_bumps_every_place(self):
        major, minor, patch = map(int, self.old.split('.'))
        new = f'{major}.{minor}.{patch + 1}'
        mermaid = self.read('src/sllmwiki/lib/mermaid.py')
        r = self.run_tool(new)
        self.assertEqual(r.code, 0, r.err)
        self.assertIn(f'{self.old} -> {new}', r.out)
        self.assertEqual(self.tool.current(self.root), new)
        self.assertIn(f'"version": "{new}"', self.read('plugin/.claude-plugin/plugin.json'))
        skill = self.read('plugin/skills/sllmwiki/SKILL.md')
        self.assertNotIn(self.old, skill)
        self.assertIn(f'sllmwiki=={new}', skill)
        for action in ('review-checklist', 'wiki-checks'):
            self.assertIn(f'@v{new}', self.read(f'src/actions/{action}/action.yml'))
        self.assertEqual(self.read('src/sllmwiki/lib/mermaid.py'), mermaid)  # another tool's version, left alone

    def test_refuses(self):
        for bad in ('1.4', 'v9.0.0', '0.0.1', self.old):
            with self.subTest(bad=bad):
                r = self.run_tool(bad)
                self.assertEqual(r.code, 2)
                self.assertEqual(self.tool.current(self.root), self.old)

    def test_a_file_out_of_step(self):
        path = os.path.join(self.root, 'src/actions/wiki-checks/action.yml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('# uses: …@v0.0.1\n')
        r = self.run_tool('99.0.0')
        self.assertEqual(r.code, 1)
        self.assertIn('src/actions/wiki-checks/action.yml doesn\'t name the current version', r.err)
        self.assertEqual(self.tool.current(self.root), self.old)  # nothing written

    def test_a_missing_file(self):
        os.remove(os.path.join(self.root, 'plugin/skills/sllmwiki/SKILL.md'))
        self.assertEqual(self.run_tool('99.0.0').code, 1)


if __name__ == '__main__':
    unittest.main()
