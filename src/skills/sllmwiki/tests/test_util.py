"""Tests for lib/util.py."""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import helpers
from lib import util


class Files(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='util-')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_text_round_trip_keeps_line_endings(self):
        path = os.path.join(self.dir, 'a', 'b.md')
        util.write_text(path, 'é\r\nx\n')
        self.assertEqual(util.read_text(path), 'é\r\nx\n')
        self.assertEqual(util.read_bytes(path), 'é\r\nx\n'.encode())

    def test_git_root(self):
        self.assertIsNone(util.git_root(self.dir))
        helpers.git_init(helpers.write(self.dir, 'x', '') and self.dir)
        sub = os.path.join(self.dir, 'sub')
        os.makedirs(sub)
        self.assertEqual(os.path.realpath(util.git_root(sub)), os.path.realpath(self.dir))

    def test_git_root_without_git(self):
        with mock.patch('subprocess.run', side_effect=OSError):
            self.assertIsNone(util.git_root(self.dir))


class Values(unittest.TestCase):
    def test_dumps(self):
        self.assertEqual(json.loads(util.dumps({'b': 'é', 'a': [1]})), {'b': 'é', 'a': [1]})
        self.assertIn('é', util.dumps('é'))

    def test_dates(self):
        self.assertTrue(util.is_date('2026-02-28'))
        self.assertTrue(util.is_date(util.today()))
        for bad in ('2026-02-30', '2026-2-3', '26-02-03', 20260203, None, '2026-02-03T00:00'):
            self.assertFalse(util.is_date(bad), bad)

    def test_setup_stdio(self):
        stream = io.TextIOWrapper(io.BytesIO(), encoding='ascii')
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(sys, 'stdout', stream))
            stack.enter_context(mock.patch.object(sys, 'stderr', io.StringIO()))  # no reconfigure: left alone
            util.setup_stdio()
            self.assertEqual(sys.stdout.encoding, 'utf-8')


class Footer(unittest.TestCase):
    BODY = b'# Doc\n\nText.\n'
    FOOTER = b'\n\n<!-- sllmwiki:original-source -->\n## Original source\n\n- URL: <https://x>\n'

    def test_split_and_hash_leave_the_footer_out(self):
        data = self.BODY + self.FOOTER
        self.assertEqual(util.split_footer(data), (self.BODY, self.FOOTER))
        self.assertEqual(util.source_hash(data), util.md5(self.BODY))

    def test_no_footer(self):
        self.assertEqual(util.split_footer(self.BODY), (self.BODY, b''))
        self.assertEqual(util.source_hash(self.BODY), util.md5(self.BODY))

    def test_a_footer_without_its_blank_line_still_splits(self):
        data = self.BODY + b'<!-- sllmwiki:original-source -->\nx\n'
        self.assertEqual(util.split_footer(data)[0], self.BODY)

    def test_only_the_last_marker_counts(self):
        quoted = b'The marker <!-- sllmwiki:original-source --> quoted.\n'
        data = quoted + self.FOOTER
        self.assertEqual(util.split_footer(data)[0], quoted)


if __name__ == '__main__':
    unittest.main()
