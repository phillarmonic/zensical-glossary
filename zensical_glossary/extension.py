# Copyright (c) 2026 phillarmonic and contributors
# SPDX-License-Identifier: MIT

"""A Zensical / Python-Markdown extension that turns dedicated glossary
pages and inline definition markers into hover tooltips and cross-links
throughout the rest of the site."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar
from xml.etree.ElementTree import Element

from markdown import Extension, Markdown
from markdown.extensions.toc import slugify
from markdown.postprocessors import Postprocessor
from markdown.treeprocessors import Treeprocessor

from zensical_glossary.assets import CSS, render_js
from zensical_glossary.i18n import resolve_labels

if TYPE_CHECKING:
    from pathlib import Path

try:
    from zensical.extensions.context import ContextPreprocessor
except ImportError:  # pragma: no cover - zensical not installed / API changed
    ContextPreprocessor = None  # type: ignore[assignment,misc]


# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------


SKIP_TAGS: frozenset[str] = frozenset(
    {
        "a",
        "abbr",
        "code",
        "pre",
        "script",
        "style",
        "kbd",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    }
)

_FRONT_MATTER_RE = re.compile(r"^-{3}.*?\n-{3}\s*\n", re.DOTALL)
_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*\s*$", re.MULTILINE)

# Inline definition marker: <!-- zensical-glossary: Term --> on any page.
# The paragraphs after it (up to the next heading or marker) are the
# definition, and the page becomes the link target for that term.
_INLINE_MARKER_RE = re.compile(r"<!--\s*zensical-glossary:\s*(.+?)\s*-->")

# Lightweight Markdown -> plain text cleanup for tooltip text.
_CLEAN_STEPS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"!\[[^\]]*\]\([^)]*\)"), ""),
    (re.compile(r"\[([^\]]+)\]\([^)]*\)"), r"\1"),
    (re.compile(r"\[([^\]]+)\]\[[^\]]*\]"), r"\1"),
    (re.compile(r"`([^`]*)`"), r"\1"),
    (re.compile(r"(\*\*|__|~~|==|\^\^|\*|_)"), ""),
    (re.compile(r"\s+"), " "),
)


# ----------------------------------------------------------------------------
# Store
# ----------------------------------------------------------------------------


class GlossaryEntry:
    """A single glossary term with its definition and anchor slug."""

    __slots__ = ("definition", "origin", "page", "slug", "term")

    def __init__(
        self,
        term: str,
        definition: str,
        slug: str,
        page: str = "",
        origin: str = "file",
    ) -> None:
        self.term = term
        self.definition = definition
        self.slug = slug
        # Docs-relative path of the page that defines this term.
        self.page = page
        # "file" (glossary source page) or "inline" (comment marker).
        self.origin = origin


class GlossaryStore:
    """Parses, merges, and caches glossary sources (by path and mtime)."""

    # Merged stores keyed on a snapshot of every contributing file.
    _cache: ClassVar[dict[tuple[Any, ...], GlossaryStore]] = {}
    # Per-file parse results, so unchanged files are never re-parsed.
    _parsed: ClassVar[dict[tuple[Any, ...], list[GlossaryEntry]]] = {}

    def __init__(self, entries: list[GlossaryEntry]) -> None:
        self.entries = entries
        # Map lowercase term -> entry for lookups, longest terms first so a
        # multi-word term wins over a shorter substring term.
        self._by_lower: dict[str, GlossaryEntry] = {
            e.term.lower(): e for e in entries
        }
        self._patterns: dict[bool, re.Pattern[str] | None] = {}

    @classmethod
    def clear_cache(cls) -> None:
        cls._cache.clear()
        cls._parsed.clear()

    @classmethod
    def load(
        cls,
        path: Path,
        *,
        min_length: int,
        max_definition: int,
        heading_level: int,
    ) -> GlossaryStore:
        """Load a single glossary file (convenience wrapper for load_multi)."""
        return cls.load_multi(
            [(path, path.name)],
            min_length=min_length,
            max_definition=max_definition,
            heading_level=heading_level,
        )

    @classmethod
    def load_multi(
        cls,
        files: list[tuple[Path, str]],
        *,
        min_length: int,
        max_definition: int,
        heading_level: int,
    ) -> GlossaryStore:
        """Load and merge glossary files, reusing the cache when unchanged."""
        return cls.assemble(
            files,
            [],
            min_length=min_length,
            max_definition=max_definition,
            heading_level=heading_level,
        )

    @classmethod
    def assemble(
        cls,
        files: list[tuple[Path, str]],
        inline_files: list[tuple[Path, str]],
        *,
        min_length: int,
        max_definition: int,
        heading_level: int,
    ) -> GlossaryStore:
        """Merge glossary files and inline-marked pages into one store.

        Both arguments are ``(absolute path, docs-relative path)`` lists.
        Glossary file entries win over inline definitions of the same term;
        within each group, earlier files win.
        """
        stamp = tuple(cls._stamp(files) + cls._stamp(inline_files))
        key = (stamp, min_length, max_definition, heading_level)

        cached = cls._cache.get(key)
        if cached is not None:
            return cached

        entries: list[GlossaryEntry] = []
        seen: set[str] = set()
        for origin, group in (("file", files), ("inline", inline_files)):
            for path, rel in group:
                for entry in cls._parse_file(
                    path,
                    rel,
                    origin=origin,
                    min_length=min_length,
                    max_definition=max_definition,
                    heading_level=heading_level,
                ):
                    if entry.term.lower() in seen:
                        continue
                    seen.add(entry.term.lower())
                    entries.append(entry)

        # Longest first so the alternation prefers the most specific term.
        entries.sort(key=lambda e: len(e.term), reverse=True)
        store = cls(entries)
        cls._cache[key] = store
        return store

    @staticmethod
    def _stamp(files: list[tuple[Path, str]]) -> list[tuple[str, float | None]]:
        stamp: list[tuple[str, float | None]] = []
        for path, rel in files:
            try:
                mtime: float | None = path.stat().st_mtime
            except OSError:
                mtime = None
            stamp.append((rel, mtime))
        return stamp

    @classmethod
    def _parse_file(
        cls,
        path: Path,
        rel: str,
        *,
        origin: str,
        min_length: int,
        max_definition: int,
        heading_level: int,
    ) -> list[GlossaryEntry]:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return []
        key = (
            str(path),
            mtime,
            origin,
            min_length,
            max_definition,
            heading_level,
        )
        cached = cls._parsed.get(key)
        if cached is not None:
            return cached
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            text = None
        if text is None:
            entries: list[GlossaryEntry] = []
        elif origin == "inline":
            entries = cls._parse_inline(
                text,
                page=rel,
                min_length=min_length,
                max_definition=max_definition,
            )
        else:
            entries = cls._parse(
                text,
                min_length=min_length,
                max_definition=max_definition,
                heading_level=heading_level,
                page=rel,
            )
        cls._parsed[key] = entries
        return entries

    @staticmethod
    def _parse(
        text: str,
        *,
        min_length: int,
        max_definition: int,
        heading_level: int,
        page: str = "",
    ) -> list[GlossaryEntry]:
        text = _FRONT_MATTER_RE.sub("", text, count=1)
        headings = list(_HEADING_RE.finditer(text))
        entries: list[GlossaryEntry] = []
        seen: set[str] = set()

        for i, match in enumerate(headings):
            # Only headings at the configured level are terms. Shallower
            # headings can organize the glossary, and deeper headings stay in
            # the current term's definition.
            level = len(match.group(1))
            if level != heading_level:
                continue
            term = _clean(match.group(2))
            if len(term) < min_length or term.lower() in seen:
                continue
            start = match.end()
            end = _definition_end(text, headings, i, heading_level)
            definition = _clean(text[start:end])
            if not definition:
                continue
            if len(definition) > max_definition:
                definition = definition[: max_definition - 1].rstrip() + "\u2026"
            seen.add(term.lower())
            entries.append(
                GlossaryEntry(term, definition, slugify(term, "-"), page)
            )

        # Longest first so the alternation prefers the most specific term.
        entries.sort(key=lambda e: len(e.term), reverse=True)
        return entries

    @staticmethod
    def _parse_inline(
        text: str,
        *,
        page: str,
        min_length: int,
        max_definition: int,
    ) -> list[GlossaryEntry]:
        """Extract terms marked with <!-- zensical-glossary: Term -->.

        The definition runs from the marker to the next heading, the next
        marker, or the end of the file.
        """
        text = _FRONT_MATTER_RE.sub("", text, count=1)
        markers = list(_INLINE_MARKER_RE.finditer(text))
        if not markers:
            return []
        headings = list(_HEADING_RE.finditer(text))
        entries: list[GlossaryEntry] = []
        seen: set[str] = set()

        for i, marker in enumerate(markers):
            term = _clean(marker.group(1))
            if len(term) < min_length or term.lower() in seen:
                continue
            end = len(text)
            for heading in headings:
                if heading.start() >= marker.end():
                    end = heading.start()
                    break
            if i + 1 < len(markers):
                end = min(end, markers[i + 1].start())
            definition = _clean(text[marker.end() : end])
            if not definition:
                continue
            if len(definition) > max_definition:
                definition = definition[: max_definition - 1].rstrip() + "…"
            seen.add(term.lower())
            entries.append(
                GlossaryEntry(
                    term, definition, slugify(term, "-"), page, "inline"
                )
            )
        return entries

    def build_regex(self, *, case_sensitive: bool) -> re.Pattern[str] | None:
        # The store is shared across pages, so compile once per build instead
        # of once per rendered page.
        if case_sensitive in self._patterns:
            return self._patterns[case_sensitive]
        pattern: re.Pattern[str] | None = None
        if self.entries:
            alternation = "|".join(re.escape(e.term) for e in self.entries)
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.compile(
                rf"(?<![\w-])(?:{alternation})(?![\w-])", flags
            )
        self._patterns[case_sensitive] = pattern
        return pattern

    def lookup(self, text: str, *, case_sensitive: bool) -> GlossaryEntry | None:
        if case_sensitive:
            for entry in self.entries:
                if entry.term == text:
                    return entry
            return None
        return self._by_lower.get(text.lower())


# ----------------------------------------------------------------------------
# Processors
# ----------------------------------------------------------------------------


class _PageState:
    """Per-page state shared between the tree and post processors."""

    __slots__ = ("labels", "wrapped")

    def __init__(self) -> None:
        self.wrapped = False
        self.labels: dict[str, str] = {}


class GlossaryTreeprocessor(Treeprocessor):
    """Wraps glossary term occurrences in linked, tooltip-bearing anchors."""

    name = "zensical-glossary"

    def __init__(
        self, md: Markdown, config: GlossaryConfig, state: _PageState
    ) -> None:
        super().__init__(md)
        self.config = config
        self.state = state

    def run(self, root: Element) -> None:
        context = self._context()
        docs_dir = self._docs_dir(context)
        files = _resolve_glossary_files(docs_dir, self._patterns())
        inline_files = (
            _list_markdown_files(docs_dir)
            if self.config.inline_definitions
            else []
        )
        store = GlossaryStore.assemble(
            files,
            inline_files,
            min_length=self.config.min_length,
            max_definition=self.config.max_definition,
            heading_level=self.config.heading_level,
        )
        if not store.entries:
            return

        page_rel = None
        if context is not None:
            page_path = getattr(context.page, "path", None)
            if page_path:
                page_rel = _norm(page_path)
                # Never annotate the glossary pages themselves.
                if page_rel in {_norm(rel) for _, rel in files}:
                    return

        pattern = store.build_regex(case_sensitive=self.config.case_sensitive)
        if pattern is None:
            return

        # Resolve localized UI labels for this page's language.
        self.state.labels = resolve_labels(
            self._language(context), self.config.labels
        )

        base_urls: dict[tuple[str, str], str] = {}

        def base_url_for(entry: GlossaryEntry) -> str:
            key = (entry.origin, entry.page)
            if key not in base_urls:
                base_urls[key] = self._base_url(context, entry)
            return base_urls[key]

        # A page never links to the terms it defines itself.
        suppress = {
            e.slug
            for e in store.entries
            if page_rel and _norm(e.page) == page_rel
        }

        used: set[str] = set()
        self._walk(root, store, pattern, base_url_for, used, suppress)

    # -- internals ----------------------------------------------------------

    def _context(self) -> Any:
        if ContextPreprocessor is None:
            return None
        return ContextPreprocessor.from_markdown(self.md)

    def _language(self, context: Any) -> str | None:
        """Determine the UI language: explicit config, else site language."""
        if self.config.language:
            return self.config.language
        if context is not None:
            theme = (context.config or {}).get("theme") or {}
            return theme.get("language")
        return None

    def _patterns(self) -> list[str]:
        """Configured glossary sources: glossary_files wins over glossary_file."""
        return list(self.config.glossary_files) or [self.config.glossary_file]

    def _docs_dir(self, context: Any) -> Path:
        from pathlib import Path

        docs_dir = None
        if context is not None:
            docs_dir = (context.config or {}).get("docs_dir")
        return Path(docs_dir) if docs_dir else Path(self.config.docs_dir)

    def _base_url(self, context: Any, entry: GlossaryEntry) -> str:
        use_directory_urls = True
        if context is not None:
            use_directory_urls = bool(
                (context.config or {}).get("use_directory_urls", True)
            )
        derived = _default_base_url(entry.page, use_directory_urls)
        if self.config.base_url is None:
            return derived
        if not self.config.glossary_files:
            # Single-file mode keeps the historical verbatim override, but it
            # only applies to the glossary page itself; inline definitions
            # live on regular pages and always derive their own URL.
            if entry.origin == "inline":
                return derived
            return self.config.base_url
        # Multi-file mode: base_url is a prefix for each derived page URL.
        return self.config.base_url.rstrip("/") + derived

    def _walk(
        self,
        el: Element,
        store: GlossaryStore,
        pattern: re.Pattern[str],
        base_url_for: Callable[[GlossaryEntry], str],
        used: set[str],
        suppress: set[str],
    ) -> None:
        if el.tag in SKIP_TAGS or "glossary-term" in (el.get("class") or ""):
            return

        # Wrap matches found in this element's own text.
        if el.text:
            built = self._build(
                el.text, store, pattern, base_url_for, used, suppress
            )
            if built is not None:
                prefix, nodes = built
                el.text = prefix
                for offset, (anchor, tail) in enumerate(nodes):
                    anchor.tail = tail
                    el.insert(offset, anchor)

        # Recurse into children, wrapping matches found in their tails.
        index = 0
        for child in list(el):
            self._walk(child, store, pattern, base_url_for, used, suppress)
            index = list(el).index(child) + 1
            if child.tail:
                built = self._build(
                    child.tail, store, pattern, base_url_for, used, suppress
                )
                if built is not None:
                    prefix, nodes = built
                    child.tail = prefix
                    for anchor, tail in nodes:
                        anchor.tail = tail
                        el.insert(index, anchor)
                        index += 1

    def _build(
        self,
        text: str,
        store: GlossaryStore,
        pattern: re.Pattern[str],
        base_url_for: Callable[[GlossaryEntry], str],
        used: set[str],
        suppress: set[str],
    ) -> tuple[str, list[tuple[Element, str]]] | None:
        matches: list[tuple[re.Match[str], GlossaryEntry]] = []
        for match in pattern.finditer(text):
            entry = store.lookup(
                match.group(0), case_sensitive=self.config.case_sensitive
            )
            if entry is None or entry.slug in suppress:
                continue
            if self.config.first_only and entry.slug in used:
                continue
            used.add(entry.slug)
            matches.append((match, entry))

        if not matches:
            return None

        self.state.wrapped = True
        prefix = text[: matches[0][0].start()]
        nodes: list[tuple[Element, str]] = []
        for i, (match, entry) in enumerate(matches):
            anchor = self._anchor(entry, match.group(0), base_url_for)
            end = (
                matches[i + 1][0].start()
                if i + 1 < len(matches)
                else len(text)
            )
            nodes.append((anchor, text[match.end() : end]))
        return prefix, nodes

    def _anchor(
        self,
        entry: GlossaryEntry,
        display: str,
        base_url_for: Callable[[GlossaryEntry], str],
    ) -> Element:
        anchor = Element("a")
        anchor.set("class", "glossary-term")
        anchor.set("href", f"{base_url_for(entry)}#{entry.slug}")
        anchor.set("data-glossary", entry.definition)
        anchor.text = display
        return anchor


class GlossaryPostprocessor(Postprocessor):
    """Turns inline markers into anchors and appends the tooltip assets."""

    name = "zensical-glossary"

    def __init__(
        self, md: Markdown, config: GlossaryConfig, state: _PageState
    ) -> None:
        super().__init__(md)
        self.config = config
        self.state = state

    def run(self, text: str) -> str:
        if self.config.inline_definitions:
            text = _INLINE_MARKER_RE.sub(self._anchor_for, text)
        if not self.state.wrapped:
            return text
        return (
            f"{text}\n"
            f"<style>{CSS}</style>\n"
            f"<script>{render_js(self.state.labels)}</script>"
        )

    @staticmethod
    def _anchor_for(match: re.Match[str]) -> str:
        slug = slugify(_clean(match.group(1)), "-")
        return f'<a id="{slug}" class="zensical-glossary-def"></a>'


# ----------------------------------------------------------------------------
# Extension
# ----------------------------------------------------------------------------


class GlossaryConfig:
    """Resolved configuration for the glossary extension."""

    __slots__ = (
        "base_url",
        "case_sensitive",
        "docs_dir",
        "first_only",
        "glossary_file",
        "glossary_files",
        "heading_level",
        "inline_definitions",
        "labels",
        "language",
        "max_definition",
        "min_length",
    )

    def __init__(self, **kwargs: Any) -> None:
        self.glossary_file: str = kwargs.get("glossary_file", "glossary.md")
        files = kwargs.get("glossary_files") or []
        self.glossary_files: list[str] = [str(f) for f in files]
        self.inline_definitions: bool = bool(
            kwargs.get("inline_definitions", False)
        )
        self.docs_dir: str = kwargs.get("docs_dir", "docs")
        self.base_url: str | None = kwargs.get("base_url")
        self.case_sensitive: bool = bool(kwargs.get("case_sensitive", False))
        self.first_only: bool = bool(kwargs.get("first_only", True))
        self.min_length: int = int(kwargs.get("min_length", 2))
        self.max_definition: int = int(kwargs.get("max_definition", 280))
        self.heading_level: int = int(kwargs.get("heading_level", 2))
        self.language: str | None = kwargs.get("language")
        labels = kwargs.get("labels") or {}
        self.labels: dict[str, str] = dict(labels) if labels else {}


class GlossaryExtension(Extension):
    """Markdown extension that cross-links and annotates glossary terms."""

    name = "zensical_glossary"

    def __init__(self, **kwargs: Any) -> None:
        self._enabled: bool = bool(kwargs.pop("enabled", True))
        self._kwargs = kwargs

    def extendMarkdown(self, md: Markdown) -> None:
        if not self._enabled:
            return
        md.registerExtension(self)

        config = GlossaryConfig(**self._kwargs)
        state = _PageState()

        treeprocessor = GlossaryTreeprocessor(md, config, state)
        md.treeprocessors.register(
            treeprocessor, GlossaryTreeprocessor.name, 4
        )

        postprocessor = GlossaryPostprocessor(md, config, state)
        md.postprocessors.register(
            postprocessor, GlossaryPostprocessor.name, 1
        )


# ----------------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------------


def _clean(text: str) -> str:
    """Reduce a Markdown fragment to compact, single-line plain text."""
    text = text.strip()
    for pattern, repl in _CLEAN_STEPS:
        text = pattern.sub(repl, text)
    return text.strip()


def _definition_end(
    text: str, headings: list[re.Match[str]], index: int, heading_level: int
) -> int:
    """Find where a term definition ends in the Markdown source."""
    for heading in headings[index + 1 :]:
        if len(heading.group(1)) <= heading_level:
            return heading.start()
    return len(text)


def _resolve_glossary_files(
    docs_dir: Path, patterns: list[str]
) -> list[tuple[Path, str]]:
    """Expand configured glossary patterns.

    Returns ``(absolute path, docs-relative path)`` pairs in configuration
    order. Patterns containing glob characters (``*``, ``?``, ``[``) are
    expanded against ``docs_dir`` and sorted for deterministic builds;
    plain paths are kept as configured, even if the file is missing (missing
    files simply contribute no entries).
    """
    from pathlib import Path

    resolved: list[tuple[Path, str]] = []
    seen: set[str] = set()

    def add(path: Path, rel: str) -> None:
        rel = _norm_path(rel)
        if rel in seen:
            return
        seen.add(rel)
        resolved.append((path, rel))

    for pattern in patterns:
        rel_pattern = _norm_path(pattern)
        if any(c in rel_pattern for c in "*?["):
            try:
                matches = sorted(
                    (p for p in docs_dir.glob(rel_pattern) if p.is_file()),
                    key=lambda p: p.as_posix(),
                )
            except OSError:
                matches = []
            for path in matches:
                try:
                    rel = path.relative_to(docs_dir).as_posix()
                except ValueError:
                    rel = path.as_posix()
                add(path, rel)
        else:
            add(docs_dir / rel_pattern, rel_pattern)
    return resolved


def _list_markdown_files(docs_dir: Path) -> list[tuple[Path, str]]:
    """List every Markdown page under docs_dir, sorted for determinism."""
    try:
        paths = sorted(
            (
                p
                for p in docs_dir.rglob("*.md")
                if p.is_file()
                and not any(
                    part.startswith(".")
                    for part in p.relative_to(docs_dir).parts
                )
            ),
            key=lambda p: p.as_posix(),
        )
    except OSError:
        return []
    return [(p, p.relative_to(docs_dir).as_posix()) for p in paths]


def _norm(path: str) -> str:
    return _norm_path(path).lower()


def _norm_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _default_base_url(glossary_file: str, use_directory_urls: bool) -> str:
    path = glossary_file.replace("\\", "/")
    path = path.removesuffix(".md")
    path = path.strip("/")
    if not use_directory_urls:
        return f"/{path}.html"
    if path in ("index", "README"):
        return "/"
    if path.endswith(("/index", "/README")):
        return "/" + path.rsplit("/", 1)[0] + "/"
    return f"/{path}/"


def makeExtension(**kwargs: Any) -> GlossaryExtension:
    """Entry point used by Python-Markdown / Zensical."""
    return GlossaryExtension(**kwargs)
