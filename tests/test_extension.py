import os
import unittest
from tempfile import TemporaryDirectory

from markdown import Markdown

from zensical_glossary import GlossaryExtension
from zensical_glossary.extension import GlossaryStore, _resolve_glossary_files


class GlossaryStoreParseTests(unittest.TestCase):
    def terms(self, text: str, heading_level: int = 2) -> list[str]:
        entries = GlossaryStore._parse(
            text,
            min_length=2,
            max_definition=280,
            heading_level=heading_level,
        )
        return [entry.term for entry in entries]

    def test_terms_use_exact_heading_level(self) -> None:
        terms = self.terms(
            """
# Glossary

## Concepts

### Markdown

A lightweight syntax.

#### Syntax notes

Nested headings are definition content.

### Extension

A Markdown plugin.
""",
            heading_level=3,
        )

        self.assertEqual(["Extension", "Markdown"], terms)

    def test_definition_continues_through_nested_headings(self) -> None:
        entries = GlossaryStore._parse(
            """
# Glossary

## Markdown

A lightweight syntax.

### Syntax notes

Nested headings are part of this definition.

## Extension

A Markdown plugin.
""",
            min_length=2,
            max_definition=280,
            heading_level=2,
        )

        by_term = {entry.term: entry.definition for entry in entries}
        self.assertIn("Syntax notes", by_term["Markdown"])
        self.assertIn("Nested headings", by_term["Markdown"])
        self.assertNotIn("Extension", by_term["Markdown"])


class GlossaryRenderingTests(unittest.TestCase):
    def setUp(self) -> None:
        GlossaryStore.clear_cache()

    def render(self, text: str, *, first_only: bool = False) -> str:
        with TemporaryDirectory() as tmp:
            from pathlib import Path

            docs_dir = Path(tmp)
            (docs_dir / "glossary.md").write_text(
                """
# Glossary

## Admonition

An admonition is a callout block.
""",
                encoding="utf-8",
            )
            md = Markdown(
                extensions=[
                    "admonition",
                    GlossaryExtension(
                        docs_dir=str(docs_dir),
                        glossary_file="glossary.md",
                        base_url="/glossary/",
                        first_only=first_only,
                    ),
                ]
            )
            return md.convert(text)

    def test_admonition_body_terms_are_wrapped(self) -> None:
        html = self.render(
            """
!!! note

    This Admonition should be wrapped.
"""
        )

        self.assertIn('<div class="admonition note">', html)
        self.assertIn('class="glossary-term"', html)
        self.assertIn('href="/glossary/#admonition"', html)

    def test_first_only_suppresses_repeated_terms_in_later_elements(
        self,
    ) -> None:
        html = self.render(
            """
Admonition appears first.

!!! note

    This Admonition appears later.
""",
            first_only=True,
        )

        self.assertEqual(html.count('class="glossary-term"'), 1)


class GlossaryStoreMultiFileTests(unittest.TestCase):
    def setUp(self) -> None:
        GlossaryStore.clear_cache()

    @staticmethod
    def _write(docs_dir, rel: str, text: str):
        path = docs_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_merge_dedupes_across_files_first_file_wins(self) -> None:
        with TemporaryDirectory() as tmp:
            from pathlib import Path

            docs_dir = Path(tmp)
            first = self._write(
                docs_dir,
                "glossary/core.md",
                "# Core\n\n## Shared\n\nDefined in core.\n\n## Alpha\n\nA term.\n",
            )
            second = self._write(
                docs_dir,
                "glossary/api.md",
                "# API\n\n## Shared\n\nDefined in api.\n\n## Beta\n\nB term.\n",
            )
            store = GlossaryStore.load_multi(
                [(first, "glossary/core.md"), (second, "glossary/api.md")],
                min_length=2,
                max_definition=280,
                heading_level=2,
            )

        by_term = {entry.term: entry for entry in store.entries}
        self.assertEqual({"Shared", "Alpha", "Beta"}, set(by_term))
        self.assertEqual("Defined in core.", by_term["Shared"].definition)
        self.assertEqual("glossary/core.md", by_term["Alpha"].page)
        self.assertEqual("glossary/api.md", by_term["Beta"].page)

    def test_missing_files_contribute_no_entries(self) -> None:
        with TemporaryDirectory() as tmp:
            from pathlib import Path

            docs_dir = Path(tmp)
            present = self._write(
                docs_dir, "glossary.md", "# Glossary\n\n## Term\n\nA term.\n"
            )
            store = GlossaryStore.load_multi(
                [
                    (docs_dir / "missing.md", "missing.md"),
                    (present, "glossary.md"),
                ],
                min_length=2,
                max_definition=280,
                heading_level=2,
            )

        self.assertEqual(["Term"], [entry.term for entry in store.entries])

    def test_store_is_cached_until_a_file_changes(self) -> None:
        with TemporaryDirectory() as tmp:
            from pathlib import Path

            docs_dir = Path(tmp)
            path = self._write(
                docs_dir, "glossary.md", "# Glossary\n\n## Alpha\n\nA term.\n"
            )
            kwargs = dict(min_length=2, max_definition=280, heading_level=2)
            files = [(path, "glossary.md")]

            first = GlossaryStore.load_multi(files, **kwargs)
            self.assertIs(first, GlossaryStore.load_multi(files, **kwargs))

            path.write_text(
                "# Glossary\n\n## Beta\n\nB term.\n", encoding="utf-8"
            )
            os.utime(path, (path.stat().st_atime, path.stat().st_mtime + 1))
            second = GlossaryStore.load_multi(files, **kwargs)
            self.assertIsNot(first, second)
            self.assertEqual(["Beta"], [e.term for e in second.entries])


