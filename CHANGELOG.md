# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Term aliases via the `<!-- zensical-glossary-aliases: ... -->` comment marker, in glossary files and inline definitions alike: each comma-separated alias matches in prose and links back to the canonical term, with first-wins collision handling (a real term always beats an alias) and longest-surface-first matching.

## [1.0.0] - 2026-08-12

### Added

- Hover tooltips with a short definition for every annotated term, linking back to its canonical glossary entry.
- Single-page glossaries via `glossary_file` and multi-page glossaries via `glossary_files` (paths or glob patterns), merged into one term index at build time; the first definition of a term wins.
- Inline term definitions on any page with the `<!-- zensical-glossary: Term -->` comment marker, merged with glossary files into a hybrid index.
- Configurable term parsing and annotation: `heading_level`, `case_sensitive`, `min_length`, `first_only`, `max_definition`, and `base_url` overrides for project sites served from a subpath.
- Localized tooltip UI for English, French, Spanish, and Portuguese, resolved from the extension or site language, with per-label overrides.
- Tooltip CSS and JavaScript injected only on pages where at least one term is annotated; code, links, abbreviations, headings, glossary pages, and each term's own defining page are never annotated.
- Modification-time caching of glossary sources and page scans so watch-mode rebuilds stay fast.
