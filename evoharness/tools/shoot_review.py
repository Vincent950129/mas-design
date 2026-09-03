#!/usr/bin/env python3
"""Checks and proofs for the three review items.

The framework figure has to *show* containment -- the harness stage is the outer
loop and adaptation runs inside it, so the two bands being stacked as peers read
as the wrong claim. The demo banner has to name what the demo runs. And the
environment chooser has to look like a control; see verify_evaluate.py for that
half, which owns the Evaluate tab.
"""
from __future__ import annotations

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "tools/proofs"
BASE = "http://127.0.0.1:8777/evoharness/index.html"
BANNER = "run the evolving mode in your browser"

fails: list[str] = []
checks = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global checks
    checks += 1
    print(f"  {'ok  ' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        fails.append(label + (f": {detail}" if detail else ""))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    errs: list[str] = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 1100}, device_scale_factor=2)
        pg.on("console", lambda m: m.type == "error"
              and "404" not in m.text and errs.append(m.text))
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE, wait_until="networkidle")
        pg.wait_for_timeout(600)

        print("\nDemo banner")
        msg = pg.eval_on_selector(".demo-banner-msg", "n => n.innerText")
        check(BANNER in msg, "the banner says what the demo runs", msg)
        pg.eval_on_selector(".demo-banner-wrap", "n => n.scrollIntoView({block:'center'})")
        pg.wait_for_timeout(200)
        pg.locator(".demo-banner-wrap").screenshot(path=str(OUT / "rv-banner.png"))
        pg.eval_on_selector("body", "n => window.scrollTo(0, 0)")

        print("\nFramework figure")
        # It lives on page 1 of the Benchmark deck.
        pg.click('.pv-tab[data-pv="benchmark"]')
        pg.wait_for_timeout(500)
        pg.click('.lp-step[data-lp="1"]')
        pg.wait_for_timeout(1400)
        check(pg.eval_on_selector(".fw-band--inner",
                                  "n => !!n.closest('.fw-band--outer')"),
              "the inner band sits inside the outer band in the DOM")
        # And geometrically, with the outer band's own frame visible on all four sides.
        gap = pg.evaluate(
            """() => {
                 const o = document.querySelector('.fw-band--outer').getBoundingClientRect();
                 const i = document.querySelector('.fw-band--inner').getBoundingClientRect();
                 return {l: i.left - o.left, r: o.right - i.right,
                         t: i.top - o.top, b: o.bottom - i.bottom};
               }""")
        check(min(gap.values()) > 6, "the outer frame shows on every side of the inner band",
              str({k: round(v) for k, v in gap.items()}))
        # Persistent state is the one thing that genuinely outlives a stage, so it stays out.
        check(not pg.eval_on_selector(".fw-band--across",
                                      "n => !!n.closest('.fw-band--outer')"),
              "persistent state stays outside the harness, as its own copy says")
        # Both modes keep the nesting; deployment only dims the inner loop.
        pg.click('.fw-mode[data-fw="deploy"]')
        pg.wait_for_timeout(500)
        check(pg.eval_on_selector(".fw-band--inner", "n => n.offsetHeight > 0"),
              "the inner band survives deployment mode")
        pg.locator(".fw-figure").screenshot(path=str(OUT / "rv-framework-deploy.png"))
        pg.click('.fw-mode[data-fw="adapt"]')
        pg.wait_for_timeout(700)
        pg.eval_on_selector("#fw", "n => n.scrollIntoView({block:'center'})")
        pg.wait_for_timeout(600)
        pg.locator(".fw-figure").screenshot(path=str(OUT / "rv-framework.png"))

        print("\nEvaluate tab")
        pg.click('.pv-tab[data-pv="overview"]')
        pg.wait_for_timeout(300)
        pg.click('.pv-tab[data-pv="evaluate"]')
        pg.wait_for_timeout(700)

        def to_top(sel: str) -> None:
            # Offset for the sticky view nav, which would otherwise cover the target.
            pg.eval_on_selector(sel, "n => window.scrollTo(0, n.getBoundingClientRect().top"
                                     " + window.scrollY - 70)")
            pg.wait_for_timeout(350)

        to_top("#service .section-heading")
        pg.screenshot(path=str(OUT / "rv-eval-top.png"))
        to_top(".sv-tabs")
        pg.screenshot(path=str(OUT / "rv-eval-key.png"))
        to_top(".sv-knobs")
        pg.screenshot(path=str(OUT / "rv-eval-recap.png"))
        pg.click('.ev-tab[data-ev="local"]')
        pg.wait_for_timeout(400)
        to_top("#service .section-heading")
        pg.screenshot(path=str(OUT / "rv-eval-local.png"))
        b.close()

    check(not errs, "no console errors", str(errs[:3]))
    print(f"\n{checks - len(fails)}/{checks} checks passed")
    if fails:
        print(f"\n{len(fails)} FAILURE(S):")
        for f in fails:
            print(f"  - {f}")
        return 1
    print(f"proofs in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
