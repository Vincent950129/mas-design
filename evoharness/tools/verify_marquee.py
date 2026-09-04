#!/usr/bin/env python3
"""Check the drifting band on the overview tab.

A band that moves has more ways to be wrong than a static one, and most of them
are invisible in a screenshot: the wrap can jump once a cycle, lazily loaded
thumbnails can stay blank as they drift in, the duplicate copy can put 18 extra
buttons in the tab order, and the motion can ignore a reader who asked for none.
Each of those is checked here against the rendered page.

The last check is the one that matters most: a panel is a promise that there is a
task behind it, so clicking one has to land on that task and not merely on the
gallery.
"""
from __future__ import annotations

import collections
import functools
import http.server
import json
import pathlib
import socketserver
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT.parent
MANIFEST = ROOT / "static" / "marquee.json"
PAGE = "/evoharness/index.html"
OUT = ROOT / "tools" / "proofs" / "marquee"
OUT.mkdir(parents=True, exist_ok=True)

fails: list[str] = []
checks = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global checks
    checks += 1
    print(f"  {'ok  ' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        fails.append(label)


def offered() -> dict[str, set[int]]:
    """Which stages each environment could put a figure at, read from the corpus.

    A stage the band shows in one environment only is either a selection bug or a
    fact about the corpus -- EnterpriseOps-Gym has no sandbox whose task waits until
    stage 5 -- and the two want telling apart.
    """
    d = json.loads((ROOT / "static" / "tasks.json").read_text())
    first: dict[str, int] = {}
    for r in d["tasks"]:
        tid, st = r[7], r[6]
        first[tid] = min(st, first.get(tid, st))
    out = {"ale": {first[t] for t in d["aleFigures"] if t in first}, "eog": set()}
    starts: dict[str, list[str]] = collections.defaultdict(list)
    for tid, envs in d["taskEnvs"].items():
        for e in envs:
            starts[e].append(tid)
    for eid in d["envFigures"]:
        ts = [first[t] for t in starts.get(eid, []) if t in first]
        if ts:
            out["eog"].add(min(ts))
    return out


def harness() -> dict[str, dict[str, dict]]:
    """What the corpus says each task is handed at the stage it enters.

    Read back from tasks.json the long way round -- pool the whole of every stream,
    then subtract the stages before -- so a panel claiming "+51 tools" is checked
    against the corpus rather than against the script that wrote the claim.
    """
    d = json.loads((ROOT / "static" / "tasks.json").read_text())
    nm = lambda i: set(d["names"][j] for j in d["lists"][i]) if i >= 0 else set()
    key = lambda r: (d["envs"][r[1]], d["domains"][r[2]], d["tracks"][r[0]])

    pool: dict[tuple, dict[int, set[str]]] = collections.defaultdict(
        lambda: collections.defaultdict(set))
    rows: dict[str, list] = collections.defaultdict(list)
    for r in d["tasks"]:
        pool[key(r)][r[6]] |= nm(r[13])
        rows[r[7]].append(r)

    out: dict[str, dict[str, dict]] = {}
    for tid, rs in rows.items():
        st = min(r[6] for r in rs)
        out[tid] = {}
        for r in (r for r in rs if r[6] == st):
            stages = pool[key(r)]
            before = set().union(*[v for s, v in stages.items() if s < st] or [set()])
            out[tid][d["tracks"][r[0]]] = {
                "pool": len(stages[st]), "new": len(stages[st] - before),
                "need": len(nm(r[12])), "first": not before,
                "fresh": stages[st] - before, "all": stages[st],
            }
    return out


def expect(h: dict) -> str:
    """The pill a panel should be showing, worked out from the manifest."""
    unit = lambda n, ax: ax[:-1] if n == 1 else ax
    if h["first"]:
        return f"{h['pool']} {unit(h['pool'], h['ax'])} to start"
    if h["new"]:
        return f"+{h['new']} {unit(h['new'], h['ax'])}"
    return f"{h['pool']} {unit(h['pool'], h['ax'])} in the pool"


def serve() -> tuple[socketserver.TCPServer, str]:
    """The band fetches its manifest, so file:// will not do."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
    srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}{PAGE}"


READ = """() => {
  const band = document.querySelector('[data-mq]');
  const track = document.querySelector('[data-mq-track]');
  const ps = [...track.querySelectorAll('.mq-panel')];
  const cs = getComputedStyle(track);
  return {
    hidden: band.hidden,
    n: ps.length,
    dup: ps.filter(p => p.getAttribute('aria-hidden') === 'true').length,
    tabbable: ps.filter(p => p.tabIndex >= 0).length,
    anim: cs.animationName,
    dur: parseFloat(cs.animationDuration),
    half: track.scrollWidth / 2,
    overflow: getComputedStyle(band).overflowX,
    tids: ps.map(p => p.dataset.tid),
    labs: ps.map(p => p.querySelector('.mq-lab').textContent),
    stages: ps.map(p => p.querySelector('.mq-st').textContent),
    gains: ps.map(p => p.querySelector('.mq-gain').textContent.trim()),
    items: ps.map(p => [...p.querySelectorAll('.mq-item')].map(i => i.textContent)),
    // A name sliced down the middle would read as a bug. The strip is one row high, so a
    // name that does not fit wraps out of sight entirely -- that is fine, and does not
    // touch the visible row. What is not fine is a chip straddling the edge. Measured in
    // layout offsets rather than client rects, which the panels' 3D tilt would project.
    sliced: ps.reduce((n, p) => {
      const s = p.querySelector('.mq-harn');
      return n + [...p.querySelectorAll('.mq-gain, .mq-item')].filter((c) => {
        const y = c.offsetTop - s.offsetTop, x = c.offsetLeft - s.offsetLeft;
        const shows = y < s.clientHeight - 1;
        const whole = y + c.offsetHeight <= s.clientHeight + 1
          && x + c.offsetWidth <= s.clientWidth + 1 && x >= -1;
        return c.offsetWidth > 0 && shows && !whole;
      }).length;
    }, 0),
    // Where the second copy starts: the wrap is seamless only if that is the
    // exact distance the animation travels.
    copy2: ps.length > 1 ? ps[ps.length / 2 | 0].offsetLeft : null,
    imgs: ps.map(p => {
      const i = p.querySelector('img');
      const r = i.getBoundingClientRect();
      return {
        w: i.naturalWidth,
        seen: r.right > 0 && r.left < innerWidth && r.bottom > 0 && r.top < innerHeight,
      };
    }),
  };
}"""


def main() -> None:
    print("Manifest")
    panels = json.loads(MANIFEST.read_text())
    check(len(panels) >= 12, "enough panels to fill a band", f"{len(panels)}")
    need = ("src", "w", "h", "lab", "tid", "title", "st", "env")
    thin = [p.get("tid", "?") for p in panels if any(not p.get(k) for k in need)]
    check(not thin, "every panel carries figure, label, stage and task", str(thin[:3]))
    gone = [p["src"] for p in panels if not (ROOT / p["src"]).exists()]
    check(not gone, "every figure file is on disk", str(gone[:3]))
    kb = sum((ROOT / p["src"]).stat().st_size for p in panels) / 1024
    check(kb < 600, "the band's thumbnails stay small", f"{kb:.0f} KB for {len(panels)}")
    envs = {p["env"] for p in panels}
    check(envs == {"ale", "eog"}, "both environments are in the band", str(sorted(envs)))
    check(len({p["lab"] for p in panels}) >= len(panels) // 2,
          "labels are varied rather than one discipline repeated",
          f"{len({p['lab'] for p in panels})} distinct in {len(panels)}")
    dupes = [t for t, n in collections.Counter(p["title"] for p in panels).items() if n > 1]
    check(not dupes, "no task is in the band twice", str(dupes[:2]))

    # The order is the point of the band: drift runs leftwards, so panels have to be
    # laid down earliest stage first for what arrives to be what comes later.
    sts = [p["st"] for p in panels]
    back = [(a, b) for a, b in zip(sts, sts[1:]) if b < a]
    check(not back, "the stages never go backwards along the band", str(back[:3]))
    per = collections.Counter(sts)
    check(len(per) >= 5, "the band reaches across the stages", str(dict(sorted(per.items()))))
    check(max(per.values()) <= len(panels) // 3,
          "no single stage takes over the band",
          f"{max(per.values())} at most, of {len(panels)}")
    # A stage held by one environment is a run of near-identical panels, unless the
    # other environment has nothing to put there.
    can = offered()
    solo = []
    for st, n in per.items():
        got = {p["env"] for p in panels if p["st"] == st}
        if n > 2 and len(got) == 1:
            missing = ({"ale", "eog"} - got).pop()
            if st in can[missing]:
                solo.append(f"stage {st} is all {got.pop()}")
    check(not solo, "no crowded stage is left holding one environment for no reason",
          str(solo))

    # The harness is the dimension that separates this corpus from a task gallery, so
    # what a panel says about it has to hold against the corpus.
    print("\nThe harness on each panel")
    truth = harness()
    wrong = []
    for p in panels:
        h, t = p["hx"], truth.get(p["tid"], {}).get(p.get("hx", {}).get("ax"))
        if not t or any(h[k] != t[k] for k in ("pool", "new", "need", "first")):
            wrong.append(f"{p['tid']} {h.get('ax')}")
    check(not wrong, "every panel's pool, gain and need are the corpus's numbers",
          str(wrong[:3]))
    axed = [p["tid"] for p in panels if p["hx"]["ax"] not in truth.get(p["tid"], {})]
    check(not axed, "each panel speaks for an axis its task is actually graded on", str(axed[:3]))
    best = [p["tid"] for p in panels
            if p["hx"]["new"] < max(a["new"] for a in truth[p["tid"]].values())]
    check(not best, "and for the axis that grew the most where the task enters", str(best[:3]))
    named = [p["tid"] for p in panels if not p["hx"]["items"]]
    check(not named, "every panel names something out of the harness", str(named[:3]))
    stray = [p["tid"] for p in panels
             if not set(p["hx"]["items"]) <= truth[p["tid"]][p["hx"]["ax"]]["all"]]
    check(not stray, "the names it puts up are in that task's pool", str(stray[:3]))
    stale = [p["tid"] for p in panels if p["hx"]["new"]
             and not set(p["hx"]["items"]) <= truth[p["tid"]][p["hx"]["ax"]]["fresh"]]
    check(not stale, "and where the harness grew, they are what it grew by", str(stale[:3]))
    grew = sum(p["hx"]["new"] > 0 for p in panels)
    check(grew >= len(panels) // 2,
          "most panels have a gain to show rather than a bare count", f"{grew} of {len(panels)}")

    srv, url = serve()
    errs: list[str] = []
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
            pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(url)
            pg.wait_for_selector("[data-mq] .mq-panel")
            # The band sits just under the hero, so it is what the first scroll
            # reaches rather than what the landing viewport shows.
            pg.locator("[data-mq]").scroll_into_view_if_needed()
            pg.wait_for_timeout(700)
            g = pg.evaluate(READ)

            print("\nWhat is on screen")
            check(not g["hidden"], "the band is shown once the manifest lands")
            check(g["n"] == 2 * len(panels), "the panels are laid down twice, for the wrap",
                  f"{g['n']} for {len(panels)} panels")
            check(g["dup"] == len(panels) and g["tabbable"] == len(panels),
                  "only the first copy is reachable by keyboard or screen reader",
                  f"{g['tabbable']} tabbable, {g['dup']} hidden")
            check(g["tids"][:len(panels)] == [p["tid"] for p in panels],
                  "panels are in manifest order and carry their task ids")
            check(g["labs"][0] == panels[0]["lab"]
                  and g["stages"][0] == f"stage {panels[0]['st']}",
                  "a panel shows its own label and stage, in words",
                  f"{g['labs'][0]!r} {g['stages'][0]!r}")
            shown = [int(s.split()[-1]) for s in g["stages"][:len(panels)]]
            check(shown == sorted(shown),
                  "the badges read forwards through the stages, left to right",
                  f"{shown[0]} to {shown[-1]}")
            want = [expect(p["hx"]) for p in panels]
            check(g["gains"][:len(panels)] == want,
                  "and each panel says what the harness hands it there",
                  f"{g['gains'][0]!r} then {g['gains'][4]!r}")
            check(g["items"][:len(panels)] == [p["hx"]["items"] for p in panels],
                  "with the harness it names",
                  f"{g['items'][0]}")
            check(g["sliced"] == 0, "and nothing in that strip is cut in half",
                  f"{g['sliced']} clipped")

            print("\nMotion")
            check(g["anim"] == "mqDrift", "the track is animated", g["anim"])
            check(abs(g["copy2"] - g["half"]) <= 1,
                  "the animation travels exactly one copy, so the wrap cannot jump",
                  f"copy 2 starts at {g['copy2']:.1f}px, half the track is {g['half']:.1f}px")
            want = g["half"] / 42
            check(abs(g["dur"] - want) < max(2.0, want * 0.05),
                  "a lap is timed from the width it came out at",
                  f"{g['dur']:.0f}s for {g['half']:.0f}px")
            x0 = pg.eval_on_selector(".mq-panel", "n => n.getBoundingClientRect().left")
            pg.wait_for_timeout(1500)
            x1 = pg.eval_on_selector(".mq-panel", "n => n.getBoundingClientRect().left")
            check(x0 - x1 > 20, "and it is actually drifting", f"{x0 - x1:.0f}px in 1.5s")
            pg.hover("[data-mq]")
            pg.wait_for_timeout(150)
            paused = pg.eval_on_selector("[data-mq-track]",
                                         "n => getComputedStyle(n).animationPlayState")
            xh = pg.eval_on_selector(".mq-panel", "n => n.getBoundingClientRect().left")
            pg.wait_for_timeout(600)
            xh2 = pg.eval_on_selector(".mq-panel", "n => n.getBoundingClientRect().left")
            check(paused == "paused" and abs(xh - xh2) < 1,
                  "it holds still while pointed at", f"{paused}, moved {abs(xh - xh2):.1f}px")
            pg.mouse.move(0, 0)
            pg.eval_on_selector(".mq-panel", "n => n.focus()")
            pg.wait_for_timeout(150)
            check(pg.eval_on_selector("[data-mq-track]",
                                      "n => getComputedStyle(n).animationPlayState") == "paused",
                  "and while a panel has keyboard focus")

            print("\nThumbnails")
            seen = [i for i in g["imgs"] if i["seen"]]
            check(len(seen) >= 3, "several panels are on screen at once", f"{len(seen)}")
            check(all(i["w"] > 0 for i in seen), "and every one of those has decoded",
                  f"{sum(1 for i in seen if not i['w'])} blank")
            # Drag the track along by hand: a panel that drifts in has to arrive
            # with its figure, not as an empty frame.
            pg.evaluate("""() => { const t = document.querySelector('[data-mq-track]');
              t.style.animation = 'none';
              t.style.transform = `translate3d(-${t.scrollWidth / 4}px,0,0)`; }""")
            pg.wait_for_timeout(1200)
            g2 = pg.evaluate(READ)
            late = [i for i in g2["imgs"] if i["seen"]]
            check(all(i["w"] > 0 for i in late),
                  "panels that drift in later arrive loaded",
                  f"{sum(1 for i in late if not i['w'])} of {len(late)} blank")
            pg.reload()
            pg.wait_for_selector("[data-mq] .mq-panel")
            pg.wait_for_timeout(600)
            pg.locator("[data-mq]").screenshot(path=str(OUT / "band.png"))
            pg.wait_for_timeout(2500)
            pg.locator("[data-mq]").screenshot(path=str(OUT / "band-later.png"))

            print("\nA panel leads to its task")
            want_tid, want_title = panels[2]["tid"], panels[2]["title"]
            # A moving target is not clickable, for the reader or for playwright:
            # entering the band is what stops it, so do that first.
            pg.hover("[data-mq]")
            pg.wait_for_timeout(250)
            pg.locator(f'.mq-panel[data-tid="{want_tid}"]').first.click()
            pg.wait_for_selector('[data-pv-view="tasks"].is-active')
            pg.wait_for_function(
                """t => { const q = document.querySelector('[data-pv-view="tasks"] .cs-q');
                    return q && q.value === t; }""", arg=want_tid, timeout=15000)
            pg.wait_for_timeout(900)
            got = pg.evaluate("""() => ({
              q: document.querySelector('[data-pv-view="tasks"] .cs-q').value,
              count: document.querySelector('[data-tg-count]').textContent.trim(),
              cards: [...document.querySelectorAll('[data-tg-grid] .tg-card')]
                .map(c => c.querySelector('.tg-ttl').textContent),
            })""")
            check(got["q"] == want_tid, "the gallery opens searching that task", got["q"])
            check(bool(got["cards"]), "and finds it", got["count"])
            check(got["cards"][:1] == [want_title],
                  "the card that comes back is the task whose figure was clicked",
                  f"{got['cards'][:1]} vs {[want_title]}")
            pg.locator("#tasks").screenshot(path=str(OUT / "landed.png"))
            pg.close()

            print("\nWhen motion is unwelcome")
            ctx = b.new_context(viewport={"width": 1280, "height": 900},
                                reduced_motion="reduce")
            p2 = ctx.new_page()
            p2.on("pageerror", lambda e: errs.append(str(e)))
            p2.goto(url)
            p2.wait_for_selector("[data-mq] .mq-panel")
            p2.wait_for_timeout(500)
            r = p2.evaluate(READ)
            check(r["n"] == len(panels), "the band is laid down once, not twice",
                  f"{r['n']} panels")
            check(r["anim"] == "none", "nothing animates", r["anim"])
            check(r["overflow"] == "auto", "and it can be scrolled by hand instead",
                  r["overflow"])
            p2.locator("[data-mq]").screenshot(path=str(OUT / "band-still.png"))
            ctx.close()
            b.close()
    finally:
        srv.shutdown()

    print("\nQuiet")
    check(not errs, "no console errors", str(errs[:2]))

    print(f"\nshots -> {OUT}")
    print(f"\n{checks - len(fails)}/{checks} checks passed")
    if fails:
        for f in fails:
            print(f"  FAIL  {f}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
