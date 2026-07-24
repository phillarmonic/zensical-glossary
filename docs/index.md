---
icon: lucide/book-open-check
---

# zensical-glossary

`zensical-glossary` turns a dedicated glossary page into inline definitions
across a Zensical site. Hover terms like Zensical, Markdown, treeprocessor, or
front matter to see a short definition without leaving the page.

Click a glossary term to jump to its full entry. The tooltip's read-more link is
interactive too, so readers can move from a term to the definition even when the
tooltip appears away from the source text.

## What it adds

- Automatic tooltip definitions for known terms.
- Links from each term occurrence to its glossary entry.
- Optional `first_only` behavior for quieter pages.
- Sectioned glossaries where `##` headings organize terms and `###` headings
  define terms.
- Localized tooltip UI labels.

!!! note "Try the glossary in rich content"

    A glossary term still works inside an admonition. This paragraph mentions
    Markdown, Extension, and Admonition so the example shows how normal page
    content is annotated after Python-Markdown renders it.

??? info "It also works in collapsible details"

    Details blocks are just rendered elements in the Markdown tree, so terms
    like tooltip and glossary entry can be annotated here too.

## Install

Install the extension in your Zensical project:

```bash
uv add zensical-glossary
```

Or use pip:

```bash
pip install zensical-glossary
```

## Configure

Enable the Markdown extension in `zensical.toml`:

```toml
[project.markdown_extensions.zensical_glossary]
glossary_file = "glossary.md"
heading_level = 3
first_only = true
```

The demo site uses `heading_level = 3`, which lets `##` headings act as
glossary sections while each `###` heading becomes a term.

Because this example is published as a GitHub Pages project site, it also sets
`base_url` to the published glossary URL so links work under the repository
subpath.

## Author terms

Create `docs/glossary.md`:

```markdown
# Glossary

## Concepts

### Glossary entry

A glossary entry is a heading and definition pair in the glossary source file.

### Tooltip

A tooltip is the compact definition shown when a reader hovers a term.
```

Then use those words naturally in your docs. The extension handles the links and
tooltip text at build time.

## Publish

This repository includes a GitHub Pages workflow. On pushes to `main` or
`master`, GitHub Actions installs the local package, builds the Zensical site,
uploads `site/`, and deploys it to Pages.

In the repository settings, set Pages to use GitHub Actions as the source.
