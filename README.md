# zensical-glossary

Add hover tooltips and glossary links to a Zensical site from one Markdown
glossary page.

Write your terms once in `docs/glossary.md`. Everywhere else in your docs,
matching words are automatically underlined, show a short definition on hover,
and link back to the full glossary entry.

## Why Use It

- Keep terminology consistent across docs.
- Give readers quick definitions without interrupting the page.
- Link every term back to a canonical glossary entry.
- Organize large glossaries into sections without turning section headings into
  terms.
- Use normal Python-Markdown and Zensical configuration.

## Install

In a Zensical project:

```bash
uv add zensical-glossary
```

Or with pip:

```bash
pip install zensical-glossary
```

For local development in this repository:

```bash
uv pip install -e .
```

## Quick Start

Create `docs/glossary.md`:

```markdown
# Glossary

## Core concepts

### Zensical

Zensical is a modern static site generator with a Rust core and a Python
Markdown pipeline.

### Markdown

Markdown is a lightweight plain-text formatting syntax that is converted to
HTML.
```

Enable the extension in `zensical.toml`:

```toml
[project.markdown_extensions.zensical_glossary]
glossary_file = "glossary.md"
heading_level = 3
first_only = true
```

Now any page can simply mention Zensical or Markdown. The extension wraps those
terms with a tooltip and a link to `/glossary/#zensical` or
`/glossary/#markdown`.

Run the site:

```bash
uv run zensical serve
```

Build it:

```bash
uv run zensical build --clean
```

## Glossary Format

By default, `heading_level = 2`, so every `## Term` in the glossary file is a
term.

For larger glossaries, use shallower headings for sections and set
`heading_level` to the exact level that contains terms:

```markdown
# Glossary

## Authoring

### Admonition

An admonition is a callout block such as a note, warning, or tip.

### Front matter

Front matter is metadata at the top of a Markdown file.
```

```toml
[project.markdown_extensions.zensical_glossary]
heading_level = 3
```

Deeper headings remain part of the current term definition instead of becoming
separate glossary entries.

## Configuration

All options live under `[project.markdown_extensions.zensical_glossary]`.

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `glossary_file` | str | `"glossary.md"` | Glossary source, relative to `docs_dir`. |
| `heading_level` | int | `2` | Exact heading level treated as terms; shallower headings can be sections. |
| `first_only` | bool | `true` | Annotate only the first occurrence of each term per page. |
| `case_sensitive` | bool | `false` | Match terms case-sensitively. |
| `min_length` | int | `2` | Ignore terms shorter than this. |
| `max_definition` | int | `280` | Truncate tooltip text to this many characters. |
| `base_url` | str | derived | Override the glossary page URL used in links. |
| `language` | str | site language | UI language for tooltip text: `en`, `fr`, `es`, `pt`. |
| `labels` | table | `{}` | Override UI strings, e.g. `labels = { more = "Read more" }`. |
| `docs_dir` | str | `"docs"` | Fallback docs directory if it cannot be read from Zensical config. |

For GitHub Pages project sites, set `base_url` when your site is served from a
repository subpath:

```toml
[project.markdown_extensions.zensical_glossary]
base_url = "https://OWNER.github.io/REPOSITORY/glossary/"
```

## Example Project

This repository includes a complete Zensical example in `docs/`. It is the same
site that can be published with the included GitHub Pages workflow.

```bash
uv run zensical serve
uv run zensical build --clean
```

The workflow at `.github/workflows/docs.yml` builds `site/` and deploys it to
GitHub Pages on pushes to `main` or `master`.

## Local Development

This repository uses drun for local automation. Use `xdrun --list` to see the
available tasks.

```bash
xdrun test
xdrun build
xdrun rebuild
xdrun ci
```

- `test` runs the Python test suite.
- `build` creates package artifacts and builds the example site.
- `rebuild` removes generated outputs first, then builds everything again.
- `ci` runs the full local verification lifecycle, including package
  metadata checks.

GitHub Actions runs the same `xdrun ci` pipeline in
`.github/workflows/ci.yml` for pull requests and pushes.

## Internationalization

The tooltip UI text is localized separately from your glossary content. The
language is resolved in this order:

1. The extension's `language` option.
2. The Zensical site language.
3. English.

Supported built-in languages are English (`en`), French (`fr`), Spanish (`es`),
and Portuguese (`pt`). Region subtags are ignored, so `pt-BR` resolves to `pt`.

Override a label directly:

```toml
[project.markdown_extensions.zensical_glossary]
language = "fr"
labels = { more = "Voir la definition complete" }
```

## How It Works

The extension parses the glossary file, builds a term index, and uses a
treeprocessor to wrap matching text in rendered pages. It skips code, links,
abbreviations, headings, and the glossary page itself. A postprocessor injects
the tooltip CSS and JavaScript only on pages where at least one term was found.

## License

MIT
