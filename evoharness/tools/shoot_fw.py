#!/usr/bin/env python3
"""Shoot the outer/inner figure and check the loop actually closes.

The two legs that carry z_t are drawn over the bands, so their endpoints are
measured rather than laid out. That is worth checking as geometry and not only
as a picture: a leg has to leave the node it belongs to, land on the band it
writes to, and stay inside the figure. Both modes and several widths, since the
overlay stands down when the loop row wraps and the .fw-fb line takes over.
"""
from __future__ import annotations

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "tools" / "proofs" / "fw"
OUT.mkdir(parents=True, exist_ok=True)

GEO = """() => {
  const fw = document.querySelector('#fw');
  const r = s => { const n = fw.querySelector(s); if (!n) return null;
    const b = n.getBoundingClientRect(); const f = fw.getBoundingClientRect();
    return {l: b.left - f.left, r: b.right - f.left, t: b.top - f.top,
            b: b.bottom - f.top, w: b.width, h: b.height}; };
  const lab = s => (fw.querySelector(s + ' .fw-riser-lab') || {}).textContent;
  return {
    looped: fw.classList.contains('is-looped'),
    fbShown: !!fw.querySelector('.fw-fb')?.offsetParent,
    box: r('.fw-band--outer') && fw.getBoundingClientRect().width,
    task: r('.fw-loop .fw-node'), env: r('.fw-node--env'),
    z: r('.fw-band--across'),
    w: r('.fw-riser--w'), rr: r('.fw-riser--r'),
    wLab: lab('.fw-riser--w'), rLab: lab('.fw-riser--r'),
    labs: [...fw.querySelectorAll('.fw-riser-lab')].map(n => {
      const b = n.getBoundingClientRect(), f = fw.getBoundingClientRect();
      return {l: b.left - f.left, r: b.right - f.left, w: b.width};
    }),
  };
}"""


def check(g: dict, where: str, width: int) -> list[str]:
    bad: list[str] = []
    if not g["looped"]:
        # Standing down is a valid state; the words have to be there instead.
        if not g["fbShown"]:
            bad.append(f"{where}: loop not drawn and the feedback line is hidden too")
        return bad
    if g["fbShown"]:
        bad.append(f"{where}: loop drawn and the feedback line still doubles it")
    task, env, z, w, rr = g["task"], g["env"], g["z"], g["w"], g["rr"]
    # Each leg leaves the node it belongs to, on its centre.
    for name, leg, node in (("write", w, env), ("read", rr, task)):
        mid = (node["l"] + node["r"]) / 2
        got = (leg["l"] + leg["r"]) / 2
        if abs(got - mid) > 2:
            bad.append(f"{where}: {name} leg is at x={got:.0f}, "
                       f"its node's centre is x={mid:.0f}")
    # The write leg runs from the environment down onto the band; the read leg
    # from the band back up to the task. Both must span that gap, not float in it.
    if not (env["b"] <= w["t"] <= env["b"] + 8):
        bad.append(f"{where}: write leg starts at y={w['t']:.0f}, "
                   f"environment ends at y={env['b']:.0f}")
    if not (z["t"] - 12 <= w["b"] <= z["t"]):
        bad.append(f"{where}: write leg ends at y={w['b']:.0f}, "
                   f"the state band starts at y={z['t']:.0f}")
    if not (task["b"] <= rr["t"] <= task["b"] + 16):
        bad.append(f"{where}: read leg ends at y={rr['t']:.0f}, "
                   f"the task ends at y={task['b']:.0f}")
    if abs(rr["b"] - z["t"]) > 1:
        bad.append(f"{where}: read leg starts at y={rr['b']:.0f}, "
                   f"the state band starts at y={z['t']:.0f}")
    if w["h"] < 12 or rr["h"] < 12:
        bad.append(f"{where}: legs are {w['h']:.0f}px and {rr['h']:.0f}px, too short to read")
    # The return leg is labelled and the write leg deliberately is not.
    if g["wLab"] is not None:
        bad.append(f"{where}: the write leg carries a label again: {g['wLab']!r}")
    if g["rLab"] != "carried across stage":
        bad.append(f"{where}: return leg reads {g['rLab']!r}")
    if len(g["labs"]) != 1:
        return bad + [f"{where}: {len(g['labs'])} labels drawn, expected 1"]
    # It has to fit the figure and stop short of the leg it points across to.
    lb = g["labs"][0]
    if lb["l"] < 0 or lb["r"] > g["box"]:
        bad.append(f"{where}: the label runs from {lb['l']:.0f} to {lb['r']:.0f} "
                   f"in a {g['box']:.0f}px figure")
    if lb["r"] > w["l"] - 8:
        bad.append(f"{where}: the label reaches x={lb['r']:.0f}, "
                   f"into the write leg at x={w['l']:.0f}")
    return bad


def main() -> None:
    fails: list[str] = []
    errs: list[str] = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 1200}, device_scale_factor=2)
        pg.on("console", lambda m: m.type == "error"
              and "ERR_FILE_NOT_FOUND" not in m.text and errs.append(m.text))
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto((ROOT / "index.html").as_uri())
        pg.click('.pv-tab[data-pv="benchmark"]')   # the figure lives here
        pg.wait_for_timeout(400)

        for width in (1280, 980, 760, 560, 430):
            pg.set_viewport_size({"width": width, "height": 1200})
            pg.wait_for_timeout(300)
            for mode in ("adapt", "deploy"):
                pg.click(f'.fw-mode[data-fw="{mode}"]')
                pg.wait_for_timeout(250)
                g = pg.evaluate(GEO)
                where = f"{width}px/{mode}"
                fails += check(g, where, width)
                print(f"{where:>14}  drawn={g['looped']}  words={g['fbShown']}"
                      + (f"  legs {g['w']['h']:.0f}px / {g['rr']['h']:.0f}px"
                         if g["looped"] else ""))
                if mode == "adapt" or width == 1280:
                    pg.query_selector(".fw-figure").screenshot(
                        path=str(OUT / f"fw-{width}-{mode}.png"))
            pg.click('.fw-mode[data-fw="adapt"]')

        # Leaving the figure and coming back must not leave the legs stale.
        pg.set_viewport_size({"width": 1280, "height": 1200})
        pg.click(".lp-next")
        pg.wait_for_timeout(300)
        pg.click(".lp-prev")
        pg.wait_for_timeout(300)
        g = pg.evaluate(GEO)
        fails += check(g, "after a round trip", 1280)
        print(f"\nafter a round trip through page 2: drawn={g['looped']}")
        b.close()

    fails += [f"console error: {e}" for e in errs]
    print(f"\nwrote shots to {OUT}")
    for f in fails:
        print(f"  FAIL  {f}")
    if fails:
        sys.exit(1)
    print("the loop closes at every width that draws it")


if __name__ == "__main__":
    main()
