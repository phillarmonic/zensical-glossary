---
icon: lucide/settings-2
---

# Usage guide

This page shows the common decisions you make when adding a glossary to a
Zensical project.

## Choose a glossary shape

For a short glossary, use one heading per term:

```markdown
# Glossary

## Tooltip

A tooltip is a compact definition shown near a term.
```

For a larger glossary, group terms into sections:

```markdown
# Glossary

## Reader experience

### Tooltip

A tooltip is a compact definition shown near a term.

### Glossary entry

A glossary entry is a term and definition pair.
```

Set `heading_level = 3` when terms live at `###`.

## Spread the glossary across pages

When one page gets too long, split the glossary by domain and list every
source with `glossary_files`:

```toml
[project.markdown_extensions.zensical_glossary]
glossary_files = [
  "glossary/core.md",
  "glossary/api.md",
]
heading_level = 3
```

Glob patterns are expanded against `docs_dir` and sorted, so a whole directory
of domain pages can be loaded at once:

```toml
glossary_files = ["glossary/**/*.md"]
```

The files are merged into a single index at build time. Each term links to the
page that defines it, and if two pages define the same term, the file listed
first wins. Unchanged files are never re-parsed, so watch-mode rebuilds stay
fast.

This site is an example: its glossary lives in three pages under `glossary/`,
loaded with `glossary_files = ["glossary/*.md"]`.

## Define terms inline

Dedicated glossary pages are not the only option. When a term is best
explained where it is used, mark a definition directly on any regular page
with an HTML comment:

```markdown
<!-- zensical-glossary: Term -->
```

The paragraphs after the marker — up to the next heading or the next marker —
become the definition. The marker itself renders as an invisible anchor, so
every other mention of the term on the site links straight to that spot.

Enable the mode and every page is scanned once per build:

```toml
[project.markdown_extensions.zensical_glossary]
inline_definitions = true
```

<!-- zensical-glossary: Hybrid glossary -->

A hybrid glossary combines curated glossary files with inline definitions on
regular pages. Both modes feed the same term index, and when a term is
defined in both places, the glossary file wins — files stay the curated
canonical source, inline markers are the lightweight fallback.

This page uses exactly that setup: the term "hybrid glossary" is defined by
the marker above, and mentions of it on other pages link back here.

A page never links to the terms it defines itself, and unchanged pages are
never re-scanned, so watch-mode rebuilds stay fast.

## Add aliases to a term

Prose rarely uses the exact glossary wording. Add an alias marker inside a
term's definition block — right after the heading in a glossary file, or
after the definition marker in inline mode — and every comma-separated alias
also matches in prose, showing the canonical definition and linking to the
canonical anchor:

```markdown
### Passivo
<!-- zensical-glossary-aliases: passivos, elemento passivo -->

Um elemento passivo é um componente de rede que...
```

```markdown
<!-- zensical-glossary: Widget -->
<!-- zensical-glossary-aliases: gadget, widgets -->

A widget is a reusable unit that...
```

The marker renders as an invisible HTML comment and never appears in the
tooltip. Matching follows the same rules as terms: case-insensitive by
default, longest surface first (a multi-word alias beats a shorter term), and
`first_only` counts the term and its aliases as one entry. If an alias
collides with another term or alias, the definition that comes first wins —
a real term always beats an alias.

## Decide how often to link

Use `first_only = true` when you want each term annotated once per page:

```toml
[project.markdown_extensions.zensical_glossary]
first_only = true
```

Use `first_only = false` for demos, reference pages, or teaching material where
every occurrence should be visible:

```toml
[project.markdown_extensions.zensical_glossary]
first_only = false
```

## Tune definitions

The tooltip uses plain text extracted from the glossary entry. Keep the first
paragraph short and useful, then add more detail below it on the glossary page.

```toml
[project.markdown_extensions.zensical_glossary]
max_definition = 220
```

## Override the link target

Most sites can let the extension derive glossary URLs from the configured
source files. If your glossary lives behind a custom route, set `base_url`.

With a single `glossary_file`, `base_url` is the full glossary URL:

```toml
[project.markdown_extensions.zensical_glossary]
base_url = "/reference/glossary/"
```

With `glossary_files`, `base_url` is a prefix joined with each derived page
URL, so every term still links to the page that defines it:

```toml
[project.markdown_extensions.zensical_glossary]
glossary_files = ["glossary/*.md"]
base_url = "https://example.com/docs"
# "Widget" defined in glossary/api.md links to:
# https://example.com/docs/glossary/api/#widget
```

## Localize the tooltip action

The tooltip UI follows the Zensical site language when possible:

```toml
[project.theme]
language = "pt"
```

You can also override the label directly:

```toml
[project.markdown_extensions.zensical_glossary]
labels = { more = "Read the full entry" }
```

## Know what is skipped

The treeprocessor avoids places where automatic links are usually surprising:
code, preformatted blocks, existing links, abbreviations, script/style tags,
headings, and the glossary pages themselves.
