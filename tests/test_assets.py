import unittest

from zensical_glossary.assets import CSS, JS


class TooltipAssetTests(unittest.TestCase):
    def test_tooltip_can_be_interactive(self) -> None:
        self.assertIn("pointer-events: auto", CSS)
        self.assertIn('document.createElement("a")', JS)
        self.assertIn("more.href = href", JS)

    def test_tooltip_hover_cancels_delayed_hide(self) -> None:
        self.assertIn('tip.addEventListener("mouseenter", cancelHide)', JS)
        self.assertIn('el.addEventListener("mouseleave", scheduleHide)', JS)


if __name__ == "__main__":
    unittest.main()
