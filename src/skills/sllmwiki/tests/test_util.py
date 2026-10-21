import os
import tempfile
import unittest

import helpers  # noqa: F401  (puts the scripts on the path)
from lib import util as j


class TrimAndStrings(unittest.TestCase):
    def test_trim_family_strips_js_whitespace(self):
        self.assertEqual(j.trim('\u00a0 x \u3000'), 'x')
        self.assertEqual(j.trim_end(' x '), ' x')

    def test_jstr_prints_like_javascript(self):
        self.assertEqual(j.jstr(None), 'null')
        self.assertEqual(j.jstr(True), 'true')
        self.assertEqual(j.jstr(False), 'false')
        self.assertEqual(j.jstr(3.0), '3')
        self.assertEqual(j.jstr(2.5), '2.5')
        self.assertEqual(j.jstr(float('nan')), 'NaN')
        self.assertEqual(j.jstr(1e22), '1e+22')
        self.assertEqual(j.jstr([1, None, 'a']), '1,,a')
        self.assertEqual(j.jstr({'a': 1}), '[object Object]')
        self.assertEqual(j.jstr('s'), 's')

    def test_lists_maps_numbers(self):
        self.assertEqual(j.as_list(None), [])
        self.assertEqual(j.as_list('a'), ['a'])
        self.assertEqual(j.as_list([1]), [1])
        self.assertTrue(j.is_map({}))
        self.assertFalse(j.is_map([]))
        self.assertTrue(j.same_number(3, 3))
        self.assertFalse(j.same_number('3', 3))
        self.assertFalse(j.same_number(True, 1))

    def test_dumps_and_utf8(self):
        self.assertEqual(j.dumps({'a': 'é'}), '{\n  "a": "é"\n}')
        self.assertEqual(j.to_utf8('é'), 'é'.encode('utf-8'))
        self.assertEqual(j.to_utf8('\ud800'), '\ufffd'.encode('utf-8'))


class Dates(unittest.TestCase):
    def test_iso_dates_and_datetimes(self):
        self.assertEqual(j.iso_or_none('2026-10-18'), '2026-10-18T00:00:00Z')
        self.assertEqual(j.iso_or_none('2026-10'), '2026-10-01T00:00:00Z')
        self.assertEqual(j.iso_or_none('2026-10-18T06:01:05Z'), '2026-10-18T06:01:05Z')
        self.assertEqual(j.iso_or_none('2026-10-18T06:01:05.250+02:00'), '2026-10-18T04:01:05Z')
        self.assertEqual(j.iso_or_none('2026-10-18T06:01-0130'), '2026-10-18T07:31:00Z')
        self.assertEqual(j.iso_or_none('2026-10-18T24:00:00Z'), '2026-10-19T00:00:00Z')

    def test_local_time_and_rfc2822(self):
        self.assertIsNotNone(j.date_parse('2026-10-18T06:01:05'))
        self.assertEqual(j.iso_or_none('Sun, 18 Oct 2026 06:01:05 GMT'), '2026-10-18T06:01:05Z')

    def test_not_dates(self):
        for v in (None, True, 'last week', '2026-13-45T00:00:00Z'):
            self.assertIsNone(j.date_parse(v), v)
        self.assertIsNone(j.iso(None))
        self.assertRegex(j.now_iso(), r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$')


class Plumbing(unittest.TestCase):
    def test_init_stdio_is_safe(self):
        j.setup_stdio()

    def test_git_root_and_files(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(j.git_root(os.path.join(d, 'missing')), os.getcwd())  # not a repository: the current directory
            helpers.git(d, 'init', '-q')
            self.assertEqual(os.path.realpath(j.git_root(d)), os.path.realpath(d))
            p = os.path.join(d, 'f.txt')
            j.write_text(p, 'a\r\nb')
            self.assertEqual(j.read_text(p), 'a\r\nb')


if __name__ == '__main__':
    unittest.main()
