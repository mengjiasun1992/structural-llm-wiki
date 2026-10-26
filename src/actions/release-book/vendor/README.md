# Vendored libraries

The release action draws a book's diagrams and math with these files, in
headless Chrome, so a build fetches nothing (docs/book_design.md §6.3). They
are pinned to the versions GitHub renders with, so what GitHub draws in review
is what the book draws.

| File | Library | Version | License | SHA-256 |
|---|---|---|---|---|
| `mermaid.min.1.js`, `mermaid.min.2.js` | [mermaid](https://github.com/mermaid-js/mermaid) (`dist/mermaid.min.js`) | 12.2.0, GitHub's in October 2026 | MIT, [LICENSE-mermaid](LICENSE-mermaid); the bundled libraries keep their own notices in the file. Kept in two plain-text halves, cut at a line break: the plugin directory takes no file over 5 MiB and its scan reads only plain text; `book.py` joins them once into a temporary folder, and the SHA-256 is the joined file's | `a8a6a6f805b074a8261a2825c86f99c8054acb3b35f50bb7e24a4f9f2c3c3b9f` |
| `tex-svg-full.js` | [MathJax](https://github.com/mathjax/MathJax) (`es5/tex-svg-full.js`) | 3.2.2 | Apache-2.0, [LICENSE-mathjax](LICENSE-mathjax) | `a4354ff94fd868aea0cc6eaaa79a57fda0588646fc46ee3700a349ee0a11cbe6` |

## Updating

Check the version GitHub uses first: its mermaid viewer names it in
`renderer.draw(…, "<version>", …)`. Then, from the repository's root:

```bash
npm pack mermaid@12.2.0 mathjax@3.2.2
tar xzf mermaid-12.2.0.tgz package/dist/mermaid.min.js package/LICENSE \
  && mv package/dist/mermaid.min.js src/actions/release-book/vendor/ && mv package/LICENSE src/actions/release-book/vendor/LICENSE-mermaid
tar xzf mathjax-3.2.2.tgz package/es5/tex-svg-full.js package/LICENSE \
  && mv package/es5/tex-svg-full.js src/actions/release-book/vendor/ && mv package/LICENSE src/actions/release-book/vendor/LICENSE-mathjax
rm -r package mermaid-12.2.0.tgz mathjax-3.2.2.tgz
shasum -a 256 src/actions/release-book/vendor/*.js
python3 src/actions/release-book/vendor/split.py
```

Update the table, and `docs/book_execution_plan.md` §5, in the same pull
request; the check-book workflow builds the fixture book with the new files.
