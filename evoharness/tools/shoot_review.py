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
# The demo the page sends readers to, with the state the paper wants them to land in:
# the enterprise arm, the CSM gym, evolving mode already on. A quick tunnel, so the
# hostname is only good for as long as the tunnel runs -- see the reachability check.
DEMO = ("https://fails-scotland-diagnostic-joy.trycloudflare.com/"
        "?mode=enterprise&gym=csm&evolving=1")

fails: list[str] = []
checks = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global checks
    checks += 1
    print(f"  {'ok  ' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        fails.append(label + (f": {detail}" if detail else ""))


def note(label: str, detail: str = "") -> None:
    """Something to know about, but not the page's fault -- source material we were given."""
    print(f"  note {label}" + (f" — {detail}" if detail else ""))


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

        print("\nHeader")
        nav = pg.eval_on_selector_all(
            ".pv-bar-inner > *", "ns => ns.map(n => [n.tagName, n.innerText.trim()])")
        views = [t for tag, t in nav if tag == "BUTTON"]
        check(views == ["Overview", "Benchmark", "Tasks", "Results", "Cases", "Evaluate",
                        "Leaderboard"], "the view tabs are unchanged", str(views))
        # The hero's CTA row duplicated these tabs, so it is gone and the demo moved up here.
        check(not pg.query_selector(".cta-buttons"), "the duplicated hero CTA row is gone")
        pill = pg.query_selector(".pv-bar .pv-demo")
        check(pill is not None, "the demo is offered in the nav instead")
        check(pill.get_attribute("href") == DEMO, "the demo pill points at the deployment",
              str(pill.get_attribute("href")))
        check(pill.get_attribute("target") == "_blank"
              and "noopener" in (pill.get_attribute("rel") or ""),
              "the demo pill opens safely")
        # A quick tunnel keeps its hostname only while the tunnel runs, and the page has no
        # way to know it went away: the pill would still look right and land on a Cloudflare
        # error. So follow it. A network failure here is not the page's fault, hence a note.
        if DEMO.startswith("http"):
            try:
                probe = pg.request.get(DEMO, timeout=15000)
                check(probe.ok, "the demo the pill points at is reachable",
                      f"{probe.status} {DEMO}")
            except Exception as exc:                       # offline run, or the tunnel is down
                note("could not reach the demo", f"{type(exc).__name__}: {DEMO}")
        # Emphasis was the point of keeping it, so it must not render as one more tab.
        look = pg.eval_on_selector(
            ".pv-demo", "n => { const s = getComputedStyle(n);"
                        " return [s.backgroundImage.slice(0, 18), s.fontWeight,"
                        " s.color, s.borderRadius]; }")
        check(look[0].startswith("linear-gradient") and int(look[1]) >= 700
              and look[2] == "rgb(255, 255, 255)", "the demo pill keeps its emphasis", str(look))
        # Author photos. Cards render at 66px with object-fit: cover, so the guard is on
        # both ends: big enough not to blur, small enough not to ship a master into a hero.
        cards = pg.eval_on_selector_all(".author-card", """ns => ns.map(c => {
            const img = c.querySelector('img');
            return {name: c.querySelector('a, .author-name').innerText.split('\\n')[0].trim(),
                    src: img ? img.getAttribute('src').split('/').pop() : null,
                    w: img ? img.naturalWidth : 0, css: img ? img.clientWidth : 0};
        })""")
        broken = [c["name"] for c in cards if c["src"] and c["w"] == 0]
        check(not broken, "every author photo loads", str(broken))
        no_photo = [c["name"] for c in cards if not c["src"]]
        check(not no_photo, "every author has a photo", str(no_photo))
        # Names link out wherever the author has a page; two do not have one.
        unlinked = pg.eval_on_selector_all(
            ".author-card", "ns => ns.filter(c => !c.querySelector('a'))"
            ".map(c => c.innerText.split('\\n')[0].trim())")
        check(unlinked == ["Yang Li†1", "Ye Liu1"], "the linked names are the ones with pages",
              str(unlinked))
        # Below 2x the circle a photo looks soft on a retina screen. Whether a better
        # source exists is not something the page can decide, so this reports rather than
        # fails: replacing the file is the fix, and it needs no code change.
        soft = [f"{c['src']} {c['w']}px for a {c['css']}px circle" for c in cards
                if c["src"] and c["w"] < c["css"] * 2]
        if soft:
            note(f"{len(soft)} photo(s) below 2x, so soft on retina", "; ".join(soft))
        else:
            note("every photo has at least 2x for its circle")
        heavy = [f"{p.name} {p.stat().st_size // 1024}KB"
                 for p in (ROOT.parent / "profile").iterdir()
                 if p.name in {c["src"] for c in cards if c["src"]}
                 and p.stat().st_size > 400 * 1024]
        check(not heavy, "no hero avatar ships as a full-size master", str(heavy))

        # The chip row is gone too: those four differences are named in #different instead,
        # under a heading that says what they are.
        check(not pg.query_selector("#hero .meta-badges"), "the hero carries no chip row")
        claims = pg.eval_on_selector_all("#different .diff-pill",
                                         "ns => ns.map(n => n.innerText.trim())")
        check(len(claims) == 4, "the four differences are named in #different", str(claims))
        # The pill leaves the page, so it must not be wired into the view switcher.
        pg.click('.pv-tab[data-pv="results"]')
        pg.wait_for_timeout(700)
        check(pg.eval_on_selector(".pv-view.is-active", "n => n.dataset.pvView") == "results",
              "switching views still works alongside it")
        check(pg.eval_on_selector(".pv-demo", "n => n.offsetHeight > 0"),
              "the demo pill rides along on every view")
        pg.locator(".pv-bar").screenshot(path=str(OUT / "rv-nav.png"))
        pg.click('.pv-tab[data-pv="overview"]')
        pg.wait_for_timeout(500)
        pg.locator("#hero").screenshot(path=str(OUT / "rv-hero.png"))
        pg.locator("#different").screenshot(path=str(OUT / "rv-different.png"))

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
