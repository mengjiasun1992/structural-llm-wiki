"""Tests for lib/html2md.py: an HTML page's main content as markdown."""

import unittest

import helpers  # noqa: F401  (puts the scripts on the path)
from lib.html2md import convert

PAGE = '''<html><head><title>Retry policy | Docs</title><script>track()</script><style>p{}</style></head><body>
<nav><a href="/">Home</a></nav><header>Site header</header>
<main><h1>Retry policy</h1>
<p>Clients <strong>retry</strong> failed requests with <em>backoff</em>, see <a href="/b?x=1">the backoff doc</a>.<br>Next line &amp; more.</p>
<h2>Details</h2>
<ul><li>First <code>retry()</code></li><li>Second<ul><li>nested</li></ul></li><li>Third<p>with a paragraph</p></li></ul>
<pre><code class="language-python">def retry():
    pass</code></pre>
<table><thead><tr><th>Try</th><th>Wait</th></tr></thead><tbody><tr><td>1</td><td>100 ms | p50</td></tr><tr><td>2</td></tr></tbody></table>
<blockquote><p>Quoted line.</p><p>Second.</p></blockquote>
<img src="/fig.png" alt="Figure 1"><hr>
<div hidden>secret</div><div style="display: none">hidden</div><div aria-hidden="true">aria</div><div role="navigation">menu</div>
<ol start="3"><li>three</li><li>four</li></ol>
<dl><dt>Term</dt><dd>Its meaning.</dd></dl>
<p>A <a href="javascript:void(0)">script link</a>, an <a href="#top">anchor</a>, <del>gone</del>, <code>a`b</code>, <kbd></kbd>
and 2 * 3 [not a link] &lt;tag&gt; snake_case.</p>
</main><footer>Footer</footer><aside>Ads</aside><!-- a comment --></body></html>'''


class Convert(unittest.TestCase):
    def setUp(self):
        self.md, self.title = convert(PAGE, 'https://docs.example.com/retry')

    def test_main_content_only(self):
        for gone in ('Home', 'Site header', 'Footer', 'Ads', 'track', 'secret', 'hidden', 'aria', 'menu', 'a comment'):
            self.assertNotIn(gone, self.md)
        self.assertEqual(self.title, 'Retry policy | Docs')

    def test_blocks(self):
        for want in ('# Retry policy\n\n',
                     'Clients **retry** failed requests with *backoff*, see [the backoff doc](<https://docs.example.com/b?x=1>).\\\nNext line & more.',
                     '\n\n## Details\n\n',
                     '- First `retry()`\n- Second\n  - nested\n- Third\n\n  with a paragraph\n',
                     '```python\ndef retry():\n    pass\n```',
                     '| Try | Wait |\n|---|---|\n| 1 | 100 ms \\| p50 |\n| 2 |  |',
                     '> Quoted line.\n>\n> Second.',
                     '[image: Figure 1](<https://docs.example.com/fig.png>)',
                     '\n---\n',
                     '3. three\n4. four',
                     '**Term**\n\nIts meaning.'):
            self.assertIn(want, self.md)

    def test_inline_details(self):
        self.assertIn('A script link, an anchor, ~~gone~~, ``a`b``,', self.md)
        self.assertIn('2 \\* 3 \\[not a link\\] \\<tag\\> snake\\_case.', self.md)

    def test_no_main_uses_article_then_body(self):
        self.assertEqual(convert('<body><nav>x</nav><article><p>Story</p></article><p>Other</p></body>')[0], 'Story\n')
        self.assertEqual(convert('<body><p>Just a body</p></body>')[0], 'Just a body\n')

    def test_title_when_the_content_has_no_heading(self):
        self.assertEqual(convert('<title>T</title><main><p>Text</p></main>')[0], '# T\n\nText\n')
        self.assertEqual(convert('<title>T</title><main></main>')[0], '# T\n')
        self.assertEqual(convert('<p>No title</p>'), ('No title\n', None))

    def test_relative_links_without_a_base(self):
        self.assertEqual(convert('<p><a href="/x">x</a> <img src="i.png"> <img></p>')[0], '[x](</x>) [image: ](<i.png>)\n')

    def test_odd_markup(self):
        self.assertEqual(convert('<main><h2></h2><p>a</p></span><pre>x```y</pre><table></table><ul><li hidden>x</li></ul></main>')[0],
                         'a\n\n````\nx```y\n````\n')
        self.assertEqual(convert('<p>one<br/>two</p>')[0], 'one\\\ntwo\n')
        self.assertEqual(convert('<p>x<sup>2</sup> <span hidden>gone</span>y</p>')[0], 'x2 y\n')
        self.assertEqual(convert('<p><em>a<span hidden>gone</span></em></p>')[0], '*a*\n')


    def test_math_is_kept_as_tex(self):
        wiki = ('<p>Here <span class="mwe-math-element mwe-math-element-inline"><span style="display: none;">'
                '<math alttext="{\\textstyle s_{t}=\\alpha x_{t}}"><semantics><mi>s</mi></semantics></math></span>'
                '<img class="mwe-math-fallback-image-inline" src="/m.svg" alt="s"></span> holds.</p>'
                '<dl><dd><span class="mwe-math-element mwe-math-element-block"><math alttext="{\\displaystyle\n x^{2}}"></math></span></dd></dl>')
        self.assertEqual(convert(wiki)[0], 'Here $s_{t}=\\alpha x_{t}$ holds.\n\n$$x^{2}$$\n')
        mathml = ('<p><math display="block"><semantics><mi>a</mi><annotation encoding="application/x-tex">a_1</annotation></semantics></math> '
                  '<math><mi>b</mi></math> <span class="mwe-math-element"></span></p>')
        self.assertEqual(convert(mathml)[0], '$$a_1$$ b\n')  # TeX annotation, else its text; an empty holder adds nothing


if __name__ == '__main__':
    unittest.main()
