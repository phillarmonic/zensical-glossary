# zensical-glossary

[![PyPI version](https://img.shields.io/pypi/v/zensical-glossary)](https://pypi.org/project/zensical-glossary/)
[![Python versions](https://img.shields.io/pypi/pyversions/zensical-glossary)](https://pypi.org/project/zensical-glossary/)
[![License](https://img.shields.io/pypi/l/zensical-glossary)](https://github.com/phillarmonic/zensical-glossary/blob/master/LICENSE)
[![Documentation](https://img.shields.io/badge/docs-phillarmonic.github.io-blue)](https://phillarmonic.github.io/zensical-glossary/)

Add hover tooltips and glossary links to a Zensical site from one or more Markdown glossary pages.

Write your terms once in `docs/glossary.md` — spread them across several
domain-focused pages, or define them inline on any page with a comment marker.
Everywhere else in your docs, matching words are automatically underlined,
show a short definition on hover, and link back to the full definition.

## Why Use It

- Keep terminology consistent and easily accessible across docs.
- Give readers quick definitions without interrupting the page.
- Link every term back to a canonical glossary entry.
- Organize large glossaries into sections without turning section headings into terms.
- Spread terms across several glossary pages, organized by domain, and have them merged at build time.
- Define terms inline on any page with a comment marker — no glossary file maintenance.
- Use normal Python-Markdown and Zensical configuration.

## Origin

This extension has its origin in the necessity of generating richer documentation for the POG Programming Language (still to be released). As the language has too many domain specific terms, it is better to have them at hand instead of jumping back-and-forth between a glossary and the page the reader is currently at.

We've decided to publish it before POG, since it has been proven extremely useful in our internal documentations.

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
terms with a tooltip and a link to `/glossary/#zensical` or `/glossary/#markdown`.

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

## Multiple Glossary Pages

For bigger knowledge bases, spread terms across several pages — for example one
page per domain — and list them with `glossary_files`:

```toml
[project.markdown_extensions.zensical_glossary]
glossary_files = [
  "glossary/core.md",
  "glossary/api.md",
]
heading_level = 3
```

Entries may also be glob patterns, expanded against `docs_dir` and sorted for
deterministic builds:

```toml
glossary_files = ["glossary/**/*.md"]
```

All files are merged into a single term index at build time:

- Files are processed in configuration order. If two pages define the same
  term, the first file wins.
- Each term links to the page that defines it, e.g. `/glossary/api/#widget`.
- Every glossary source page is skipped during annotation, so glossary pages
  never link to themselves.
- Parsed pages are cached by modification time, and the merged index and term
  regex are built once per build, so watch-mode rebuilds stay fast.

`glossary_files` takes precedence over `glossary_file` when both are set, so a
single-page setup keeps working unchanged.

## Inline Definitions

For terms that are best explained where they are used, skip glossary files
entirely and mark a definition directly on any regular page:

```markdown
<!-- zensical-glossary: Widget -->

A widget is a reusable UI unit that...
```

The paragraphs after the marker — up to the next heading or the next marker —
become the definition. The marker renders as an invisible anchor
(`#widget`), and every other mention of the term on the site links to it.

Enable the mode with:

```toml
[project.markdown_extensions.zensical_glossary]
inline_definitions = true
```

All pages are scanned once per build (cached by modification time) and merged
with any glossary files into a single index — a hybrid glossary. When a term
is defined both inline and in a glossary file, the glossary file wins. A page
never links to the terms it defines itself.

## Configuration

All options live under `[project.markdown_extensions.zensical_glossary]`.

| Option                | Type  | Default         | Description                                                               |
| --------------------- | ----- | --------------- | ------------------------------------------------------------------------- |
| `glossary_file`       | str   | `"glossary.md"` | Glossary source, relative to `docs_dir`.                                  |
| `glossary_files`      | list  | `[]`            | Multiple glossary sources (paths or globs). Wins over `glossary_file`.    |
| `inline_definitions`  | bool  | `false`         | Scan all pages for `<!-- zensical-glossary: Term -->` definitions.        |
| `heading_level`       | int   | `2`             | Exact heading level treated as terms; shallower headings can be sections. |
| `first_only`          | bool  | `true`          | Annotate only the first occurrence of each term per page.                 |
| `case_sensitive`      | bool  | `false`         | Match terms case-sensitively.                                             |
| `min_length`          | int   | `2`             | Ignore terms shorter than this.                                           |
| `max_definition`      | int   | `280`           | Truncate tooltip text to this many characters.                            |
| `base_url`            | str   | derived         | Single file: override the glossary URL. Multiple files: URL prefix.       |
| `language`            | str   | site language   | UI language for tooltip text: `en`, `fr`, `es`, `pt`.                     |
| `labels`              | table | `{}`            | Override UI strings, e.g. `labels = { more = "Read more" }`.              |
| `docs_dir`            | str   | `"docs"`        | Fallback docs directory if it cannot be read from Zensical config.        |

For GitHub Pages project sites, set `base_url` when your site is served from a
repository subpath. With a single glossary file it is the full glossary URL;
with `glossary_files` it is a prefix joined with each derived page URL:

```toml
[project.markdown_extensions.zensical_glossary]
# Single file:
base_url = "https://OWNER.github.io/REPOSITORY/glossary/"

# Multiple files (terms link to https://OWNER.github.io/REPOSITORY/glossary/api/#term):
glossary_files = ["glossary/*.md"]
base_url = "https://OWNER.github.io/REPOSITORY"
```

## Example Project

This repository includes a complete Zensical example in `docs/`. It is the same
site that can be published with the included GitHub Pages workflow.

```bash
uv run zensical serve
uv run zensical build --clean
```

The workflow at `.github/workflows/docs.yml` builds `site/` and deploys it to
GitHub Pages on pushes to `master`.

## Local Development

This repository uses the [drun automation language](https://github.com/phillarmonic/drun) for local automation. 

Use `xdrun --list` to see the available tasks.

```bash
xdrun test
xdrun build
xdrun rebuild
# xdrun ci is optimized for LLMs and MCPs, it only generates
# verbose output in the case an error is thrown. Saves input tokens.
xdrun ci
# For seeing everything the CI is outputting, use:
xdrun ci --task-mode normal
```

- `test` runs the Python test suite.
- `build` creates package artifacts and builds the example site.
- `rebuild` removes generated outputs first, then builds everything again.
- `ci` runs the full local verification lifecycle, including package
  metadata checks.

GitHub Actions runs the same `xdrun ci` pipeline in
`.github/workflows/ci.yml` for pull requests and pushes.

### Releasing

Releases are prepared with:

```bash
xdrun prepare-release version=X.Y.Z
```

This checks that the version is newer than the latest release, runs the full
CI pipeline, promotes the unreleased changelog entries to the new version,
syncs the version across the drun spec, `pyproject.toml`, and the package,
and rebuilds the distribution artifacts. After reviewing the changes, commit,
tag `vX.Y.Z`, and push the tag — the workflow at
`.github/workflows/release.yml` builds and publishes to PyPI.

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

The extension parses the glossary files and scans pages for inline definition
markers, merges everything into one term index, and uses a treeprocessor to
wrap matching text in rendered pages. Each term links to the page that defines
it. It skips code, links, abbreviations, headings, the glossary pages
themselves, and each term's own defining page. A postprocessor injects the
tooltip CSS and JavaScript only on pages where at least one term was found.
Source files are cached by modification time, so unchanged content is never
re-parsed during a build or watch session.

## License

MIT
