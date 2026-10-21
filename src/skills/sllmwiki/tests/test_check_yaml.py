"""Tests for src/tools/check-yaml.py, the spec-level YAML check. It needs PyYAML,
which CI installs for the unit tests; without it these tests are skipped."""

import json
import os
import unittest

import helpers

try:
    import yaml  # noqa: F401
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

TOOL = os.path.join(helpers.REPO, 'src', 'tools', 'check-yaml.py')


@unittest.skipUnless(HAVE_YAML, 'check-yaml needs PyYAML')
class CheckYaml(helpers.WikiTestCase):
    def check(self, *argv):
        return helpers.run(TOOL, argv, cwd=self.root)

    def test_the_fixture_wiki_is_valid(self):
        r = self.check()
        self.assertEqual(r.code, 0, r.out)
        self.assertRegex(r.out, r'check-yaml: 0 error\(s\) in \d+ file\(s\)')

    def test_a_syntax_error_and_its_line(self):
        self.write('notes.yaml', 'a: 1\nb: [unclosed\nc: 3\n')
        r = self.check('notes.yaml')
        self.assertEqual(r.code, 1)
        self.assertRegex(r.out, r'error +YAML_ERROR +notes\.yaml:3: ')

    def test_duplicate_keys_at_any_depth(self):
        self.write('d.yml', 'a: 1\nouter:\n  x: 1\n  x: 2\nlist:\n  - k: 1\n    k: 2\n')
        r = self.check('d.yml')
        self.assertEqual((r.code, r.out.count('DUPLICATE_KEY')), (1, 2))
        self.assertIn('d.yml:4: Map keys must be unique; "x" is repeated', r.out)
        self.assertIn('d.yml:7:', r.out)

    def test_every_document_in_a_file(self):
        self.write('multi.yaml', 'a: 1\n---\nb: 2\nb: 3\n')
        self.assertIn('multi.yaml:4:', self.check('multi.yaml').out)

    def test_yaml_blocks_in_markdown_at_their_lines(self):
        self.write('doc.md', '# Doc\n\n```yaml\na: 1\na: 2\n```\n\n~~~yml\nok: true\n~~~\n\n```text\nnot: [yaml\n```\n')
        r = self.check('doc.md')
        self.assertEqual(r.code, 1)
        self.assertIn('doc.md:5: Map keys must be unique; "a" is repeated', r.out)
        self.assertEqual(r.out.count('error '), 1)  # the text block isn't YAML

    def test_saved_sources_are_skipped_but_not_their_manifest(self):
        self.write('sllmwiki/sources/broken.yaml', 'a: [x\n')
        self.write('node_modules/pkg/x.yaml', 'a: [x\n')
        self.write('sllmwiki/sources/manifest.yaml', self.read('sllmwiki/sources/manifest.yaml') + 'alpha-doc:\n  kind: text\n')
        helpers.git(self.root, 'add', '-A')
        r = self.check()
        self.assertEqual(r.code, 1)
        self.assertIn('sllmwiki/sources/manifest.yaml', r.out)
        self.assertNotIn('broken.yaml', r.out)
        self.assertNotIn('node_modules', r.out)

    def test_json(self):
        self.write('d.yml', 'a: 1\na: 2\n')
        r = self.check('--json', 'd.yml')
        self.assertEqual(r.code, 1)
        self.assertEqual(json.loads(r.out), {'errors': 1, 'findings': [
            {'file': 'd.yml', 'line': 2, 'code': 'DUPLICATE_KEY', 'message': 'Map keys must be unique; "a" is repeated'}]})

    def test_usage_error(self):
        r = self.check('--bogus')
        self.assertEqual(r.code, 2)
        self.assertIn('usage: check-yaml.py', r.err)


if __name__ == '__main__':
    unittest.main()
