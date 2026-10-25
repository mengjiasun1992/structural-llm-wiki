# Sphinx settings for a wiki's book (docs/book_design.md §6.4). book.py build
# passes this folder with -c, so no Sphinx file lives in the wiki, and sets
# project, version, release, copyright and language with -D. It runs inside
# Sphinx, which provides docutils.

from docutils import nodes

project = 'book'
version = release = ''
copyright = ''
language = 'en'

extensions = ['myst_parser']
myst_enable_extensions = ['alert']  # GitHub's alerts become admonitions; math is SVG already
root_doc = 'index'
exclude_patterns = ['_build', 'book.json']
suppress_warnings = ['misc.highlighting_failure']  # a block no lexer knows stays plain code

html_theme = 'basic'
html_static_path = ['_static']
html_css_files = ['book.css', 'book-html.css']
html_sidebars = {'**': []}
html_show_sphinx = False
html_show_sourcelink = False
html_copy_source = False
html_use_index = False
html_domain_indices = False

epub_show_urls = 'no'
epub_css_files = ['book.css']  # without book-html.css, which only the one-page HTML and the PDF use
epub_exclude_files = ['_static/book-html.css']  # nor packed: epubcheck reads every stylesheet in the book
epub_tocscope = 'includehidden'  # the toctrees are hidden (the contents are links), but the reader's contents list them
epub_tocdepth = 6  # parts, their sections at any depth, every chapter, and the chapters' own sections


def staged_ids(app, doctree):
    """A section keeps only the id of the label staging gave it (a name with
    "--"), so every id in the single-file book is unique and the contents and
    heading links use it (design §6.4)."""
    for section in doctree.findall(nodes.section):
        staged = {nodes.make_id(n) for n in section['names'] if '--' in n}
        keep = [i for i in section['ids'] if i in staged]
        if keep:
            section['ids'] = keep


def setup(app):
    app.connect('doctree-read', staged_ids, priority=100)
