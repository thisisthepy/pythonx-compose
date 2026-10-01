#!/usr/bin/env python3
"""Check the bilingual guide site under `docs/guide/`.

This is the guide's test. It fails when:

* an HTML page does not parse (unbalanced or mis-nested tags);
* a relative link or asset (`href`, `src`) points at a file that does not exist;
* a page shows a string in one language but not the other -- every element carrying
  `data-lang="en"` must be paired, in the same parent, with one carrying `data-lang="ko"`,
  and the reverse;
* visible text sits outside any `data-lang` element (it would show in both languages), unless it
  is code, a diagram, a proper name in `NEUTRAL_TEXT`, or inside an element marked `translate="no"`;
* a page loads an external resource other than Google Fonts.

    python3 tools/check_guide.py          # exit status 0 = clean, 1 = findings printed

Standard library only, so it runs anywhere the repository's tests run.
"""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[1]
GUIDE = REPO / "docs" / "guide"

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source",
    "track", "wbr", "path", "circle", "rect", "line", "polyline", "polygon", "ellipse", "use",
    "stop",
}
ALLOWED_EXTERNAL = ("fonts.googleapis.com", "fonts.gstatic.com")
# Links that leave the site on purpose (sibling repositories, the license, the source).
ALLOWED_LINK_HOSTS = ("github.com",)
# Text that reads the same in both languages and may appear without a `data-lang` pair.
NEUTRAL_TEXT = {"FAQ", "pythonx-compose", "GitHub", "Kotlin", "Python", "→", "←", "·"}
# Elements whose text is code, markup, or a diagram rather than prose.
EXEMPT_TAGS = {"code", "pre", "kbd", "svg", "script", "style", "title"}
REQUIRED_PAGES = (
    "index.html",
    "getting-started.html",
    "concepts.html",
    "guide-composables.html",
    "guide-modifiers.html",
    "guide-manifest.html",
    "ecosystem.html",
    "status.html",
)


class Page(HTMLParser):
    def __init__(self, path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.path = path
        self.stack: list[tuple[str, int]] = []
        self.errors: list[str] = []
        self.refs: list[tuple[str, str, int]] = []  # (attr, value, line)
        # Per open element: list of language markers of its direct children.
        self.children_langs: list[list[str]] = [[]]
        # Per open element: does it (or an ancestor) make its text language-neutral or bilingual?
        self.covered: list[bool] = [False]

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        attrs = dict(attrs)
        for attr in ("href", "src"):
            if attrs.get(attr):
                self.refs.append((attr, attrs[attr], line))
        lang = attrs.get("data-lang")
        if lang is not None:
            if lang not in ("en", "ko"):
                self.errors.append(f"{line}: data-lang={lang!r} is neither en nor ko")
            self.children_langs[-1].append(lang)
        if tag in VOID:
            return
        self.stack.append((tag, line))
        self.children_langs.append([])
        self.covered.append(
            self.covered[-1]
            or lang is not None
            or tag in EXEMPT_TAGS
            or attrs.get("translate") == "no"
        )

    def handle_startendtag(self, tag, attrs):
        # `<path ... />` and friends: record refs and language, never push.
        line = self.getpos()[0]
        attrs = dict(attrs)
        for attr in ("href", "src"):
            if attrs.get(attr):
                self.refs.append((attr, attrs[attr], line))
        lang = attrs.get("data-lang")
        if lang is not None:
            self.children_langs[-1].append(lang)

    def handle_endtag(self, tag):
        line = self.getpos()[0]
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"{line}: </{tag}> closes nothing")
            return
        open_tag, open_line = self.stack.pop()
        langs = self.children_langs.pop()
        self.covered.pop()
        if open_tag != tag:
            self.errors.append(f"{line}: </{tag}> closes <{open_tag}> opened on line {open_line}")
        en, ko = langs.count("en"), langs.count("ko")
        if en != ko:
            self.errors.append(
                f"{open_line}: <{open_tag}> has {en} English and {ko} Korean children -- "
                "a string exists in one language only"
            )

    def handle_data(self, data):
        text = data.strip()
        if not text or self.covered[-1]:
            return
        words = [w for w in text.replace("·", " ").split() if any(ch.isalpha() for ch in w)]
        if words and text not in NEUTRAL_TEXT:
            self.errors.append(f"{self.getpos()[0]}: untranslated text outside data-lang: {text[:60]!r}")

    def close(self):
        super().close()
        for tag, line in self.stack:
            self.errors.append(f"{line}: <{tag}> is never closed")


def check_ref(page: Path, attr: str, value: str) -> str | None:
    parsed = urlparse(value)
    if parsed.scheme in ("http", "https"):
        host = parsed.netloc
        if attr == "src" or (attr == "href" and value.endswith(".css")):
            if not host.endswith(ALLOWED_EXTERNAL):
                return f"external resource {value} (only Google Fonts is allowed)"
            return None
        if host.endswith(ALLOWED_EXTERNAL + ALLOWED_LINK_HOSTS):
            return None
        return f"external link to an unexpected host: {value}"
    if parsed.scheme in ("mailto", "data") or value.startswith("#"):
        return None
    target = (page.parent / parsed.path).resolve()
    if not target.exists():
        return f"{attr}={value!r} does not resolve ({target.relative_to(REPO) if target.is_relative_to(REPO) else target})"
    return None


def main() -> int:
    findings: list[str] = []
    if not GUIDE.is_dir():
        print(f"FAIL: {GUIDE.relative_to(REPO)} does not exist")
        return 1
    for name in REQUIRED_PAGES:
        if not (GUIDE / name).is_file():
            findings.append(f"{name}: required page is missing")
    pages = sorted(GUIDE.rglob("*.html"))
    for page in pages:
        parser = Page(page)
        parser.feed(page.read_text(encoding="utf-8"))
        parser.close()
        rel = page.relative_to(REPO)
        findings += [f"{rel}:{e}" for e in parser.errors]
        for attr, value, line in parser.refs:
            problem = check_ref(page, attr, value)
            if problem:
                findings.append(f"{rel}:{line}: {problem}")
    for finding in findings:
        print(f"FAIL: {finding}")
    print(f"{len(pages)} pages checked, {len(findings)} findings")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
