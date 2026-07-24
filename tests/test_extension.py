import unittest
from tempfile import TemporaryDirectory

from markdown import Markdown

from zensical_glossary import GlossaryExtension
from zensical_glossary.extension import GlossaryStore


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


if __name__ == "__main__":
    unittest.main()
