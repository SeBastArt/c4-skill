#!/usr/bin/env python3
"""Open a rendered architecture.html headless and report what a reader would hit.

    py c4_check_page.py <page.html>

Clicks every level tab, counts drawn SVG nodes per tab and collects console and page errors.
Exit 1 on errors or an empty tab. Needs Playwright for Python (`pip install playwright`) and a
Chromium or Edge; without it the script says so and exits 2.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def available() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return False
    return True


def _svg_id(level: str) -> str:
    return {"context": "svg-context", "code": "svg-code"}.get(level) or "svg-" + level.replace(":", "-", 1)


def check(page_path: Path) -> dict:
    from playwright.sync_api import sync_playwright

    errors: list[str] = []
    tabs = []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:
            browser = p.chromium.launch(channel="msedge")
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(Path(page_path).resolve().as_uri())
        page.wait_for_timeout(500)
        for button in page.query_selector_all("button.tab[data-level]"):
            level = button.get_attribute("data-level")
            button.click()
            page.wait_for_timeout(200)
            nodes = page.evaluate(
                "id => { const s = document.getElementById(id); return s ? s.querySelectorAll('*').length : -1 }",
                _svg_id(level))
            tabs.append({"level": level, "label": button.inner_text().strip(), "nodes": nodes})
        browser.close()
    return {"errors": errors, "tabs": tabs}


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = argv if argv is not None else sys.argv[1:]
    if args in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    if not Path(args[0]).is_file():
        print(f"c4_check_page: no such page: {args[0]}", file=sys.stderr)
        return 2
    if not available():
        print("c4_check_page: Playwright is not installed (pip install playwright); page not checked",
              file=sys.stderr)
        return 2
    report = check(Path(args[0]))
    json.dump(report, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 1 if report["errors"] or any(t["nodes"] <= 0 for t in report["tabs"]) else 0


if __name__ == "__main__":
    sys.exit(main())
