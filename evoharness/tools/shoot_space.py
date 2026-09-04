#!/usr/bin/env python3
"""Guards the empty band above and below the copy in the page's two blue boxes.

Bulma sizes .hero-body and .section for a hero that carries a byline and a row of
buttons; this hero is three blocks of text, and the BibTeX card is a heading, a
listing and a button. On Bulma's defaults the hero opened with 80px of nothing and
closed with 96px, which is what this checks has not crept back.
"""
from __future__ import annotations

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "tools/proofs"
BASE = "http://127.0.0.1:8777/evoharness/index.html"
# Each box, the shot to leave behind for it, and the most empty space either end may
# hold. Generous on purpose: the point is to catch a padding default coming back, not
# to pin the design to a pixel.
BOXES = [("#hero", "hero-space.png", 48), (".bibtex-card", "bibtex-space.png", 48)]

# Empty space is what the box's own frame adds beyond the outermost thing it draws,
# so measure against every visible descendant that carries ink of its own.
JS = """sel => {
  const box = document.querySelector(sel);
  const b = box.getBoundingClientRect();
  const kids = [...box.querySelectorAll('h1, h2, h3, p, pre, button, a, span, div')]
      .filter(n => n.offsetHeight > 0 && n.innerText.trim()
                   && !n.querySelector('h1, h2, h3, p, pre, button'));
  const rs = kids.map(n => n.getBoundingClientRect());
  return {h: Math.round(b.height),
          top: Math.round(Math.min(...rs.map(r => r.top)) - b.top),
          bottom: Math.round(b.bottom - Math.max(...rs.map(r => r.bottom))),
          content: kids.map(n => [n.tagName.toLowerCase()
                                  + (n.className ? '.' + String(n.className).split(' ')[0] : ''),
                                  n.innerText.trim().split('\\n')[0].slice(0, 34)])};
}"""


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    fails: list[str] = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 1100}, device_scale_factor=2)
        pg.goto(BASE, wait_until="networkidle")
        pg.wait_for_timeout(500)
        for sel, shot, cap in BOXES:
            m = pg.evaluate(JS, sel)
            worst = max(m["top"], m["bottom"])
            ok = worst <= cap
            print(f"\n{'ok  ' if ok else 'FAIL'} {sel}  {m['h']}px tall — empty above "
                  f"{m['top']}px, empty below {m['bottom']}px (cap {cap}px)")
            if not ok:
                fails.append(f"{sel} wastes {worst}px at one end")
            for tag, text in m["content"]:
                print(f"       {tag:26} {text}")
            pg.locator(sel).screenshot(path=str(OUT / shot))
        # And the hero in context: the space it gives back only reads as an improvement
        # next to the nav above it and the band below it. Back to the top first -- the
        # per-box shots above scrolled to whatever they were framing.
        pg.evaluate("() => window.scrollTo(0, 0)")
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(OUT / "page-top.png"),
                      clip={"x": 0, "y": 0, "width": 1280, "height": 760})
        b.close()
    if fails:
        print("\n" + "\n".join(f"  - {f}" for f in fails))
        return 1
    print(f"\nboth boxes are within their caps; shots in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
