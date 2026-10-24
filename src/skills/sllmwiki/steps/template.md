# template: make or change one of this wiki's narrative templates

A wiki can bring its own templates, for kinds of answers the bundled ones don't fit: a folder in `templates/<name>/` with a `template.md` and a `guide.md`, offered next to the bundled ones; one named like a bundled template replaces it. A wiki that only wants a different length sets `max_words` or `abstract_words` in `Config.toml` instead (`[structural-llm-wiki-templates.<name>]`); do that, and stop here.

## 1. Start from the closest template

From what the owner describes (the questions it answers, its reader, what each answer must contain), pick the closest template in `narrative-format.py --templates`. Then `narrative-format.py --new-template <name> --from <closest>` copies it into `templates/<name>/` for you to change. To change a bundled template for this wiki only, give its own name. Choose a short noun for a new name, such as `postmortem`.

## 2. Shape the template

`template.md` is a header and the body sections; every narrative also gets the shared sections around them (Abstract and Terminology before; the optional Appendix and SMEs, References and Metadata after), so leave those out.

- **Header:** `description`, one line of what the template produces; `use_when`, the questions it fits, with two or three examples in the owner's words, and how it differs from the closest bundled template; `max_words` for the body and `abstract_words`, `[min, max]`.
- **Body:** one `## N. Title` section per part every answer needs, in reading order, each with a `<…>` line saying what goes there. Mark a section a narrative may leave out `(optional)`. Keep a ```` ```mermaid ```` placeholder where a diagram is required.

`guide.md` is how to write it, under exactly these `##` sections: Audience and purpose, Voice and tone, Structure, Evidence, Length, Checklist. Keep what still holds from the template you copied, and change what the owner's description changes. Say each rule once: what every narrative shares stays in `templates/narratives/shared.md` and `shared-guide.md`.

## 3. Check it

`narrative-format.py --templates` must list it with no problem, and `narrative-format.py --skeleton <name>` must show the skeleton you meant. In a wiki whose `language` isn't English, new headings stay English until the wiki's language pack (`templates/languages/<tag>.md`) translates them: say so in the summary.

## 4. Summary

`publish.py summary template --json '{...}'` with:
- `title`: `"Template: <name>"`;
- `checklist`: `"Template <name>: its use_when picks the right questions, and its sections are what every answer needs"`;
- `decisions`: what the description left open, and the choice you made;
- `body`: what it's for, the template it started from, and its sections.

Then `publish.py commit template --subject "Template <name>: <what it's for>"`.
