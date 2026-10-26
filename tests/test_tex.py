"""Tests for lib/tex.py."""

import unittest

import helpers  # noqa: F401  (puts scripts/ on the path)
from lib import tex

DOC = r'''\documentclass{article}
\newcommand{\foo}{bar}
\title{Retry \emph{Budgets}}
\author{Someone\thanks{Somewhere}}
\begin{document}
\maketitle
\begin{abstract}
Retries, bounded. % a comment
\end{abstract}
\section{Introduction}\label{sec:intro}
A retry budget~\cite{aws,sre} caps retries at 10\% of requests---see Section~\ref{sec:how} and \cite[p.~3]{beyer}.
It is \textbf{simple}, \texttt{cheap} and \url{https://example.com}; \href{https://a.example}{a link}\footnote{A note.}.
``Quoted'' text \LaTeX{} \ldots{} \unknown{kept text}.
\subsection*{How it works}\label{sec:how}
The rate is $r = \frac{b}{n}$ and \(x_t\) too; a dollar \$5.
\[ y = 2x \]
\begin{equation}\label{eq:one}
  E = mc^2
\end{equation}
$$a+b$$
\begin{itemize}
  \item First, with $math$
  \item[Second] labeled
  \begin{enumerate}
    \item nested one
    \item nested two
  \end{enumerate}
\end{itemize}
\begin{description}
  \item[Term] its meaning
\end{description}
\begin{verbatim}
  if retries > budget: stop()   % not a comment
\end{verbatim}
Inline \verb|code_here| works.
\begin{table}[h]
\centering
\begin{tabular}{l|r}
\hline
Name & Value \\ \hline
a \& b & 1 \\
c & 2 | 3 \\[2pt]
\end{tabular}
\caption{Results}
\end{table}
\begin{quote}
Quoted
block.
\end{quote}
\begin{theorem}[Safety]
Nothing bad.
\end{theorem}
\begin{proof}
Obvious.
\end{proof}
\begin{center}Centered\end{center} and a stray } brace.
\paragraph{Run-in} heading.
#hash line
\begin{thebibliography}{9}
\bibitem{aws} Amazon.
\end{thebibliography}
\end{document}
ignored after the end
'''


class Convert(unittest.TestCase):
    def setUp(self):
        self.out = tex.convert(DOC)

    def test_title_sections_and_abstract(self):
        self.assertTrue(self.out.startswith('# Retry *Budgets*\n\n## Abstract\n\nRetries, bounded.\n\n## Introduction\n\n'))
        self.assertIn('\n### How it works\n', self.out)
        self.assertNotIn('ignored after the end', self.out)
        self.assertNotIn('Someone', self.out)

    def test_text_formatting_citations_and_symbols(self):
        self.assertIn('A retry budget [aws, sre] caps retries at 10% of requests—see Section sec:how and [beyer, p. 3].', self.out)
        self.assertIn('It is **simple**, `cheap` and <https://example.com>; [a link](https://a.example) (Footnote: A note.).', self.out)
        self.assertIn('“Quoted” text LaTeX … kept text.', self.out)
        self.assertIn('Centered and a stray brace.\n**Run-in** heading.\n\\#hash line\n', self.out)

    def test_math_is_kept_as_tex(self):
        self.assertIn('The rate is $r = \\frac{b}{n}$ and $x_t$ too; a dollar $5.', self.out)
        self.assertIn('\n$$\ny = 2x\n$$\n\n$$\nE = mc^2\n$$\n\n$$\na+b\n$$\n', self.out)

    def test_lists(self):
        self.assertIn('- First, with $math$\n- **Second** labeled\n\n   1. nested one\n   2. nested two', self.out)
        self.assertIn('- **Term** its meaning', self.out)
        self.assertIn('- [aws] Amazon.', self.out)

    def test_code_tables_quotes_and_theorems(self):
        self.assertIn('```\n  if retries > budget: stop()   % not a comment\n```', self.out)
        self.assertIn('Inline `code_here` works.', self.out)
        self.assertIn('| Name | Value |\n|---|---|\n| a & b | 1 |\n| c | 2 \\| 3 |\n\nCaption: Results', self.out)
        self.assertIn('> Quoted\n> block.', self.out)
        self.assertIn('**Theorem (Safety).** Nothing bad.', self.out)
        self.assertIn('**Proof.** Obvious.', self.out)

    def test_inputs_without_a_document(self):
        files = {'chap': r'\chapter{One}Text of one.\input{deeper}', 'deeper': 'Deeper.'}
        out = tex.convert(r'\input{chap} \include{missing} \section{Two} \begin{tabular}{l}\end{tabular} \begin{itemize', files.get)
        self.assertEqual(out, '## One\n\nText of one.Deeper.\n\n### Two\n')
        self.assertEqual(tex.convert(r'\input{x}'), '\n')  # nothing to read it from
        self.assertEqual(tex.convert(r'\section{Unclosed'), '## Unclosed\n')
        self.assertEqual(tex.convert(r'\textbf'), '****\n')


if __name__ == '__main__':
    unittest.main()