class GlossaryFileResolutionTests(unittest.TestCase):
    def test_globs_expand_sorted_and_skip_non_files(self) -> None:
        with TemporaryDirectory() as tmp:
            from pathlib import Path

            docs_dir = Path(tmp)
            (docs_dir / "glossary" / "nested").mkdir(parents=True)
            for name in ("b.md", "a.md"):
                (docs_dir / "glossary" / name).write_text(
                    "# G\n", encoding="utf-8"
                )
            (docs_dir / "glossary" / "notes.txt").write_text(
                "x", encoding="utf-8"
            )

            files = _resolve_glossary_files(docs_dir, ["glossary/*.md"])

        self.assertEqual(
            ["glossary/a.md", "glossary/b.md"], [rel for _, rel in files]
        )

    def test_explicit_paths_are_kept_in_order_even_when_missing(self) -> None:
        with TemporaryDirectory() as tmp:
            from pathlib import Path

            docs_dir = Path(tmp)
            files = _resolve_glossary_files(
                docs_dir, ["missing.md", "glossary.md"]
            )

        self.assertEqual(
            ["missing.md", "glossary.md"], [rel for _, rel in files]
        )

    def test_overlapping_patterns_dedupe_files(self) -> None:
        with TemporaryDirectory() as tmp:
            from pathlib import Path

            docs_dir = Path(tmp)
            (docs_dir / "glossary").mkdir()
            (docs_dir / "glossary" / "a.md").write_text("# G\n", "utf-8")

            files = _resolve_glossary_files(
                docs_dir, ["glossary/a.md", "glossary/*.md"]
            )

        self.assertEqual(["glossary/a.md"], [rel for _, rel in files])


class GlossaryMultiPageRenderingTests(unittest.TestCase):
    def setUp(self) -> None:
        GlossaryStore.clear_cache()

    def render(self, text: str, **overrides) -> str:
        with TemporaryDirectory() as tmp:
            from pathlib import Path

            docs_dir = Path(tmp)
            glossary = docs_dir / "glossary"
            glossary.mkdir()
            (glossary / "core.md").write_text(
                "# Core\n\n## Zensical\n\nA static site generator.\n",
                encoding="utf-8",
            )
            (glossary / "api.md").write_text(
                "# API\n\n## Extension\n\nA Markdown plugin.\n",
                encoding="utf-8",
            )
            config = {
                "docs_dir": str(docs_dir),
                "glossary_files": ["glossary/core.md", "glossary/api.md"],
            }
            config.update(overrides)
            md = Markdown(extensions=[GlossaryExtension(**config)])
            return md.convert(text)

    def test_terms_link_to_their_own_pages(self) -> None:
        html = self.render("Zensical builds on an Extension.")

        self.assertIn('href="/glossary/core/#zensical"', html)
        self.assertIn('href="/glossary/api/#extension"', html)

    def test_base_url_is_a_prefix_in_multi_file_mode(self) -> None:
        html = self.render(
            "Zensical builds on an Extension.",
            base_url="https://example.com/docs/",
        )

        self.assertIn(
            'href="https://example.com/docs/glossary/core/#zensical"', html
        )
        self.assertIn(
            'href="https://example.com/docs/glossary/api/#extension"', html
        )

    def test_glob_patterns_load_all_pages(self) -> None:
        html = self.render(
            "Zensical builds on an Extension.",
            glossary_files=["glossary/*.md"],
        )

        self.assertIn('href="/glossary/core/#zensical"', html)
        self.assertIn('href="/glossary/api/#extension"', html)


