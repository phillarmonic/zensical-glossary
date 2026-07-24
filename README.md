# zensical-glossary
An enriched glossary extension for the Zensical site generator

Write your terms once on a dedicated glossary page. Everywhere else in the
docs, each term is automatically:

- **underlined**, with a **hover tooltip** showing a short definition, and
- **linked** to its full entry on the glossary page (click to jump).

It is a standard Python-Markdown extension, so it plugs into Zensical's
existing extension pipeline (no theme changes required). The tooltip CSS/JS is
injected automatically into any page that uses at least one term.

## Installation

From this repo (editable, for development):

```bash
uv pip install -e .
```

Or as a normal dependency in your Zensical project:

```bash
uv add zensical-glossary
```

## Usage

1. Create a glossary page at `docs/glossary.md`. Each **heading** (level 2+)
   is a term; the text beneath it is the definition:

   ```markdown
   # Glossary

   ## Zensical

   A modern static site generator with a Rust core and a Python Markdown
   pipeline.

   ## Markdown

   A lightweight plain-text formatting syntax that is converted to HTML.
   ```

2. Enable the extension in `zensical.toml`:

   ```toml
   [project.markdown_extensions.zensical_glossary]
   glossary_file = "glossary.md"
   first_only = true
   ```

3. Build or serve as usual:

   ```bash
   uv run zensical serve
   ```

Any occurrence of "Zensical" or "Markdown" on other pages now gets a tooltip
and links to `/glossary/#zensical` etc. The glossary page itself is never
self-linked.

## Configuration

All options live under `[project.markdown_extensions.zensical_glossary]`.

| Option           | Type   | Default        | Description                                                                 |
| ---------------- | ------ | -------------- | --------------------------------------------------------------------------- |
| `glossary_file`  | str    | `"glossary.md"`| Glossary source, relative to `docs_dir`.                                    |
| `heading_level`  | int    | `2`            | Minimum heading level treated as a term (keeps the page's H1 title out).    |
| `first_only`     | bool   | `true`         | Annotate only the first occurrence of each term per page.                   |
| `case_sensitive` | bool   | `false`        | Match terms case-sensitively.                                               |
| `min_length`     | int    | `2`            | Ignore terms shorter than this.                                             |
| `max_definition` | int    | `280`          | Truncate tooltip text to this many characters.                              |
| `base_url`       | str    | derived        | Override the glossary page URL used in links (e.g. `"/reference/glossary/"`).|
| `language`       | str    | site language  | UI language for tooltip text (`en`, `fr`, `es`, `pt`). Defaults to the site's `language`. |
| `labels`         | table  | `{}`           | Override individual UI strings, e.g. `labels = { more = "…" }`.              |
| `docs_dir`       | str    | `"docs"`       | Fallback docs directory if it cannot be read from Zensical's config.        |

## Internationalization

The plugin localizes its own UI text (currently the tooltip's "read the full
definition" call-to-action). Only the plugin's interface is translated;
glossary content is authored by you.

The language is resolved in this order:

1. The `language` option in the extension config, if set.
2. Zensical's site language (`language = "…"` in `zensical.toml`).
3. Fallback to English.

Region subtags are ignored, so `pt-BR` resolves to `pt`. Supported languages
out of the box: **English (`en`)**, **French (`fr`)**, **Spanish (`es`)**, and
**Portuguese (`pt`)**.

Override a specific string without changing the language via `labels`:

```toml
[project.markdown_extensions.zensical_glossary]
language = "fr"
labels = { more = "Voir la définition complète →" }
```

To add another language, extend `TRANSLATIONS` in
`zensical_glossary/i18n.py` with a new entry keyed by its ISO 639-1 code.

## How it works

- A **treeprocessor** parses the glossary file (cached by path + mtime), then
  walks the rendered element tree and wraps term occurrences in
  `<a class="glossary-term" href="...#slug" data-glossary="...">` anchors. It
  skips code, links, abbreviations, and headings, and never annotates the
  glossary page itself.
- Term anchors reuse the same slugs that the `toc` extension assigns to the
  glossary headings, so clicking lands exactly on the entry.
- A **postprocessor** appends the tooltip CSS/JS to any page that wrapped at
  least one term. The JavaScript positions the tooltip and flips it near the
  viewport edges, and reads its localized labels from a small config object
  injected ahead of it.

## License

MIT
