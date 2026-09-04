#!/usr/bin/env python3
"""Check the transfer chart against the paper's own FWT/BWT figures.

The chart had been carrying a single EOG bar for tools, copied from a summary
table the paper has since commented out and marked as needing an update. The
figures are the live source, so the numbers below are transcribed from them and
the page is checked against that, method by method and sign by sign:

  Figure 3  figs/fwt_bwt_tool_verifier_compact.png
  Figure 4  figs/fwt_bwt_skill_verifier_compact_claude.png
  Figure 6  figs/fwt_bwt_agent_verifier_compact.png

A value the figure omits is not a zero, it is a measure that method does not
report, and the two have to stay distinguishable on screen: deployment reports
no FWT because there is no stage-specific adaptation to take a delta against,
and Claude Code is held out of the adaptation half entirely. Those are written
here as None and the page has to draw them as stubs rather than as bars.
"""
from __future__ import annotations

import pathlib
import re

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "tools" / "proofs" / "xfer"
OUT.mkdir(parents=True, exist_ok=True)

DAG = "\u2020"

# axis -> env -> [(method as the page labels it, fwt, bwt, fwt dagger, bwt dagger)]
# The figures label deployment "ReAct/Codex" on tools and "Codex" on the other
# two; the page calls all three "Deploy", since its own tables carry the host.
FIG = {
    "tools": {  # Figure 3
        "eog": [
            ("Deploy", None, -0.7, False, True),
            ("GEPA", 2.6, 0.4, True, True),
            ("Meta-H.", 1.0, 1.4, True, True),
        ],
        "ale": [
            ("Deploy", None, -5.3, False, False),
            ("GEPA", -28.5, 12.6, False, False),
            ("Meta-H.", -11.1, 2.1, False, False),
        ],
    },
    "skills": {  # Figure 4
        "eog": [
            ("Deploy", None, 2.1, False, True),
            ("Claude Code", None, -2.6, False, False),
            ("Codex mem.", -1.5, -0.6, False, True),
            ("GEPA", 1.1, 6.6, True, False),
            # The figure prints "-0.0", a negative that rounds flat; the page
            # draws zero as a mark on the axis, which is the honest reading.
            ("Meta-H.", 1.4, 0.0, True, True),
        ],
        "ale": [
            ("Deploy", None, -4.0, False, False),
            ("Claude Code", None, 4.6, False, False),
            ("Codex mem.", 2.4, -5.7, False, False),
            ("GEPA", -4.0, 14.9, False, False),
            ("Meta-H.", -12.2, 6.6, False, False),
        ],
    },
    "agents": {  # Figure 6
        "eog": [
            ("Deploy", None, 9.5, False, True),
            ("Claude Code", None, 4.6, False, True),
            ("Codex mem.", -1.5, -2.8, True, True),
            ("GEPA", 14.3, 6.4, True, True),
            ("Meta-H.", 8.8, 5.5, True, True),
        ],
        "ale": [
            ("Deploy", None, -34.7, False, False),
            ("Claude Code", None, 1.8, False, False),
            ("Codex mem.", -14.1, -24.1, False, False),
            ("GEPA", 7.9, -7.9, False, False),
            ("Meta-H.", -0.9, -21.6, False, False),
        ],
    },
}

READ = """axis => [...document.querySelectorAll(
    `[data-xfer="${axis}"] .xfer-col`)].map(c => {
  const lab = c.querySelector('.xfer-lab');
  const half = s => [...c.querySelectorAll(`.xfer-half.${s} .xfer-bar`)].map(b => ({
    kind: b.classList.contains('fwt') ? 'fwt' : 'bwt',
    na: b.classList.contains('is-na'),
    zero: b.classList.contains('is-zero'),
    h: Math.round(b.getBoundingClientRect().height),
    title: b.getAttribute('title'),
  }));
  return {
    name: lab.firstChild.textContent.trim(),
    text: lab.textContent.replace(/\\s+/g, ' ').trim(),
    dag: [...lab.querySelectorAll('.xfer-dag')].length,
    up: half('is-up'),
    dn: half('is-dn'),
  };
})"""


def num(v) -> str:
    return "\u2014" if v is None else f"{v:.1f}"


