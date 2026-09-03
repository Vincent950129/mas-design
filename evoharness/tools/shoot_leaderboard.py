#!/usr/bin/env python3
"""Screenshot the leaderboard in the states the merge has to survive.

Renders the ranking with every appendix row in the field, the filtered views,
and the charts that now have to hold a much larger field, so layout problems
show up as pictures rather than as reasoning about CSS.
"""
from __future__ import annotations

import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "tools" / "proofs" / "leaderboard"
OUT.mkdir(parents=True, exist_ok=True)

SHOTS = [
    # name, axis, view, filters, width, and optionally the EOG/ALE arm
    ("skills-rank-all", "skills", "rank", {}, 1440),
    ("skills-rank-gpt5-codex", "skills", "rank", {"llm": "GPT-5", "harness": "Codex"}, 1440),
    ("skills-rank-skill-learning", "skills", "rank", {"cat": "skill"}, 1440),
    ("agents-rank-all", "agents", "rank", {}, 1440),
    ("tools-rank-mas", "tools", "rank", {"agency": "mas"}, 1440),
    ("tools-rank-all", "tools", "rank", {}, 1440),
    ("skills-gap-all", "skills", "gap", {}, 1440),
    ("skills-gap-ale", "skills", "gap", {}, 1440, "ale"),
    ("skills-eff-all", "skills", "eff", {}, 1440),
    ("skills-rank-narrow", "skills", "rank", {}, 430),
    ("skills-rank-empty", "skills", "rank", {"llm": "Sonnet-4.6", "cat": "skill"}, 1440),
    # A single point, and a chart with none: the two degenerate cases filters create.
    ("tools-eff-one-point", "tools", "eff", {"cat": "code"}, 1440),
    ("skills-eff-no-cost", "skills", "eff", {"cat": "skill"}, 1440),
    ("skills-gap-no-arm", "skills", "gap", {"cat": "skill"}, 1440, "ale"),
]


def sweep(browser) -> list[str]:
    """Visit every state the filters can reach and check nothing degenerates.

    Filtering can leave a chart with one point or none at all, which the charts
    never had to survive before there were filters: a lone value collapses the
    y range and every coordinate derived from it comes out NaN. This walks each
    axis, view, environment and facet value and fails on any numeric artefact
    or console error.
    """
    out: list[str] = []
    errs: list[str] = []
    pg = browser.new_page(viewport={"width": 1440, "height": 1000})
    pg.on("console", lambda m: m.type == "error"
          and "ERR_FILE_NOT_FOUND" not in m.text and errs.append(m.text))
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto((ROOT / "index.html").as_uri())
    pg.click('.pv-tab[data-pv="leaderboard"]')
    seen = 0
    for axis in ("tools", "skills", "agents"):
        pg.click(f'[data-lb-axis] [data-axis="{axis}"]')
        for view in ("rank", "gap", "eff"):
            pg.click(f'[data-lb-view] [data-view="{view}"]')
            for env in ("eog", "ale"):
                btn = pg.query_selector(f'[data-env2="{env}"]')
                if btn:
                    btn.click()
                for key in ("llm", "harness", "cat", "agency"):
                    # single-value facets are hidden on purpose
                    if pg.eval_on_selector(f'[data-lbf="{key}"]',
                                           "n => n.closest('.cs-fl').hidden"):
                        continue
                    for val in pg.eval_on_selector_all(
                            f'[data-lbf="{key}"] option', "ns => ns.map(n => n.value)"):
                        pg.select_option(f'[data-lbf="{key}"]', val)
                        seen += 1
                        hits = pg.evaluate(
                            "() => (document.querySelector('#leaderboard').innerHTML"
                            ".match(/NaN|Infinity|undefined/g) || []).length")
                        if hits:
                            out.append(f"{axis}/{view}/{env} {key}={val or 'All'}: "
                                       f"{hits} numeric artefacts")
                    pg.select_option(f'[data-lbf="{key}"]', "")
    pg.wait_for_timeout(200)
    pg.close()
    print(f"\nswept {seen} filter states")
    out += [f"console error: {e}" for e in errs]
    return out


