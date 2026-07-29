# Copyright (c) 2026 phillarmonic and contributors
# SPDX-License-Identifier: MIT

"""Localization of the glossary plugin's own UI strings.

Only the plugin's interface text is translated here (for example the tooltip
call-to-action). Glossary content itself is authored by the user and is not
affected by this module.
"""

from __future__ import annotations

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------


DEFAULT_LANGUAGE = "en"

# Each language maps a stable label key to its translated string. Add new keys
# here (and a matching default in `en`) to localize additional UI text.
TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "more": "Click to read the full definition \u2192",
    },
    "fr": {
        "more": "Cliquez pour lire la d\u00e9finition compl\u00e8te \u2192",
    },
    "es": {
        "more": "Haz clic para leer la definici\u00f3n completa \u2192",
    },
    "pt": {
        "more": "Clique para ler a defini\u00e7\u00e3o completa \u2192",
    },
}

SUPPORTED_LANGUAGES: tuple[str, ...] = tuple(TRANSLATIONS)


# ----------------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------------


def normalize_language(code: str | None) -> str:
    """Normalize a language code to a supported base language.

    Lowercases and strips any region/script subtag (for example ``pt-BR`` and
    ``pt_BR`` both become ``pt``). Unknown or empty codes fall back to the
    default language.
    """
    if not code:
        return DEFAULT_LANGUAGE
    base = code.replace("_", "-").split("-", 1)[0].strip().lower()
    return base if base in TRANSLATIONS else DEFAULT_LANGUAGE


def resolve_labels(
    code: str | None, overrides: dict[str, str] | None = None
) -> dict[str, str]:
    """Return the label set for a language, applying optional overrides.

    The result always contains every key defined for the default language, so
    callers can rely on all labels being present. ``overrides`` (from user
    configuration) win over the built-in translations.
    """
    language = normalize_language(code)
    labels = dict(TRANSLATIONS[DEFAULT_LANGUAGE])
    labels.update(TRANSLATIONS.get(language, {}))
    if overrides:
        labels.update(
            {k: str(v) for k, v in overrides.items() if k in labels and v}
        )
    return labels