def check(cols: list[dict], want: list[tuple], where: str) -> list[str]:
    """Compare one rendered panel against the figure it comes from."""
    bad: list[str] = []
    if len(cols) != len(want):
        got = ", ".join(c["name"] for c in cols) or "nothing"
        return [f"{where}: figure has {len(want)} methods "
                f"({', '.join(w[0] for w in want)}), page draws {len(cols)}: {got}"]

    seen: dict[float, int] = {}
    for col, (name, fwt, bwt, fdag, bdag) in zip(cols, want):
        if col["name"] != name:
            bad.append(f"{where}: expected {name!r} in this slot, got {col['name']!r}")
            continue
        bars = {b["kind"]: b for b in col["up"] + col["dn"]}
        sides = {b["kind"]: ("up" if b in col["up"] else "dn")
                 for b in col["up"] + col["dn"]}
        for kind, v, dag in (("fwt", fwt, fdag), ("bwt", bwt, bdag)):
            b = bars.get(kind)
            if b is None:
                bad.append(f"{where}/{name}: no {kind.upper()} mark at all")
                continue
            if v is None:
                if not b["na"]:
                    bad.append(f"{where}/{name}: {kind.upper()} is not reported in the "
                               f"figure but the page draws a bar ({b['title']})")
                continue
            if b["na"]:
                bad.append(f"{where}/{name}: figure reports {kind.upper()} {num(v)} "
                           f"but the page draws a not-reported stub")
                continue
            if f"{kind.upper()} {num(v)}" not in (b["title"] or ""):
                bad.append(f"{where}/{name}: {kind.upper()} reads {b['title']!r}, "
                           f"figure says {num(v)}")
            if f"{kind.upper()} {num(v)}" not in col["text"]:
                bad.append(f"{where}/{name}: label {col['text']!r} omits "
                           f"{kind.upper()} {num(v)}")
            # Sign is carried by direction, so a wrong side is a wrong number.
            want_side = "dn" if v < 0 else "up"
            if v and sides[kind] != want_side:
                bad.append(f"{where}/{name}: {kind.upper()} {num(v)} draws "
                           f"{sides[kind]} from the axis, should be {want_side}")
            if (v == 0) is not b["zero"]:
                bad.append(f"{where}/{name}: {kind.upper()} {num(v)} "
                           f"{'should' if v == 0 else 'should not'} be the flat mark")
            # One scale per panel: equal magnitudes have to come out equal.
            if v and not b["zero"]:
                prev = seen.setdefault(abs(v), b["h"])
                if abs(prev - b["h"]) > 1:
                    bad.append(f"{where}/{name}: {kind.upper()} {num(v)} is {b['h']}px "
                               f"where the same magnitude is {prev}px elsewhere")
            # The dagger qualifies the number it trails, so it has to sit on the
            # values the figure marks and nowhere else.
            m = re.search(rf"{kind.upper()} {re.escape(num(v))}({DAG})?", col["text"])
            if bool(m and m.group(1)) is not dag:
                bad.append(f"{where}/{name}: {kind.upper()} {num(v)} "
                           f"{'lacks' if dag else 'invents'} the dagger")

    want_dag = sum(bool(fdag and fwt is not None) + bool(bdag and bwt is not None)
                   for _n, fwt, bwt, fdag, bdag in want)
    got_dag = sum(c["dag"] for c in cols)
    if got_dag != want_dag:
        bad.append(f"{where}: figure marks {want_dag} values with a dagger, page shows {got_dag}")
    return bad


def main() -> None:
    fails: list[str] = []
    errs: list[str] = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 1100}, device_scale_factor=2)
        pg.on("console", lambda m: m.type == "error"
              and "ERR_FILE_NOT_FOUND" not in m.text and errs.append(m.text))
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto((ROOT / "index.html").as_uri())
        pg.click('.pv-tab[data-pv="results"]')

        for axis, envs in FIG.items():
            pg.click(f'.rs-tab[data-rs="{axis}"]')
            for env, want in envs.items():
                # Each panel carries two copies of the toggle, one per chart, and
                # both repaint the whole axis; either one will do.
                pg.locator(f'[data-env="{axis}"] button[data-env-key="{env}"]').first.click()
                pg.wait_for_timeout(150)
                cols = pg.evaluate(READ, axis)
                where = f"{axis}/{env}"
                fails += check(cols, want, where)

                cap = pg.eval_on_selector(f'[data-xfer="{axis}"] .chart-cap',
                                          "n => n.textContent")
                has = any(w[3] or w[4] for w in want)
                if ("disagree" in cap) is not has:
                    fails.append(f"{where}: caption "
                                 f"{'omits' if has else 'offers'} the dagger note")
                html = pg.eval_on_selector(f'[data-xfer="{axis}"]', "n => n.innerHTML")
                for junk in ("NaN", "Infinity", "undefined"):
                    if junk in html:
                        fails.append(f"{where}: {junk} in the chart")

                shot = pg.query_selector(f'[data-xfer="{axis}"]')
                shot.screenshot(path=str(OUT / f"{axis}-{env}.png"))
                print(f"\n{where}  ({len(cols)} methods)")
                for c in cols:
                    print(f"    {c['text']}")

        # The narrow arm is where five methods have to fit a phone column.
        pg.set_viewport_size({"width": 430, "height": 1100})
        pg.click('.rs-tab[data-rs="agents"]')
        pg.wait_for_timeout(200)
        wrap = pg.query_selector('[data-xfer="agents"]')
        wrap.screenshot(path=str(OUT / "agents-narrow.png"))
        over = pg.evaluate("""() => {
          const w = document.querySelector('[data-xfer="agents"] .xfer-bars');
          const labs = [...w.querySelectorAll('.xfer-lab')];
          return {
            hscroll: w.scrollWidth - w.clientWidth,
            clipped: labs.filter(l => l.scrollHeight > l.clientHeight + 1).length,
          };
        }""")
        if over["hscroll"] > 1:
            fails.append(f"agents narrow: chart overflows by {over['hscroll']}px")
        if over["clipped"]:
            fails.append(f"agents narrow: {over['clipped']} labels clipped")
        print(f"\nnarrow (430px): overflow {over['hscroll']}px, "
              f"clipped labels {over['clipped']}")
        b.close()

    fails += [f"console error: {e}" for e in errs]
    print(f"\nwrote shots to {OUT}")
    for f in fails:
        print(f"  FAIL  {f}")
    if fails:
        raise SystemExit(1)
    n = sum(len(w) for e in FIG.values() for w in e.values())
    print(f"\nall {n} method columns match the figures they come from")


if __name__ == "__main__":
    main()
