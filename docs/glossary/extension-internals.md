---
icon: lucide/cog
---

# Extension internals

Terms about how the extension plugs into the Python-Markdown pipeline.

### Extension

An extension is a Python-Markdown plugin that hooks into the rendering pipeline
to transform content, add syntax, or inject supporting assets.

### Treeprocessor

A treeprocessor walks and mutates the parsed HTML element tree before the page
is serialized to a string.

### Postprocessor

A postprocessor runs after Markdown serialization and can append or rewrite the
final HTML string.
