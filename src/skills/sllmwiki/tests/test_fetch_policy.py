"""Tests for lib/fetch.py and lib/policy.py (no network: a local server and mocks)."""

import io
import json
import os
import subprocess
import tempfile
import unittest
import urllib.error
from unittest import mock

import helpers
from lib import fetch, policy


class Fetch(unittest.TestCase):
    def test_fetch_and_kind(self):
        with helpers.LocalServer({'/a': (200, {'Content-Type': 'text/markdown; charset=utf-8'}, b'# A\n'),
                                  '/r': (302, {'Location': '/a'}, b'')}) as s:
            r = fetch.fetch(s.url('/r'))
            self.assertEqual((r.status, r.data, r.url.endswith('/a')), (200, b'# A\n', True))
            self.assertEqual(fetch.kind_of(r.content_type, r.url), 'text')

    def test_refusals(self):
        with helpers.LocalServer({'/login': (401, {}, b''), '/pay': (402, {}, b''), '/gone': (404, {}, b'')}) as s:
            for path in ('/login', '/pay'):
                with self.assertRaises(fetch.FetchError) as e:
                    fetch.fetch(s.url(path))
                self.assertIn('never get around it', str(e.exception))
            with self.assertRaises(fetch.FetchError) as e:
                fetch.fetch(s.url('/gone'))
            self.assertIn('HTTP 404', str(e.exception))
        for url in ('ftp://x', 'file:///etc/passwd'):
            with self.assertRaises(fetch.FetchError):
                fetch.fetch(url)
        with self.assertRaises(fetch.FetchError) as e:
            fetch.fetch('http://127.0.0.1:1/unreachable', timeout=2)
        self.assertIn('127.0.0.1:1', str(e.exception))

    def test_too_large(self):
        with mock.patch.object(fetch, 'MAX_BYTES', 4), helpers.LocalServer({'/big': (200, {}, b'0123456789')}) as s:
            with self.assertRaises(fetch.FetchError) as e:
                fetch.fetch(s.url('/big'))
            self.assertIn('record it as a link', str(e.exception))

    def test_tls_context_falls_back_to_the_system_bundle(self):
        class Context:
            def __init__(self, cas):
                self.cas, self.loaded = cas, None

            def cert_store_stats(self):
                return {'x509_ca': self.cas}

            def load_verify_locations(self, cafile):
                self.loaded = cafile

        bundle = tempfile.NamedTemporaryFile(suffix='.pem', delete=False).name
        try:
            env = {k: v for k, v in os.environ.items() if k != 'SSL_CERT_FILE'}
            with mock.patch.dict(os.environ, env, clear=True):
                for cas, expected in ((0, bundle), (150, None)):  # none of its own, then Python's own
                    with mock.patch('ssl.create_default_context', return_value=Context(cas)):
                        self.assertEqual(fetch.tls_context(('/nope.pem', bundle)).loaded, expected)
            with mock.patch.dict(os.environ, {'SSL_CERT_FILE': bundle}), mock.patch('ssl.create_default_context', return_value=Context(0)):
                self.assertIsNone(fetch.tls_context((bundle,)).loaded)  # the operator's choice wins
        finally:
            os.remove(bundle)

    def test_kind_of(self):
        cases = [('text/html; charset=utf-8', 'x', 'html'), ('application/xhtml+xml', 'x', 'html'), ('application/pdf', 'x', 'pdf'),
                 ('text/plain', 'x', 'text'), ('', 'notes.MD', 'text'), ('application/octet-stream', 'a.pdf?x=1#p', 'pdf'),
                 ('', 'page.htm', 'html'), ('', 'data.bin', None), ('image/png', 'x.png', None),
                 ('application/x-tex', 'x', 'tex'), ('text/x-tex', 'x', 'tex'), ('', 'main.tex', 'tex'),
                 ('text/plain; charset=utf-8', 'https://e.com/tcp_input.c', 'code'), ('text/x-python', 'a.py', 'code'),
                 ('', 'b.go', 'code'), ('text/html', 'page.py', 'html')]
        for ct, name, want in cases:
            self.assertEqual(fetch.kind_of(ct, name), want, (ct, name))
        self.assertEqual((fetch.charset('text/html; charset=ISO-8859-1'), fetch.charset('text/html')), ('ISO-8859-1', None))


