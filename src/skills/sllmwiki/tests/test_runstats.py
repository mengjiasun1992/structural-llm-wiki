"""Tests for lib/runstats.py: a run's time, turns and tokens."""

import datetime
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import helpers  # noqa: F401  (puts scripts/ on the path)
from lib import runstats

T0 = datetime.datetime(2026, 10, 20, 12, 0, tzinfo=datetime.timezone.utc)


def line(minute, request, out=10, kind='assistant', **usage):
    u = dict({'input_tokens': 2, 'cache_creation_input_tokens': 100, 'cache_read_input_tokens': 1000, 'output_tokens': out}, **usage)
    return json.dumps({'type': kind, 'requestId': request, 'timestamp': f'2026-10-20T12:{minute:02d}:00.000Z', 'message': {'usage': u}})


class RunStats(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix='runstats-')
        self.path = helpers.write(self.home, 'projects/-work-wiki/abc-123.jsonl', '\n'.join([
            line(0, 'before'),                      # before the run started
            line(5, 'r1'), line(5, 'r1'),           # one request, two lines
            line(6, 'r2', out=20),
            line(7, 'x', kind='user'),              # not a request
            '{not json', json.dumps([1]),
            json.dumps({'type': 'assistant', 'timestamp': 'soon', 'message': {'usage': {}}}),
        ]) + '\n')

    def tearDown(self):
        shutil.rmtree(self.home)

    def test_the_transcript_is_found_by_session(self):
        self.assertEqual(runstats.transcript('abc-123', self.home), self.path)
        with mock.patch.dict(os.environ, {'CLAUDE_CODE_SESSION_ID': 'abc-123', 'CLAUDE_CONFIG_DIR': self.home}):
            self.assertEqual(runstats.transcript(), self.path)
        self.assertIsNone(runstats.transcript('nope', self.home))
        self.assertIsNone(runstats.transcript('../../etc/x', self.home))
        with mock.patch.dict(os.environ, {'CLAUDE_CODE_SESSION_ID': ''}):
            self.assertIsNone(runstats.transcript())

    def test_usage_counts_each_request_once_after_the_start(self):
        start = T0 + datetime.timedelta(minutes=1)
        self.assertEqual(runstats.usage(self.path, start), {'turns': 2, 'tokens_in': 2204, 'cached': 2000, 'tokens_out': 30})
        self.assertIsNone(runstats.usage(os.path.join(self.home, 'gone.jsonl'), start))

    def test_section(self):
        started = (T0 + datetime.timedelta(minutes=1)).isoformat()
        lines = runstats.section(started, cost=2.125, at=T0 + datetime.timedelta(minutes=73), path=self.path)
        self.assertEqual(lines, ['## Run', '', '- Time: 1 h 12 min since the run started',
                                 '- Turns: 2; tokens: 2,204 in (2,000 of them from the cache), 30 out (this session only, not its subagents)',
                                 '- Cost: $2.12'])
        self.assertEqual(runstats.section(None, path=self.path), ['## Run', '', '- Time: not recorded',
                                                                  '- Turns and tokens: not counted, since the run has no start time'])
        self.assertEqual(runstats.section(started)[3], '- Turns and tokens: no session transcript to read them from')
        self.assertIn('- Time: 4 min since the run started', runstats.section('2026-10-20T12:00:00', at=T0 + datetime.timedelta(minutes=4)))

    def test_model(self):
        self.assertIsNone(runstats.model(self.path))  # no reply names one
        helpers.write(self.home, 'm.jsonl', '\n'.join([
            json.dumps({'type': 'assistant', 'message': {'model': 'claude-opus-5-5'}}),
            json.dumps({'type': 'assistant', 'message': {'model': '<synthetic>'}}),  # a reply the CLI wrote itself
            '{not json', json.dumps({'type': 'user', 'message': {'model': 'x'}}), json.dumps([1])]))
        self.assertEqual(runstats.model(os.path.join(self.home, 'm.jsonl')), 'claude-opus-5-5')
        self.assertIsNone(runstats.model(None))
        self.assertIsNone(runstats.model(os.path.join(self.home, 'gone.jsonl')))

    def test_parse_time(self):
        self.assertEqual(runstats.parse_time('2026-10-20T12:00:00Z'), T0)
        self.assertIsNone(runstats.parse_time(3))
        self.assertIsNone(runstats.parse_time('later'))


if __name__ == '__main__':
    unittest.main()
