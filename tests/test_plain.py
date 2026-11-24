"""Tests for lib/plain.py: the plain-sentence warnings narrative-format gives an English narrative
(shared-guide.md, Plain sentences): long sentences, filler phrases and trailing participle clauses."""

import unittest

import helpers  # noqa: F401 (puts the package on the path)
from sllmwiki.lib import plain

LONG = ' '.join(['word'] * 31) + '.'
CASES = (  # (line, the codes it gets)
    (LONG, ['SENTENCE_LONG']),
    (' '.join(['word'] * 30) + '.', []),  # 30 words: at the limit
    (' '.join(['word'] * 20) + '. ' + ' '.join(['word'] * 20) + '.', []),  # two sentences
    (' '.join(['word'] * 20) + '; ' + ' '.join(['word'] * 20) + '.', []),  # a semicolon ends a clause too
    ('- ' + LONG, ['SENTENCE_LONG']),  # a list item is prose
    ('It is important to note that retries wait.', ['SENTENCE_REFERENCE', 'SENTENCE_FILLER']),
    ('Clients back off in order to spread the load.', ['SENTENCE_FILLER']),
    ('When it comes to retries, clients wait.', ['SENTENCE_FILLER']),
    ('Clients wait longer each time, allowing the server to recover.', ['SENTENCE_TRAILING']),
    ('The wait doubles, thereby spreading the load.', ['SENTENCE_TRAILING']),
    ('The wait doubles, resulting in fewer collisions.', ['SENTENCE_TRAILING']),
    ('The wait doubles. The longer wait lets the server recover.', []),
    ('Clients ordered the retries, allowed by the server.', []),  # no trailing participle
    ('See [a long link text that ' + ' '.join(['w'] * 30) + '](../x.md).', ['SENTENCE_LONG']),  # a link's text counts
    ('Waits grow [\\[1\\]](../sources/alpha-doc.md#details).', []),  # a citation doesn't
    ('`' + ' '.join(['code'] * 40) + '`', []),  # a code span is masked
    ('| ' + LONG + ' |', []),  # a table row
    ('> ' + LONG, []),  # a block quote: often a source's words
    ('$$', []),
    ('It balances keys, not traffic.', ['SENTENCE_REFERENCE']),  # "it" with nothing before it
    ('- They combine: a wiki adds search.', ['SENTENCE_REFERENCE']),
    ('- **Modulo hashing is out.** It balances keys.', []),  # the bold lead-in is what "it" names
    ('Itself a ring, the table balances keys.', []),
    ('The ring balances keys. This means hot keys still land on one server.', ['SENTENCE_REFERENCE']),
    ('These are the two knobs.', ['SENTENCE_REFERENCE']),
    ('This ring balances keys.', []),  # "this" with its noun
    ('The state is the only thing stored.', ['SENTENCE_VAGUE']),
    ('Arcs have very different sizes.', ['SENTENCE_VAGUE']),
    ('Retries add a lot of load.', ['SENTENCE_VAGUE']),
    ('The owner makes a decision on each source.', ['SENTENCE_VAGUE']),
    ('The owner decides on each source. Everything else waits.', []),  # "everything" isn't "thing"
    ('Retries wait due to the fact that the server is busy.', ['SENTENCE_FILLER']),
    ('Each and every client waits.', ['SENTENCE_FILLER']),
    ('We think the wait helps.', ['SENTENCE_FILLER']),
    ('This section explains the wait.', ['SENTENCE_FILLER']),
    ('The wait cuts load significantly.', ['SENTENCE_VAGUE']),
    ('The ring was recently redesigned.', ['SENTENCE_VAGUE']),
    ('Experts agree that the wait helps.', ['SENTENCE_UNSOURCED']),
    ('It is widely believed that retries help.', ['SENTENCE_REFERENCE', 'SENTENCE_UNSOURCED']),
    ('Studies show the wait helps.', ['SENTENCE_UNSOURCED']),
    ('The wait cuts load from 120 ms to 80 ms.', []),
    ('The two methods are compared fairly, with respect to x.', []),  # "fairly" and "with respect to" are exact here
    ('Each kind of narrative has a guide.', []),  # "kind of" naming a kind
)


