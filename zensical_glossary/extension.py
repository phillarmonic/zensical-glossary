# Copyright (c) 2026 phillarmonic and contributors
# SPDX-License-Identifier: MIT

"""A Zensical / Python-Markdown extension that turns a dedicated glossary
page into hover tooltips and cross-links throughout the rest of the site."""

from __future__ import annotations

import re
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

    __slots__ = ("definition", "slug", "term")

    def __init__(self, term: str, definition: str, slug: str) -> None:
        self.term = term
        self.definition = definition
        self.slug = slug


class GlossaryStore:
    """Parses and caches the glossary source file (by path and mtime)."""

    _cache: ClassVar[dict[str, tuple[float, GlossaryStore]]] = {}

    def __init__(self, entries: list[GlossaryEntry]) -> None:
        self.entries = entries
        # Map lowercase term -> entry for lookups, longest terms first so a
        # multi-word term wins over a shorter substring term.
        self._by_lower: dict[str, GlossaryEntry] = {
            e.term.lower(): e for e in entries
        }

    @classmethod
    def load(
        cls,
        path: Path,
        *,
        min_length: int,
        max_definition: int,
        heading_level: int,
    ) -> GlossaryStore:
        """Load a glossary store, reusing the cache when the file is unchanged."""
        key = f"{path}|{min_length}|{max_definition}|{heading_level}"
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return cls([])

        cached = cls._cache.get(key)
        if cached and cached[0] == mtime:
            return cached[1]

        entries = cls._parse(
            path.read_text(encoding="utf-8"),
            min_length=min_length,
            max_definition=max_definition,
            heading_level=heading_level,
        )
        store = cls(entries)
        cls._cache[key] = (mtime, store)
        return store

    @staticmethod
    def _parse(
        text: str,
        *,
        min_length: int,
        max_definition: int,
        heading_level: int,
    ) -> list[GlossaryEntry]:
        text = _FRONT_MATTER_RE.sub("", text, count=1)
        headings = list(_HEADING_RE.finditer(text))
        entries: list[GlossaryEntry] = []
        seen: set[str] = set()

        for i, match in enumerate(headings):
            # Only headings at or below the configured level are terms; this
            # keeps the page's own H1 title out of the glossary.
            if len(match.group(1)) < heading_level:
                continue
            term = _clean(match.group(2))
            if len(term) < min_length or term.lower() in seen:
                continue
            start = match.end()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            definition = _clean(text[start:end])
            if not definition:
                continue
            if len(definition) > max_definition:
                definition = definition[: max_definition - 1].rstrip() + "\u2026"
            seen.add(term.lower())
            entries.append(GlossaryEntry(term, definition, slugify(term, "-")))

        # Longest first so the alternation prefers the most specific term.
        entries.sort(key=lambda e: len(e.term), reverse=True)
        return entries

    def build_regex(self, *, case_sensitive: bool) -> re.Pattern[str] | None:
        if not self.entries:
            return None
        alternation = "|".join(re.escape(e.term) for e in self.entries)
        flags = 0 if case_sensitive else re.IGNORECASE
        return re.compile(
            rf"(?<![\w-])(?:{alternation})(?![\w-])", flags
        )

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
        store = self._store(context)
        if store is None:
            return

        # Never annotate the glossary page itself.
        if context is not None and _same_page(
            getattr(context.page, "path", None), self.config.glossary_file
        ):
            return

        pattern = store.build_regex(case_sensitive=self.config.case_sensitive)
        if pattern is None:
            return

        # Resolve localized UI labels for this page's language.
        self.state.labels = resolve_labels(
            self._language(context), self.config.labels
        )

        base_url = self._base_url(context)
        used: set[str] = set()
        self._walk(root, store, pattern, base_url, used)

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

    def _store(self, context: Any) -> GlossaryStore | None:
        path = self._glossary_path(context)
        if path is None:
            return None
        return GlossaryStore.load(
            path,
            min_length=self.config.min_length,
            max_definition=self.config.max_definition,
            heading_level=self.config.heading_level,
        )

    def _glossary_path(self, context: Any) -> Path | None:
        from pathlib import Path

        docs_dir = None
        if context is not None:
            docs_dir = (context.config or {}).get("docs_dir")
        docs_dir = Path(docs_dir) if docs_dir else Path(self.config.docs_dir)
        return docs_dir / self.config.glossary_file

    def _base_url(self, context: Any) -> str:
        if self.config.base_url is not None:
            return self.config.base_url
        use_directory_urls = True
        if context is not None:
            use_directory_urls = bool(
                (context.config or {}).get("use_directory_urls", True)
            )
        return _default_base_url(
            self.config.glossary_file, use_directory_urls
        )

    def _walk(
        self,
        el: Element,
        store: GlossaryStore,
        pattern: re.Pattern[str],
        base_url: str,
        used: set[str],
    ) -> None:
        if el.tag in SKIP_TAGS or "glossary-term" in (el.get("class") or ""):
            return

        # Wrap matches found in this element's own text.
        if el.text:
            built = self._build(el.text, store, pattern, base_url, used)
            if built is not None:
                prefix, nodes = built
                el.text = prefix
                for offset, (anchor, tail) in enumerate(nodes):
                    anchor.tail = tail
                    el.insert(offset, anchor)

        # Recurse into children, wrapping matches found in their tails.
        index = 0
        for child in list(el):
            self._walk(child, store, pattern, base_url, used)
            index = list(el).index(child) + 1
            if child.tail:
                built = self._build(
                    child.tail, store, pattern, base_url, used
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
        base_url: str,
        used: set[str],
    ) -> tuple[str, list[tuple[Element, str]]] | None:
        matches: list[tuple[re.Match[str], GlossaryEntry]] = []
        for match in pattern.finditer(text):
            entry = store.lookup(
                match.group(0), case_sensitive=self.config.case_sensitive
            )
            if entry is None:
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
            anchor = self._anchor(entry, match.group(0), base_url)
            end = (
                matches[i + 1][0].start()
                if i + 1 < len(matches)
                else len(text)
            )
            nodes.append((anchor, text[match.end() : end]))
        return prefix, nodes

    def _anchor(
        self, entry: GlossaryEntry, display: str, base_url: str
    ) -> Element:
        anchor = Element("a")
        anchor.set("class", "glossary-term")
        anchor.set("href", f"{base_url}#{entry.slug}")
        anchor.set("data-glossary", entry.definition)
        anchor.text = display
        return anchor


class GlossaryPostprocessor(Postprocessor):
    """Appends the tooltip CSS/JS to pages that use at least one term."""

    name = "zensical-glossary"

    def __init__(self, md: Markdown, state: _PageState) -> None:
        super().__init__(md)
        self.state = state

    def run(self, text: str) -> str:
        if not self.state.wrapped:
            return text
        return (
            f"{text}\n"
            f"<style>{CSS}</style>\n"
            f"<script>{render_js(self.state.labels)}</script>"
        )


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
        "heading_level",
        "labels",
        "language",
        "max_definition",
        "min_length",
    )

    def __init__(self, **kwargs: Any) -> None:
        self.glossary_file: str = kwargs.get("glossary_file", "glossary.md")
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

        postprocessor = GlossaryPostprocessor(md, state)
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


def _same_page(page_path: str | None, glossary_file: str) -> bool:
    if not page_path:
        return False
    return _norm(page_path) == _norm(glossary_file)


def _norm(path: str) -> str:
    return path.replace("\\", "/").lstrip("./").lower()


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
