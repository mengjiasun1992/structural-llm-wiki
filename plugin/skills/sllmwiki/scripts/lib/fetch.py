"""Fetching a source over HTTP(S), and telling what kind of source it is.

A page behind a login, a paywall or anti-bot protection is never worked around
(design doc §4.7): its refusal is reported, and the source becomes a link.
"""

import os
import random
import re
import ssl
import time
import urllib.error
import urllib.request

from . import layout, plaintext

USER_AGENT = f'sllmwiki (+{layout.SKILL_URL})'
MAX_BYTES = 20 * 1024 * 1024
BLOCKED = (401, 402, 403, 407, 429, 451)
# A rate-limited fetch (429) is the server asking to wait, not a refusal: retried
# RETRIES times with exponential backoff and jitter, and a Retry-After honored up to
# MAX_WAIT seconds; then it's blocked like the others (the owner's decision, #42).
RETRIES, BACKOFF, MAX_WAIT = 3, 2.0, 60
sleep, jitter = time.sleep, random.uniform  # tests replace them
# The system's CA bundles, for a Python without its own (python.org's macOS
# build, before its "Install Certificates" step): verification stays on.
SYSTEM_CA = ('/etc/ssl/cert.pem', '/etc/ssl/certs/ca-certificates.crt', '/etc/pki/tls/certs/ca-bundle.crt')


class FetchError(Exception):
    pass


class Response:
    def __init__(self, url, status, content_type, data):
        self.url, self.status, self.content_type, self.data = url, status, content_type, data


def tls_context(system_ca=SYSTEM_CA):
    """Python's default TLS context, given the system's CA bundle when Python has none."""
    context = ssl.create_default_context()
    if not context.cert_store_stats()['x509_ca'] and not os.environ.get('SSL_CERT_FILE'):
        for path in system_ca:
            if os.path.isfile(path):
                context.load_verify_locations(cafile=path)
                break
    return context


def wait_for(attempt, retry_after):
    """Seconds to wait before retry number attempt (0-based): exponential backoff with
    jitter, or the server's Retry-After when longer; None when that's over MAX_WAIT."""
    delay = jitter(BACKOFF * 2 ** attempt / 2, BACKOFF * 2 ** attempt)
    asked = int(retry_after) if (retry_after or '').strip().isdigit() else 0
    return None if asked > MAX_WAIT else max(delay, asked)


def fetch(url, timeout=30):
    """The response for url, following redirects, retrying a 429; raises FetchError."""
    for attempt in range(RETRIES + 1):
        try:
            return _fetch_once(url, timeout)
        except _RateLimited as e:
            delay = wait_for(attempt, e.retry_after) if attempt < RETRIES else None
            if delay is None:
                raise FetchError(f'{url}: HTTP 429: rate limited, {attempt} retr{"y" if attempt == 1 else "ies"} later still refused; '
                                 'record it as a link, and never get around it') from None
            sleep(delay)


class _RateLimited(Exception):
    def __init__(self, retry_after):
        super().__init__(retry_after)
        self.retry_after = retry_after


def _fetch_once(url, timeout):
    if not re.match(r'https?://', url):
        raise FetchError(f'{url}: only http(s) URLs are fetched')
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,text/markdown,text/plain,application/pdf;q=0.9,application/epub+zip;q=0.9,*/*;q=0.5'})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=tls_context()) as r:
            data = r.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise FetchError(f'{url}: over {MAX_BYTES // (1024 * 1024)} MB; record it as a link')
            return Response(r.geturl(), r.status, r.headers.get('Content-Type', ''), data)
    except urllib.error.HTTPError as e:
        e.close()
        if e.code == 429:
            raise _RateLimited(e.headers.get('Retry-After') if e.headers else None) from None
        if e.code in BLOCKED:
            raise FetchError(f'{url}: HTTP {e.code}: it needs a login or payment, or refuses automated fetches; '
                             'record it as a link, and never get around it') from None
        raise FetchError(f'{url}: HTTP {e.code}') from None
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise FetchError(f'{url}: {getattr(e, "reason", e)}') from None


def kind_of(content_type, name):
    """'text', 'html', 'pdf', 'epub', 'tex' or 'code' from a content type, else from the file name's extension; None when neither tells.
    A code file served as plain text is code."""
    ct = (content_type or '').split(';')[0].strip().lower()
    ext = os.path.splitext(name.split('?')[0].split('#')[0])[1].lower()
    if ext in plaintext.LANGUAGES and (ct in ('', 'text/plain', 'application/octet-stream') or ct.startswith('text/x-')):
        return 'code'
    by_type = {'text/markdown': 'text', 'text/x-markdown': 'text', 'text/plain': 'text', 'text/html': 'html',
               'application/xhtml+xml': 'html', 'application/pdf': 'pdf', 'application/epub+zip': 'epub', 'application/x-tex': 'tex', 'text/x-tex': 'tex', 'text/x-rst': 'text'}
    if ct in by_type:
        return by_type[ct]
    return {'.md': 'text', '.markdown': 'text', '.txt': 'text', '.html': 'html', '.htm': 'html', '.pdf': 'pdf', '.epub': 'epub', '.tex': 'tex', '.rst': 'text'}.get(ext)


def charset(content_type):
    m = re.search(r'charset=([\w-]+)', content_type or '', re.I)
    return m.group(1) if m else None
