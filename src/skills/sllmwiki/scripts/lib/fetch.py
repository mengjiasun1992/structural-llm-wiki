"""Fetching a source over HTTP(S), and telling what kind of source it is.

A page behind a login, a paywall or anti-bot protection is never worked around
(design doc §4.7): its refusal is reported, and the source becomes a link.
"""

import os
import re
import ssl
import urllib.error
import urllib.request

from . import plaintext

USER_AGENT = 'sllmwiki (+https://github.com/mengjiasun1992/structural-llm-wiki)'
MAX_BYTES = 20 * 1024 * 1024
BLOCKED = (401, 402, 403, 407, 429, 451)
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


def fetch(url, timeout=30):
    """The response for url, following redirects; raises FetchError."""
    if not re.match(r'https?://', url):
        raise FetchError(f'{url}: only http(s) URLs are fetched')
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,text/markdown,text/plain,application/pdf;q=0.9,*/*;q=0.5'})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=tls_context()) as r:
            data = r.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise FetchError(f'{url}: over {MAX_BYTES // (1024 * 1024)} MB; record it as a link')
            return Response(r.geturl(), r.status, r.headers.get('Content-Type', ''), data)
    except urllib.error.HTTPError as e:
        e.close()
        if e.code in BLOCKED:
            raise FetchError(f'{url}: HTTP {e.code}: it needs a login or payment, or refuses automated fetches; '
                             'record it as a link, and never get around it') from None
        raise FetchError(f'{url}: HTTP {e.code}') from None
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise FetchError(f'{url}: {getattr(e, "reason", e)}') from None


def kind_of(content_type, name):
    """'text', 'html', 'pdf', 'tex' or 'code' from a content type, else from the file name's extension; None when neither tells.
    A code file served as plain text is code."""
    ct = (content_type or '').split(';')[0].strip().lower()
    ext = os.path.splitext(name.split('?')[0].split('#')[0])[1].lower()
    if ext in plaintext.LANGUAGES and (ct in ('', 'text/plain', 'application/octet-stream') or ct.startswith('text/x-')):
        return 'code'
    by_type = {'text/markdown': 'text', 'text/x-markdown': 'text', 'text/plain': 'text', 'text/html': 'html',
               'application/xhtml+xml': 'html', 'application/pdf': 'pdf', 'application/x-tex': 'tex', 'text/x-tex': 'tex'}
    if ct in by_type:
        return by_type[ct]
    return {'.md': 'text', '.markdown': 'text', '.txt': 'text', '.html': 'html', '.htm': 'html', '.pdf': 'pdf', '.tex': 'tex'}.get(ext)


def charset(content_type):
    m = re.search(r'charset=([\w-]+)', content_type or '', re.I)
    return m.group(1) if m else None