def completed(stdout='', code=0):
    return subprocess.CompletedProcess([], code, stdout, '')


class Visibility(unittest.TestCase):
    def run_with(self, remote, gh=None, api=None, remotes='origin\n'):
        def fake_run(cmd, **kw):
            if cmd[:3] == ['git', 'config', '--get']:
                return completed(remote or '', 0 if remote else 2)
            if cmd[:2] == ['git', 'remote']:
                return completed(remotes)
            if isinstance(gh, Exception):
                raise gh
            return gh or completed('', 1)
        with mock.patch.object(policy.subprocess, 'run', side_effect=fake_run), \
                mock.patch.object(policy.urllib.request, 'urlopen', side_effect=api or urllib.error.URLError('offline')):
            return policy.visibility('/wiki')

    def test_gh_answers(self):
        self.assertEqual(self.run_with('git@github.com:o/r.git', completed('PUBLIC\n')), 'public')
        self.assertEqual(self.run_with('https://github.com/o/r', completed('PRIVATE\n')), 'private')

    def test_without_gh_the_public_api(self):
        api = mock.MagicMock()
        api.__enter__.return_value = io.StringIO(json.dumps({'private': False}))
        self.assertEqual(self.run_with('https://github.com/o/r.git', OSError(), lambda *a, **k: api), 'public')
        not_found = urllib.error.HTTPError('u', 404, 'nf', {}, io.BytesIO())
        self.assertEqual(self.run_with('https://github.com/o/r.git', completed('', 1), mock.Mock(side_effect=not_found)), 'private')
        limited = urllib.error.HTTPError('u', 403, 'rate', {}, io.BytesIO())
        self.assertEqual(self.run_with('https://github.com/o/r.git', subprocess.TimeoutExpired('gh', 1), mock.Mock(side_effect=limited)), 'unknown')
        self.assertEqual(self.run_with('https://github.com/o/r.git'), 'unknown')  # offline

    def test_no_remote_or_another_host(self):
        self.assertEqual(self.run_with(None, remotes=''), 'private')
        self.assertEqual(self.run_with('https://gitlab.example.com/o/r.git'), 'unknown')
        self.assertEqual(self.run_with('git@github-work:o/r.git', completed('PRIVATE\n')), 'private')  # an SSH host alias


class Repository(helpers.WikiTestCase):
    def test_a_fixture_wiki_has_no_remote(self):
        self.assertEqual(policy.visibility(self.root), 'private')


class MayCopy(unittest.TestCase):
    def test_decisions(self):
        self.assertFalse(policy.may_copy('links-only', 'private', 'CC0-1.0')[0])
        self.assertIn('links-only', policy.may_copy('links-only', 'private', 'CC0-1.0')[1])
        self.assertTrue(policy.may_copy('allow', 'private', 'proprietary')[0])
        self.assertTrue(policy.may_copy('allow', 'public', 'CC-BY-4.0')[0])
        self.assertTrue(policy.may_copy('allow', 'public', 'cc-by-sa-4.0 ')[0])
        ok, why = policy.may_copy('allow', 'public', 'unknown')
        self.assertFalse(ok)
        self.assertIn('--allow-restricted', why)
        ok, why = policy.may_copy('allow', 'unknown', None)
        self.assertFalse(ok)
        self.assertIn('couldn\'t confirm', why)
        self.assertIn('an unknown license', why)
        ok, why = policy.may_copy('allow', 'public', 'proprietary', 'Jane, 2026-10-21')
        self.assertTrue(ok)
        self.assertIn('Jane, 2026-10-21', why)


if __name__ == '__main__':
    unittest.main()