def main() -> None:
    fails: list[str] = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for name, axis, view, filters, width, *rest in SHOTS:
            pg = b.new_page(viewport={"width": width, "height": 1100},
                            device_scale_factor=2)
            pg.goto((ROOT / "index.html").as_uri())
            pg.click('.pv-tab[data-pv="leaderboard"]')
            pg.click(f'[data-lb-axis] [data-axis="{axis}"]')
            pg.click(f'[data-lb-view] [data-view="{view}"]')
            for key, val in filters.items():
                pg.select_option(f'[data-lbf="{key}"]', val)
            if rest:
                pg.click(f'[data-env2="{rest[0]}"]')
            pg.wait_for_timeout(220)
            sec = pg.query_selector("#leaderboard")
            sec.screenshot(path=str(OUT / f"{name}.png"))
            # Report the facts a screenshot cannot assert on its own.
            info = pg.evaluate("""() => {
              const t = document.querySelector('#leaderboard table.lb');
              const rows = t ? [...t.querySelectorAll('tbody tr')] : [];
              const hdr = t ? [...t.querySelectorAll('thead tr:last-child th')].map(h => h.textContent.trim()) : [];
              const sel = [...document.querySelectorAll('#leaderboard [data-lbf]')]
                .map(s => `${s.dataset.lbf}${s.closest('.cs-fl').hidden ? '(hidden)' : ''}`);
              return {
                rows: rows.length,
                hdr: hdr.slice(0, 4).join('|'),
                overflow: t ? t.scrollWidth > t.parentElement.clientWidth : null,
                facets: sel.join(' '),
                count: document.querySelector('#leaderboard [data-lb-count]')?.textContent,
                first: rows.slice(0, 3).map(r => [...r.querySelectorAll('td')]
                  .slice(0, 4).map(c => c.textContent.replace(/\\s+/g, ' ').trim()).join(' / ')),
              };
            }""")
            print(f"\n{name}  ({width}px)")
            print(f"  rows={info['rows']}  hdr={info['hdr']}  hscroll={info['overflow']}")
            print(f"  facets: {info['facets']}   count: {info['count']}")
            for line in info["first"]:
                print(f"    {line}")

            # The caption has to describe what is on screen and the legend has to
            # describe the marks actually drawn. Both are checked against the DOM
            # rather than against a restatement of the rendering rules, so a caveat
            # can neither go missing nor be offered for rows that are filtered out.
            cap = pg.eval_on_selector_all(
                "#leaderboard .lb-cap", "ns => ns.map(n => n.textContent).join(' ')")
            lg = pg.eval_on_selector_all(
                "#leaderboard .lb-legend span", "ns => ns.map(n => n.textContent)")
            shown = pg.evaluate("""() => ({
              skill: !!document.querySelector('#leaderboard table.lb tbody .lb-cat')
                && [...document.querySelectorAll('#leaderboard table.lb tbody .lb-cat')]
                  .some(n => n.textContent.trim() === 'Skill learning'),
              alt: !!document.querySelector('#leaderboard table.lb tbody .lb-llm.is-alt'),
            })""")
            for phrase, want in [
                ("EOG-only ablation", shown["skill"]),
                ("changes the backbone as well", shown["alt"]),
            ]:
                if view == "rank" and (phrase in cap) is not want:
                    fails.append(f"{name}: caption {'omits' if want else 'wrongly mentions'} {phrase!r}")
            if "Skill learning" in lg:
                marks = pg.eval_on_selector_all(
                    "#leaderboard .lb-fig [fill='#be185d'], #leaderboard .lb-fig [fill*='be185d']",
                    "ns => ns.length")
                if not marks:
                    fails.append(f"{name}: legend claims Skill learning with nothing drawn in it")
            pg.close()

        fails += sweep(b)
        b.close()
    print(f"\nwrote {len(SHOTS)} shots to {OUT}")
    for f in fails:
        print(f"  FAIL  {f}")
    if fails:
        raise SystemExit(1)
    print("all rendered-DOM checks passed")


if __name__ == "__main__":
    main()
