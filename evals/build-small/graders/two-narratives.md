---
type: regex
target:
  source: file
  path: sllmwiki/narratives/manifest.yaml
pattern: '(retry-budget|jitter)[\s\S]*\n[a-z0-9-]*(jitter|retry-budget)[a-z0-9-]*:'
---

Each question gets a narrative in the manifest.
