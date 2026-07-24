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

Most sites can let the extension derive the glossary URL from
`glossary_file`. If your glossary lives behind a custom route, set `base_url`:

```toml
[project.markdown_extensions.zensical_glossary]
base_url = "/reference/glossary/"
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
headings, and the glossary page itself.
