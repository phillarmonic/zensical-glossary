---
icon: material/book-open-variant
---

# Glossary

This page defines the terms used throughout the documentation. Each entry
below can be referenced automatically: whenever a term appears on another
page, it is underlined, shows this definition on hover, and links back here.

## Zensical

Zensical is a modern static site generator with a Rust core and a Python
Markdown pipeline. It is the successor toolchain to Material for MkDocs.

## Markdown

Markdown is a lightweight plain-text formatting syntax that is converted to
HTML. Zensical extends it through Python-Markdown extensions.

## Extension

An extension is a Python-Markdown plugin that hooks into the rendering
pipeline to transform content, for example to add tooltips or wrap images.

## Treeprocessor

A treeprocessor is an extension component that walks and mutates the parsed
HTML element tree before it is serialized to a string.

## Admonition

An admonition is a callout block (note, warning, tip, and so on) used to
draw attention to a piece of content.

## Front matter

Front matter is the optional YAML metadata block at the top of a Markdown
file, delimited by triple dashes, used to set page options.