class GlossaryInlineParseTests(unittest.TestCase):
    def parse(self, text: str, page: str = "guide.md"):
        return GlossaryStore._parse_inline(
            text, page=page, min_length=2, max_definition=280
        )

    def test_marker_defines_term_until_next_heading(self) -> None:
        entries = self.parse(
            """
# Guide

<!-- zensical-glossary: Widget -->

A widget is a reusable unit.

More widget details.

## Next section

Not part of the definition.
"""
        )

        self.assertEqual(["Widget"], [e.term for e in entries])
        entry = entries[0]
        self.assertEqual("inline", entry.origin)
        self.assertEqual("guide.md", entry.page)
        self.assertIn("reusable unit", entry.definition)
        self.assertIn("More widget details", entry.definition)
        self.assertNotIn("Next section", entry.definition)

    def test_definition_ends_at_next_marker(self) -> None:
        entries = self.parse(
            """
<!-- zensical-glossary: Alpha -->

First term.

<!-- zensical-glossary: Beta -->

Second term.
"""
        )

        by_term = {e.term: e.definition for e in entries}
        self.assertEqual("First term.", by_term["Alpha"])
        self.assertEqual("Second term.", by_term["Beta"])

    def test_multi_word_terms_and_short_terms(self) -> None:
        entries = self.parse(
            """
<!-- zensical-glossary: Pull Request -->

A reviewed change proposal.

<!-- zensical-glossary: X -->

Too short.
"""
        )

        self.assertEqual(["Pull Request"], [e.term for e in entries])
        self.assertEqual("pull-request", entries[0].slug)

    def test_empty_definitions_are_skipped(self) -> None:
        entries = self.parse(
            """
<!-- zensical-glossary: Widget -->

## Next section
"""
        )

        self.assertEqual([], entries)

    def test_front_matter_is_stripped(self) -> None:
        entries = self.parse(
            """---
title: Guide
---

<!-- zensical-glossary: Widget -->

A widget.
"""
        )

        self.assertEqual(["Widget"], [e.term for e in entries])


class GlossaryInlineRenderingTests(unittest.TestCase):
    def setUp(self) -> None:
        GlossaryStore.clear_cache()

    def make_docs(self, docs_dir) -> None:
        guide = docs_dir / "guide.md"
        guide.write_text(
            "# Guide\n\n"
            "<!-- zensical-glossary: Widget -->\n\n"
            "A widget is a reusable unit.\n",
            encoding="utf-8",
        )
        glossary = docs_dir / "glossary"
        glossary.mkdir()
        (glossary / "core.md").write_text(
            "# Core\n\n## Extension\n\nA Markdown plugin.\n",
            encoding="utf-8",
        )

    def render(self, docs_dir, text: str, **overrides) -> str:
        config = {
            "docs_dir": str(docs_dir),
            "glossary_files": ["glossary/*.md"],
            "inline_definitions": True,
        }
        config.update(overrides)
        md = Markdown(extensions=[GlossaryExtension(**config)])
        return md.convert(text)

    def test_marker_becomes_an_anchor(self) -> None:
        with TemporaryDirectory() as tmp:
            from pathlib import Path

            docs_dir = Path(tmp)
            self.make_docs(docs_dir)
            html = self.render(
                docs_dir,
                "<!-- zensical-glossary: Widget -->\n\nA widget is a unit.\n",
            )

        self.assertIn(
            '<a id="widget" class="zensical-glossary-def"></a>', html
        )
        self.assertNotIn("<!-- zensical-glossary:", html)

    def test_other_pages_link_to_the_defining_page(self) -> None:
        with TemporaryDirectory() as tmp:
            from pathlib import Path

            docs_dir = Path(tmp)
            self.make_docs(docs_dir)
            html = self.render(docs_dir, "A Widget appears here.")

        self.assertIn('href="/guide/#widget"', html)

    def test_hybrid_mode_combines_files_and_inline_definitions(self) -> None:
        with TemporaryDirectory() as tmp:
            from pathlib import Path

            docs_dir = Path(tmp)
            self.make_docs(docs_dir)
            html = self.render(docs_dir, "A Widget and an Extension.")

        self.assertIn('href="/guide/#widget"', html)
        self.assertIn('href="/glossary/core/#extension"', html)

    def test_glossary_files_win_over_inline_definitions(self) -> None:
        with TemporaryDirectory() as tmp:
            from pathlib import Path

            docs_dir = Path(tmp)
            self.make_docs(docs_dir)
            (docs_dir / "glossary" / "widgets.md").write_text(
                "# Widgets\n\n## Widget\n\nThe canonical widget.\n",
                encoding="utf-8",
            )
            html = self.render(docs_dir, "A Widget appears here.")

        self.assertIn('href="/glossary/widgets/#widget"', html)
        self.assertIn("The canonical widget.", html)

    def test_inline_mode_off_leaves_markers_untouched(self) -> None:
        with TemporaryDirectory() as tmp:
            from pathlib import Path

            docs_dir = Path(tmp)
            self.make_docs(docs_dir)
            html = self.render(
                docs_dir,
                "<!-- zensical-glossary: Gizmo -->\n\nA gizmo.\n\nA Gizmo.",
                inline_definitions=False,
            )

        self.assertNotIn("zensical-glossary-def", html)
        self.assertNotIn("glossary-term", html)


