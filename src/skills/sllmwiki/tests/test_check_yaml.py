"""Tests for src/tools/check-yaml.py, the spec-level YAML check (it needs PyYAML;
CI installs it, and without it these tests are skipped)."""

import contextlib
import importlib.util
import io
import json
import os
import unittest

import helpers

try:
    import yaml  # noqa: F401
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

TOOL = os.path.join(os.path.dirname(helpers.SKILL_DIR), '..', 'tools', 'check-yaml.py')


def load_tool():
    spec = importlib.util.spec_from_file_location('check_yaml', TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(HAVE_YAML, 'check-yaml needs PyYAML')
class CheckYaml(helpers.WikiTestCase):
    def setUp(self):
        super().setUp()
        self.tool = load_tool()

    def run_tool(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        old = os.getcwd()
        try:
            os.chdir(self.root)
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = self.tool.main(list(argv))
        finally:
            os.chdir(old)
        return code, out.getvalue(), err.getvalue()

    def test_the_fixture_wiki_is_valid(self):
        code, out, _ = self.run_tool()
        self.assertEqual(code, 0, out)
        self.assertIn('check-yaml: 0 error(s) in', out)

    def test_syntax_error_with_its_line(self):
        self.write('notes.yaml', 'a: 1\nb: [unclosed\nc: 3\n')
        code, out, _ = self.run_tool('notes.yaml')
        self.assertEqual(code, 1)
        self.assertRegex(out, r'error +YAML_ERROR +notes\.yaml:3: ')

    def test_duplicate_key_at_any_depth(self):
        self.write('d.yml', 'a: 1\nouter:\n  x: 1\n  x: 2\nlist:\n  - k: 1\n    k: 2\n')
        code, out, _ = self.run_tool('d.yml')
        self.assertEqual(code, 1)
        self.assertEqual(out.count('DUPLICATE_KEY'), 2)
        self.assertIn('d.yml:4: Map keys must be unique; "x" is repeated', out)
        self.assertIn('d.yml:7:', out)

    def test_several_documents(self):
        self.write('multi.yaml', 'a: 1\n---\nb: 2\nb: 3\n')
        code, out, _ = self.run_tool('multi.yaml')
        self.assertEqual(code, 1)
        self.assertIn('multi.yaml:4:', out)

    def test_yaml_blocks_in_markdown_report_markdown_lines(self):
        self.write('doc.md', '# Doc\n\nText.\n\n```yaml\na: 1\na: 2\n```\n\n~~~yml\nok: true\n~~~\n\n  ```yaml\n  b: [x\n  ```\n\n```text\nnot: [yaml\n```\n')
        code, out, _ = self.run_tool('doc.md')
        self.assertEqual(code, 1)
        self.assertIn('doc.md:7: Map keys must be unique; "a" is repeated', out)
        self.assertRegex(out, r'YAML_ERROR +doc\.md:1[56]: ')  # the indented block, at its line in the file
        self.assertEqual(out.count('error '), 2)  # the text block isn't YAML

    def test_tracked_files_skip_the_sources_but_not_their_manifest(self):
        self.write('ingested/broken.yaml', 'a: [x\n')  # a verbatim source: left alone
        self.write('node_modules/pkg/x.yaml', 'a: [x\n')
        self.write('ingested/manifest.yaml', self.read('ingested/manifest.yaml') + 'alpha-doc:\n  file: again\n')
        helpers.git(self.root, 'add', '-A')
        code, out, _ = self.run_tool()
        self.assertEqual(code, 1)
        self.assertIn('ingested/manifest.yaml', out)
        self.assertNotIn('broken.yaml', out)
        self.assertNotIn('node_modules', out)

    def test_moved_sources_folder(self):
        self.write('Config.toml', '[structural-llm-wiki-paths]\ningested = "sources"\ningested_manifest = "sources/manifest.yaml"\n')
        self.write('sources/broken.yaml', 'a: [x\n')
        self.write('ingested/now-checked.yaml', 'a: [x\n')
        helpers.git(self.root, 'add', '-A')
        code, out, _ = self.run_tool()
        self.assertEqual(code, 1)
        self.assertIn('ingested/now-checked.yaml', out)
        self.assertNotIn('sources/broken.yaml', out)

    def test_json(self):
        self.write('d.yml', 'a: 1\na: 2\n')
        code, out, _ = self.run_tool('--json', 'd.yml')
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertEqual(data['errors'], 1)
        self.assertEqual(data['findings'][0], {'file': 'd.yml', 'line': 2, 'code': 'DUPLICATE_KEY', 'message': 'Map keys must be unique; "a" is repeated'})

    def test_usage_error(self):
        code, _, err = self.run_tool('--bogus')
        self.assertEqual(code, 2)
        self.assertIn('usage: check-yaml.py', err)


if __name__ == '__main__':
    unittest.main()
