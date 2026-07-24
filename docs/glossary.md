---
icon: material/book-open-variant
---

# Glossary

This glossary powers the examples on this site. The `##` headings are sections;
the `###` headings are terms because the demo config sets `heading_level = 3`.

## Zensical basics

### Zensical

Zensical is a modern static site generator with a Rust core and a Python
Markdown pipeline.

### Markdown

Markdown is a lightweight plain-text formatting syntax that is converted to
HTML. Zensical extends it through Python-Markdown extensions.

### Front matter

Front matter is optional metadata at the top of a Markdown file, usually
delimited by triple dashes, that sets page-level options.

## Extension internals

### Extension

An extension is a Python-Markdown plugin that hooks into the rendering pipeline
to transform content, add syntax, or inject supporting assets.

### Treeprocessor

A treeprocessor walks and mutates the parsed HTML element tree before the page
is serialized to a string.

### Postprocessor

A postprocessor runs after Markdown serialization and can append or rewrite the
final HTML string.

## Reader experience

### Glossary entry

A glossary entry is a term and definition pair in the glossary source file.
Each entry gets an anchor that other pages can link to.

### Tooltip

A tooltip is the compact definition shown when a reader hovers or focuses a
glossary term.

### Admonition

An admonition is a callout block, such as a note, warning, or tip, used to draw
attention to a piece of content.

### Sectioned glossary

A sectioned glossary uses shallower headings to organize related terms while a
configured heading level identifies the terms themselves.
