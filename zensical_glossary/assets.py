# Copyright (c) 2026 phillarmonic and contributors
# SPDX-License-Identifier: MIT

"""Inline CSS and JavaScript assets for the glossary tooltip."""

from __future__ import annotations

import json

CSS: str = """
.glossary-term {
  border-bottom: 1px dashed var(--md-default-fg-color--light, #9e9e9e);
  cursor: help;
  text-decoration: none;
  color: inherit;
}
.glossary-term:hover {
  border-bottom-color: var(--md-accent-fg-color, #526cfe);
}
.glossary-tooltip {
  position: absolute;
  z-index: 9999;
  max-width: 20rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.2rem;
  font-size: 0.72rem;
  line-height: 1.4;
  color: var(--md-default-bg-color, #fff);
  background: var(--md-default-fg-color, #1e2129);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
  opacity: 0;
  transform: translateY(4px);
  transition: opacity 120ms ease, transform 120ms ease;
  pointer-events: none;
}
.glossary-tooltip[data-show] {
  opacity: 1;
  transform: translateY(0);
}
.glossary-tooltip__more {
  display: block;
  margin-top: 0.35rem;
  font-size: 0.66rem;
  opacity: 0.75;
}
"""

JS: str = """
(function () {
  if (window.__zensicalGlossaryInit) return;
  window.__zensicalGlossaryInit = true;

  var tip = null;

  function labels() {
  return window.__zensicalGlossaryLabels || {};
  }

  function ensureTip() {
    if (tip) return tip;
    tip = document.createElement("div");
    tip.className = "glossary-tooltip";
    tip.setAttribute("role", "tooltip");
    document.body.appendChild(tip);
    return tip;
  }

  function show(el) {
    var def = el.getAttribute("data-glossary");
    if (!def) return;
    var t = ensureTip();
    t.innerHTML = "";
    t.appendChild(document.createTextNode(def));
    if (el.getAttribute("href")) {
      var more = document.createElement("span");
      more.className = "glossary-tooltip__more";
      more.textContent =
        labels().more || "Click to read the full definition \u2192";
      t.appendChild(more);
    }
    t.setAttribute("data-show", "");
    position(el, t);
  }

  function hide() {
    if (tip) tip.removeAttribute("data-show");
  }

  function position(el, t) {
    var r = el.getBoundingClientRect();
    var tr = t.getBoundingClientRect();
    var pad = 8;
    var top = window.scrollY + r.top - tr.height - 6;
    if (top < window.scrollY + pad) {
      top = window.scrollY + r.bottom + 6;
    }
    var left = window.scrollX + r.left + r.width / 2 - tr.width / 2;
    var maxLeft =
      window.scrollX + document.documentElement.clientWidth - tr.width - pad;
    if (left > maxLeft) left = maxLeft;
    if (left < window.scrollX + pad) left = window.scrollX + pad;
    t.style.top = top + "px";
    t.style.left = left + "px";
  }

  function bind(el) {
    if (el.__glossaryBound) return;
    el.__glossaryBound = true;
    el.addEventListener("mouseenter", function () { show(el); });
    el.addEventListener("mouseleave", hide);
    el.addEventListener("focus", function () { show(el); });
    el.addEventListener("blur", hide);
  }

  function scan() {
    var els = document.querySelectorAll(".glossary-term");
    for (var i = 0; i < els.length; i++) bind(els[i]);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scan);
  } else {
    scan();
  }
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(scan);
  }
  window.addEventListener("scroll", hide, true);
})();
"""


def render_js(labels: dict[str, str]) -> str:
    """Return the tooltip JS with localized labels injected.

    Labels are JSON-encoded with ``ensure_ascii=True`` so that accented
    characters remain safe inside an inline HTML ``<script>`` element.
    """
    config = json.dumps(labels or {}, ensure_ascii=True)
    return f"window.__zensicalGlossaryLabels = {config};\n{JS}"
