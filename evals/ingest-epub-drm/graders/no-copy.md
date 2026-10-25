---
type: regex
target:
  source: file
  path: sllmwiki/sources/manifest.yaml
pattern: 'alpha-patterns:\n(?:  .*\n)*?  file:'
match: not_contains
---

No copy of the book is saved: its entry has no file.