class Plain(unittest.TestCase):
    def codes(self, text, tag='en'):
        return [code for _, code, _, _ in plain.check(text, tag)]

    def test_cases(self):
        for line, codes in CASES:
            with self.subTest(line=line[:50]):
                self.assertEqual(self.codes(f'# Q\n\n{line}\n'), codes)

    def test_where_it_looks(self):
        self.assertEqual(plain.check(f'# Q\n\nShort.\n\n{LONG}\n', 'en')[0][2], 5)  # the line number
        self.assertEqual(self.codes(f'# Q\n\n## 1. Intro\n\n{LONG}\n'), ['SENTENCE_LONG'])
        for section in ('References', 'SMEs', 'Metadata'):
            self.assertEqual(self.codes(f'# Q\n\n## {section}\n\n{LONG}\n'), [], section)
        self.assertEqual(self.codes(f'# Q\n\n## Metadata\n\n{LONG}\n\n## 2. Back\n\n{LONG}\n'), ['SENTENCE_LONG'])
        self.assertEqual(self.codes(f'# Q\n\n```text\n{LONG}\n```\n'), [])  # code
        self.assertEqual(self.codes(f'# {LONG}\n'), [])  # a heading
        self.assertEqual(self.codes(f'# Q\n\n{LONG}\n', 'en-US'), ['SENTENCE_LONG'])
        self.assertEqual(self.codes(f'# Q\n\n{LONG}\n', 'zh-Hans'), [])  # English only

    def test_abbreviations(self):
        cases = (  # (text after the title, the abbreviations reported)
            ('The RTT grows.', ['RTT']),
            ('The round-trip time (RTT) grows. The RTT shrinks.', []),  # spelled out at its first use
            ('The RTT (round-trip time) grows.', []),
            ('The **RTT** (round-trip time) grows.', []),
            ('The RTT grows. The round-trip time (RTT) shrinks.', ['RTT']),  # spelled out too late
            ('The RTTs grow.', ['RTT']),  # a plural
            ('The CPU, the GPU and the HTTP API.', []),  # general computing
            ('Part II and part IV.', []),  # roman numerals
            ('The H100 and NVLink and IPv4.', []),  # names, not abbreviations
            ('Use `RTT` here.', []),  # code
            ('| RTT | the time |', []),  # a table
            ('## Terminology\n\n- **RTT:** the round-trip time.\n\n## 2. Body\n\nThe RTT grows.', ['RTT']),  # Terminology doesn't count
        )
        for body, words in cases:
            with self.subTest(body=body[:40]):
                found = [m.split('"')[1] for _, code, _, m in plain.check(f'# Q\n\n{body}\n', 'en') if code == 'ABBREV_UNDEFINED']
                self.assertEqual(found, words)
        title = '# What is a round-trip time (RTT)?\n\nThe RTT grows.\n'
        self.assertEqual(self.codes(title), [])  # the title spelled it out
        self.assertEqual(self.codes('# What is an RTT?\n\nThe RTT grows.\n'), ['ABBREV_UNDEFINED'])

    def test_passive_share(self):
        active, passive = 'The server sends the reply.', 'The reply is sent by the server.'
        self.assertEqual(self.codes('# Q\n\n' + '\n\n'.join([active] * 17 + [passive] * 3) + '\n'), [])  # 15%: at the limit
        found = plain.check('# Q\n\n' + '\n\n'.join([active] * 16 + [passive] * 4) + '\n', 'en')
        self.assertEqual([f[1] for f in found], ['PASSIVE_SHARE'])
        self.assertEqual(found[0][2], 35)  # the first passive sentence
        self.assertIn('4 of 20 sentences (20%)', found[0][3])
        self.assertEqual(self.codes('# Q\n\n' + '\n\n'.join([passive] * 19) + '\n'), [])  # too few to judge
        for line in ('The keys were chosen at random.', 'The tables are built once.', 'It was not written down.'):
            self.assertTrue(plain.PASSIVE.search(line), line)
        for line in ('The server is ready.', 'The reply is late.', 'They were in the queue.'):
            self.assertFalse(plain.PASSIVE.search(line), line)


if __name__ == '__main__':
    unittest.main()
