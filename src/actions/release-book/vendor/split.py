"""Cut mermaid.min.js into two plain-text halves at a line break (README.md, "Updating")."""
import os

here = os.path.dirname(os.path.abspath(__file__))
whole = os.path.join(here, 'mermaid.min.js')
with open(whole, 'rb') as f:
    data = f.read()
cut = data.find(b'\n', len(data) // 2) + 1
for n, part in ((1, data[:cut]), (2, data[cut:])):
    with open(os.path.join(here, f'mermaid.min.{n}.js'), 'wb') as f:
        f.write(part)
os.remove(whole)