class GlossaryInlineSuppressionTests(unittest.TestCase):
    def setUp(self) -> None:
        GlossaryStore.clear_cache()

    def test_defining_page_does_not_link_its_own_term(self) -> None:
        from unittest import mock

        from zensical_glossary import extension

        class fake_page:
            path = "guide.md"

        class fake_context:
            page = fake_page()
            config: dict = {}

        class fake_preprocessor:
            @classmethod
            def from_markdown(cls, md):
                return fake_context()

        with TemporaryDirectory() as tmp:
            from pathlib import Path

            docs_dir = Path(tmp)
            (docs_dir / "guide.md").write_text(
                "# Guide\n\n"
                "<!-- zensical-glossary: Widget -->\n\n"
                "A widget is a reusable unit.\n",
                encoding="utf-8",
            )
            md = Markdown(
                extensions=[
                    GlossaryExtension(
                        docs_dir=str(docs_dir),
                        glossary_files=[],
                        glossary_file="missing.md",
                        inline_definitions=True,
                    )
                ]
            )
            with mock.patch.object(
                extension, "ContextPreprocessor", fake_preprocessor
            ):
                html = md.convert(
                    "This Widget mention stays plain on the defining page."
                )

        self.assertNotIn("glossary-term", html)


class GlossaryAliasParseTests(unittest.TestCase):
    def test_parse_extracts_aliases_and_strips_marker(self) -> None:
        entries = GlossaryStore._parse(
            """
# Glossary

## Concepts

### Component
<!-- zensical-glossary-aliases: components, reusable component -->

A component is a reusable building block.
""",
            min_length=2,
            max_definition=280,
            heading_level=3,
        )

        self.assertEqual(["Component"], [e.term for e in entries])
        entry = entries[0]
        self.assertEqual(("components", "reusable component"), entry.aliases)
        self.assertNotIn("zensical-glossary-aliases", entry.definition)
        self.assertIn("reusable building block", entry.definition)

    def test_parse_inline_extracts_aliases(self) -> None:
        entries = GlossaryStore._parse_inline(
            """
<!-- zensical-glossary: Widget -->
<!-- zensical-glossary-aliases: gadget, widgets -->

A widget is a reusable unit.
""",
            page="guide.md",
            min_length=2,
            max_definition=280,
        )

        self.assertEqual(("gadget", "widgets"), entries[0].aliases)
        self.assertEqual("A widget is a reusable unit.", entries[0].definition)

    def test_min_length_and_duplicates_filter_aliases(self) -> None:
        entries = GlossaryStore._parse(
            """
## Widget
<!-- zensical-glossary-aliases: x, gadget, Gadget, widgets -->

A widget.
""",
            min_length=2,
            max_definition=280,
            heading_level=2,
        )

        self.assertEqual(("gadget", "widgets"), entries[0].aliases)


class GlossaryAliasStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        GlossaryStore.clear_cache()

    @staticmethod
    def _store(*files: tuple[str, str]) -> GlossaryStore:
        with TemporaryDirectory() as tmp:
            from pathlib import Path

            docs_dir = Path(tmp)
            resolved = []
            for rel, text in files:
                path = docs_dir / rel
                path.write_text(text, encoding="utf-8")
                resolved.append((path, rel))
            return GlossaryStore.load_multi(
                resolved, min_length=2, max_definition=280, heading_level=2
            )

    def test_alias_colliding_with_a_term_is_dropped(self) -> None:
        store = self._store(
            ("a.md", "# A\n\n## Shared\n\nA term.\n"),
            (
                "b.md",
                (
                    "# B\n\n## Beta\n"
                    "<!-- zensical-glossary-aliases: Shared, gadget -->\n\n"
                    "B term.\n"
                ),
            ),
        )

        by_term = {entry.term: entry for entry in store.entries}
        self.assertEqual(("gadget",), by_term["Beta"].aliases)
        self.assertEqual("Shared", store.lookup("shared", case_sensitive=False).term)

    def test_duplicate_alias_first_entry_wins(self) -> None:
        store = self._store(
            (
                "a.md",
                (
                    "# A\n\n## Alpha\n"
                    "<!-- zensical-glossary-aliases: gadget -->\n\n"
                    "A term.\n"
                ),
            ),
            (
                "b.md",
                (
                    "# B\n\n## Beta\n"
                    "<!-- zensical-glossary-aliases: gadget -->\n\n"
                    "B term.\n"
                ),
            ),
        )

        by_term = {entry.term: entry for entry in store.entries}
        self.assertEqual(("gadget",), by_term["Alpha"].aliases)
        self.assertEqual((), by_term["Beta"].aliases)
        self.assertEqual("Alpha", store.lookup("gadget", case_sensitive=False).term)


class GlossaryAliasRenderingTests(unittest.TestCase):
    def setUp(self) -> None:
        GlossaryStore.clear_cache()

    def render(self, text: str, glossary: str, **overrides) -> str:
        with TemporaryDirectory() as tmp:
            from pathlib import Path

            docs_dir = Path(tmp)
            (docs_dir / "glossary.md").write_text(glossary, encoding="utf-8")
            config = {
                "docs_dir": str(docs_dir),
                "glossary_file": "glossary.md",
                "base_url": "/glossary/",
            }
            config.update(overrides)
            md = Markdown(extensions=[GlossaryExtension(**config)])
            return md.convert(text)

    GLOSSARY = (
        "# Glossary\n\n"
        "## Component\n"
        "<!-- zensical-glossary-aliases: components, reusable component -->\n\n"
        "A component is a reusable building block.\n"
    )

    def test_alias_links_to_the_canonical_anchor(self) -> None:
        html = self.render("The components are in the inventory.", self.GLOSSARY)

        self.assertIn('href="/glossary/#component"', html)
        self.assertIn(">components</a>", html)
        self.assertIn('data-glossary="A component', html)

    def test_longest_surface_wins(self) -> None:
        html = self.render("A reusable component exists.", self.GLOSSARY)

        self.assertIn(">reusable component</a>", html)
        self.assertEqual(1, html.count('class="glossary-term"'))

    def test_first_only_counts_term_and_alias_as_one_entry(self) -> None:
        html = self.render(
            "Component registered. More components here.",
            self.GLOSSARY,
            first_only=True,
        )

        self.assertEqual(1, html.count('class="glossary-term"'))

    def test_alias_matching_is_case_insensitive_by_default(self) -> None:
        html = self.render("The COMPONENTS are here.", self.GLOSSARY)

        self.assertIn(">COMPONENTS</a>", html)

    def test_case_sensitive_aliases(self) -> None:
        glossary = self.GLOSSARY

        exact = self.render(
            "The components are here.", glossary, case_sensitive=True
        )
        self.assertIn(">components</a>", exact)

        different_case = self.render(
            "The COMPONENTS are here.", glossary, case_sensitive=True
        )
        self.assertNotIn("glossary-term", different_case)

    def test_inline_definition_with_aliases(self) -> None:
        with TemporaryDirectory() as tmp:
            from pathlib import Path

            docs_dir = Path(tmp)
            (docs_dir / "guide.md").write_text(
                "# Guide\n\n"
                "<!-- zensical-glossary: Widget -->\n"
                "<!-- zensical-glossary-aliases: gadget -->\n\n"
                "A widget is a reusable unit.\n",
                encoding="utf-8",
            )
            md = Markdown(
                extensions=[
                    GlossaryExtension(
                        docs_dir=str(docs_dir),
                        glossary_file="missing.md",
                        inline_definitions=True,
                    )
                ]
            )
            html = md.convert("A gadget appears here.")

        self.assertIn('href="/guide/#widget"', html)
        self.assertIn(">gadget</a>", html)


if __name__ == "__main__":
    unittest.main()
