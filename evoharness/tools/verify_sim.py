#!/usr/bin/env python3
"""Check the floor under the band: four systems running inside a stage.

The band says the harness moves. The floor is the claim that follows from it -- that a
system running underneath has to answer for the movement -- and it makes two assertions a
screenshot cannot check. One is that the numbers are the corpus's: the stage, the pool and
the capability names on the floor are the same ones the panel that drops is carrying, not
decoration. The other is the difference between the two evaluation modes, which exists for
about three seconds each cycle: at the boundary the deployment trays empty and z_t does not.

Both are checked here against the rendered page, along with the things an animation gets
wrong quietly -- a clock that keeps running behind a tab nobody is looking at, a pause
button that pauses the phases but not the motion, and a reader who asked for no motion at
all being given some anyway.
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "tools/proofs"
BASE = "http://127.0.0.1:8777/evoharness/index.html"
# The families, in the order the floor lays them out, with the mode each is evaluated under:
# three that start a stage clean and the one that carries state. Families and not products --
# the floor may not name a particular agent as one of its four, because any system that takes
# a harness can be run and the paper's own are examples, not the taxonomy.
WANT = [("Single agent", "deployment"), ("Agent with memory", "self-evolving"),
        ("Centralized MAS", "deployment"), ("Decentralized MAS", "deployment")]
PRODUCTS = ("ReAct", "Codex", "AutoGen", "DeLM", "Raw Memory", "G-Memory", "Claude")

fails: list[str] = []
checks = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global checks
    checks += 1
    print(f"  {'ok  ' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        fails.append(label + (f": {detail}" if detail else ""))


STATE = """() => {
  const box = (g) => ({ax: g.dataset.ax, n: g.querySelector('text').textContent});
  const cards = [...document.querySelectorAll('.sim-card')].map((c) => ({
    name: c.querySelector('.sim-card-h b').textContent.trim(),
    eg: c.querySelector('.sim-eg').textContent.trim(),
    mode: c.dataset.mode,
    head: Math.round(c.querySelector('.sim-card-h').getBoundingClientRect().height),
    clip: [...c.querySelectorAll('.sim-card-h span')]
      .some((e) => e.scrollWidth > e.clientWidth + 1),
    caps: [...c.querySelectorAll('.sn-cap')].map(box),
    fresh: [...c.querySelectorAll('.sn-cap.is-new')].map(box),
    on: c.querySelectorAll('.sim-marks i.is-on').length,
    stale: c.querySelectorAll('.sim-marks i.is-stale').length,
    note: c.querySelector('[data-note]').textContent.trim(),
  }));
  const s = document.querySelector('[data-sim]');
  const mets = {};
  s.querySelectorAll('[data-met]').forEach((m) => { mets[m.dataset.met] = m.textContent; });
  const lives = [...s.querySelectorAll('[data-met].is-live')].map((m) => m.dataset.met);
  const nodes = [...document.querySelectorAll('.sn:not(.sn-cap) text')]
    .map((t) => t.textContent.trim());
  // Which way the traffic runs on the single-agent card, and how a capability is drawn.
  const one = document.querySelector('.sim-card[data-sys="sas"]');
  const out = [...one.querySelectorAll('.sf')]
    .filter((l) => +l.getAttribute('x1') < +l.getAttribute('x2')).length;
  const rect = document.querySelector('.sn-cap rect');
  const look = {out, back: one.querySelectorAll('.sf').length - out,
                rx: parseFloat(getComputedStyle(rect).rx) || 0,
                dash: getComputedStyle(rect).strokeDasharray};
  return {phase: s.dataset.phase, nodes, lives, look,
          st: s.querySelector('[data-st]').textContent.trim(),
          mets, axes: [...s.querySelectorAll('[data-met]')].map((m) => m.dataset.met),
          say: s.querySelector('[data-say]').innerText.trim(),
          held: s.classList.contains('is-held'), cards};
}"""


def corpus() -> dict[tuple, dict[int, set[str]]]:
    """Every stream in the corpus, as the pool it offers at each of its stages.

    Read straight out of tasks.json rather than through the dumper that wrote the floor's
    ladder, so the two have to agree on their own.
    """
    d = json.loads((ROOT / "static/tasks.json").read_text())
    out: dict[tuple, dict[int, set[str]]] = collections.defaultdict(
        lambda: collections.defaultdict(set))
    for r in d["tasks"]:
        key = (d["envs"][r[1]], d["domains"][r[2]], d["tracks"][r[0]])
        if r[13] >= 0:
            out[key][r[6]] |= {d["names"][j] for j in d["lists"][r[13]]}
    return out


def watch(pg, want: str, limit: float = 20.0) -> dict:
    """Wait for the next time the floor is in `want`, and read it there."""
    end = time.time() + limit
    while time.time() < end:
        s = pg.evaluate(STATE)
        if s["phase"] == want:
            return s
        pg.wait_for_timeout(90)
    return {"phase": "timed out", "cards": [], "st": "", "pool": "", "say": "", "held": False}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    lads = json.loads((ROOT / "static/stream.json").read_text())
    pools = corpus()
    # What the floor can legally show on an axis meter: a stage of that axis's stream, and
    # the pool it offers there. And, for the boxes, the capability it releases there.
    rungs = {(s["ax"], r["st"], r["pool"]) for s in lads for r in s["rungs"]}
    bank = {(s["ax"], r["st"]): r["items"] for s in lads for r in s["rungs"]}
    names = {n for s in lads for r in s["rungs"] for n in r["items"]}
    # The paper reads tools, skills, agents, and the floor's meters and its rows of boxes
    # both have to, or a colour means one thing in the header and another underneath it.
    AXES = ["tools", "skills", "agents"]
    errs: list[str] = []

    print("\nThe stream the floor climbs")
    check(len(lads) >= 2, f"{len(lads)} streams, so the floor is not one loop of one stream",
          ", ".join(f"{s['lab']} {s['ax']}" for s in lads))
    for s in lads:
        stages = [r["st"] for r in s["rungs"]]
        got = pools.get((s["env"], s["dom"], s["ax"]), {})
        tag = f"{s['lab']} {s['ax']}"
        check(stages == list(range(stages[0], stages[0] + len(stages))),
              f"{tag}: the stages are contiguous", str(stages))
        # The outer loop is a nested sequence H_1 subset of H_2 ...: a pool that ever
        # shrinks is not the thing the paper is describing.
        check(all(b["pool"] > a["pool"] for a, b in zip(s["rungs"], s["rungs"][1:])),
              f"{tag}: the pool only ever grows",
              " -> ".join(str(r["pool"]) for r in s["rungs"]))
        check(all(r["pool"] == len(got.get(r["st"], ())) for r in s["rungs"]),
              f"{tag}: and every count is the corpus's own",
              str([(r["pool"], len(got.get(r["st"], ()))) for r in s["rungs"]]))
        # A named capability has to be one that actually arrived at that stage, or the
        # floor is announcing releases the corpus never made.
        seen: set[str] = set()
        bad = []
        for r in s["rungs"]:
            fresh = got.get(r["st"], set()) - seen
            seen |= got.get(r["st"], set())
            bad += [n for n in r["items"] if n not in fresh]
        check(not bad, f"{tag}: and every name arrives at the stage it is announced at",
              str(bad))

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 1050}, device_scale_factor=2)
        pg.on("console", lambda m: m.type == "error"
              and "404" not in m.text and errs.append(m.text))
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE, wait_until="networkidle")
        pg.wait_for_timeout(700)
        # Both halves in frame: the panel has to have somewhere to fall from.
        pg.evaluate("() => scrollTo(0, document.querySelector('.mq-sec')"
                    ".getBoundingClientRect().top + scrollY - 60)")
        pg.wait_for_timeout(500)

        print("\nThe floor")
        s = pg.evaluate(STATE)
        check([(c["name"], c["mode"]) for c in s["cards"]] == WANT,
              "the four families, with the mode each is evaluated under",
              str([(c["name"], c["mode"]) for c in s["cards"]]))
        # A product may be offered as an example. It may not be the title, and it may not be
        # painted onto the diagram, or the floor reads as a list of four agents.
        named = [c["name"] for c in s["cards"] if any(p in c["name"] for p in PRODUCTS)]
        check(not named, "none of them is named after a particular agent", str(named))
        check(not [x for x in s["nodes"] if any(p in x for p in PRODUCTS)],
              "and no diagram is either", str(s["nodes"]))
        check(all(c["eg"].startswith("e.g.") for c in s["cards"]),
              "the paper's own runs are offered as examples",
              str([c["eg"] for c in s["cards"]]))
        # A family name is longer than a product name, and a header that wraps takes the
        # height back out of the diagram under it and reads as a different card.
        heads = [c["head"] for c in s["cards"]]
        check(len(set(heads)) == 1 and not any(c["clip"] for c in s["cards"]),
              "and every header still holds on one line, whole",
              f"{heads}, clipped {[c['clip'] for c in s['cards']]}")
        # A rect stroked on the edge of the viewport is cut in half by it, and a box with no
        # bottom edge, a few pixels above the tray's own dashed line, reads as a diagram
        # overlapping the row beneath it. Measured at three widths, because the markup looks
        # the same either way and only the rendered geometry gives it away.
        EDGE = """() => [...document.querySelectorAll('.sim-card')].map((c) => {
          const f = c.querySelector('.sim-fig').getBoundingClientRect();
          const t = c.querySelector('.sim-tray').getBoundingClientRect();
          const low = Math.max(...[...c.querySelectorAll('.sn rect')]
            .map((r) => r.getBoundingClientRect().bottom));
          return {cut: +(low - f.bottom).toFixed(1), gap: +(t.top - low).toFixed(1)};
        })"""
        for w in (1280, 1024, 430):
            pg.set_viewport_size({"width": w, "height": 1000})
            pg.wait_for_timeout(200)
            edge = pg.evaluate(EDGE)
            check(all(e["cut"] <= -0.5 for e in edge),
                  f"at {w}px nothing is cut off by the edge of its own figure", str(edge))
            check(all(e["gap"] >= 2 for e in edge),
                  "and the drawing clears the tray under it", str(edge))
        pg.set_viewport_size({"width": 1280, "height": 1000})
        pg.wait_for_timeout(200)
        check(s["axes"] == AXES and len(s["lives"]) == 1,
              "all three axes are named, and exactly one of them is being evaluated",
              f"{s['axes']}, live {s['lives']}")
        # One harness, four systems: they differ in what they do with a capability, never in
        # which ones they were handed, so a card holding its own set would be a lie. The
        # boxes are not all the same width, so a long name is cut differently from card to
        # card and only the stems can be compared.
        rows = [[(x["ax"], x["n"]) for x in c["caps"] if x["n"]] for c in s["cards"]]
        wide = max(rows, key=lambda r: sum(len(x[1]) for x in r))
        same = all(len(r) <= len(wide)
                   and all(a[0] == b[0] and b[1].startswith(a[1].rstrip("\u2026"))
                           for a, b in zip(r, wide))
                   for r in rows)
        check(same, "every card is holding the same harness", str(wide))
        check(all(rows), "no card is holding an empty box", str([len(r) for r in rows]))
        check({x[0] for r in rows for x in r} == set(s["lives"]),
              "all of it on the one axis that stream evolves",
              str(sorted({x[0] for r in rows for x in r})))
        # A tool is an endpoint: the members of a multi-agent system are generic, because the
        # axis is not growing them, and the traffic goes out to the capability and back.
        check(s["lives"] == ["tools"] and s["nodes"].count("specialist") == 3
              and s["nodes"].count("worker") == 3,
              "on a tools stream the members of a system are its own, drawn generically",
              str(s["nodes"]))
        check(s["look"]["out"] > 0 and s["look"]["dash"] == "none"
              and s["look"]["rx"] < 8,
              "and a capability is an endpoint it calls out to", str(s["look"]))
        # Names are the corpus's own. Long ones are cut on screen, so compare on the stem.
        shown = {x[1].rstrip("\u2026") for r in rows for x in r}
        stray = [x for x in shown if not any(n.startswith(x) for n in names)]
        check(not stray, "and every name on it comes from the corpus", str(stray))

        print("\nA stage turning over")
        run = watch(pg, "run")
        drop = watch(pg, "drop")
        # Something has to leave the band. A panel too close to the edge of the window is not
        # flown -- half a panel in mid-air reads as a fault -- and the release goes instead.
        pg.wait_for_timeout(320)
        a = pg.evaluate("() => { const f = document.querySelector('.sim-fly'); if (!f) return null;"
                        " const r = f.getBoundingClientRect(), d = document.querySelector"
                        "('[data-dock]').getBoundingClientRect();"
                        " return {pkt: f.classList.contains('is-pkt'), op: +getComputedStyle(f).opacity,"
                        " gap: Math.hypot(r.left - d.left, r.top - d.top)}; }")
        pg.wait_for_timeout(360)
        c2 = pg.evaluate("() => { const f = document.querySelector('.sim-fly'); if (!f) return null;"
                         " const r = f.getBoundingClientRect(), d = document.querySelector"
                         "('[data-dock]').getBoundingClientRect();"
                         " return Math.hypot(r.left - d.left, r.top - d.top); }")
        check(bool(a), "something drops out of the band", str(a))
        check(bool(a) and a["op"] > 0.5, "and is still solid on the way down",
              str(a and a["op"]))
        check(bool(a) and c2 is not None and c2 < a["gap"] - 20,
              "falling towards the harness it lands on",
              f"{a and round(a['gap'])}px to {c2 and round(c2)}px")
        pg.screenshot(path=str(OUT / "sim-drop.png"),
                      clip={"x": 0, "y": 0, "width": 1280, "height": 1000})

        adapt = watch(pg, "adapt")
        check([run["phase"], drop["phase"], adapt["phase"]] == ["run", "drop", "adapt"],
              "the stage runs, takes a release, then answers for it",
              str([run["phase"], drop["phase"], adapt["phase"]]))
        def read(s: dict) -> tuple[int, str, int]:
            """The stage on the badge, the axis being evaluated, and the pool it claims."""
            ax = s["lives"][0] if len(s["lives"]) == 1 else ""
            n = s["mets"].get(ax, "").split()[0] if ax else ""
            return int(s["st"].replace("H", "")), ax, int(n) if n.isdigit() else -1

        st, ax, pool = read(adapt)
        check((ax, st, pool) in rungs,
              "the stage and the pool are a rung of that axis's own stream",
              f"H{st}, {pool} {ax}")
        # The axes are three separate evaluations -- the pipeline runs independently per axis
        # and a system is measured on one stream at a time. So the two the floor is not
        # running may be named, but they may not carry a pool: nothing arrives on all three
        # at once, because no run ever holds all three.
        idle = {a: m for a, m in adapt["mets"].items()
                if a != ax and any(c.isdigit() for c in m)}
        check(not idle, "and the axes it is not running carry no pool of their own",
              str(idle) or str(adapt["mets"]))
        check("+" in adapt["say"] and ax in adapt["say"]
              and not [a for a in AXES if a != ax and a in adapt["say"]],
              "the release is named on that one axis, and no other", adapt["say"])
        watch(pg, "run")
        nxt = watch(pg, "adapt", limit=25)
        st2, ax2, pool2 = read(nxt)
        check(ax2 == ax and st2 == st + 1 and pool2 > pool,
              "and the next boundary climbs the same stream",
              f"H{st} {pool} {ax} -> H{st2} {pool2} {ax2}")
        check((ax2, st2, pool2) in rungs, "on a real rung again", f"H{st2}, {pool2} {ax2}")
        adapt = nxt
        # The release is marked on every card, not only counted in the header, and what is
        # marked on an axis is what that axis released at this stage.
        fresh = [c["fresh"] for c in adapt["cards"]]
        check(all(fresh), "and every system is holding what arrived",
              str([len(f) for f in fresh]))
        wrong = [x for f in fresh for x in f
                 if not any(n.startswith(x["n"].rstrip("\u2026"))
                            for n in bank.get((x["ax"], st2), []))]
        check(not wrong, "and it is what that axis released at this stage, all of it",
              str(wrong) or str([x["n"] for x in fresh[0]]))

        print("\nWhat a boundary costs each mode")
        dep = [c for c in adapt["cards"] if c["mode"] == "deployment"]
        sev = [c for c in adapt["cards"] if c["mode"] == "self-evolving"]
        check(len(dep) == 3 and len(sev) == 1, "three deployment systems and one that carries",
              f"{len(dep)}/{len(sev)}")
        check(all(c["on"] == 0 for c in dep), "deployment keeps nothing across the boundary",
              str([c["on"] for c in dep]))
        check(all(c["note"] == "fresh instance" for c in dep), "and says so",
              str([c["note"] for c in dep]))
        check(sev[0]["on"] > 0, "z_t is still there on the other side", str(sev[0]["on"]))
        check(sev[0]["stale"] > 0, "and part of it now describes a harness that moved",
              f"{sev[0]['stale']} of {sev[0]['on']} stale")
        pg.screenshot(path=str(OUT / "sim-adapt.png"),
                      clip={"x": 0, "y": 0, "width": 1280, "height": 1000})

        # A different axis is not the next stage of anything -- it is another evaluation, on
        # a stream built by the same pipeline run independently. So the floor may not slide
        # from one axis into another as though the harness had grown: it has to stop, hand
        # over, and start the new stream with nothing carried into it.
        print("\nAnother axis, another evaluation")
        sw = watch(pg, "swap", limit=30)
        check(sw["phase"] == "swap", "the floor hands over to another axis", sw["phase"])
        check("different axis" in sw["say"] and "separately" in sw["say"],
              "and says that axis is evaluated separately", sw["say"])
        check(not [c for c in sw["cards"] if c["fresh"]],
              "nothing is marked as having arrived, because nothing did",
              str([len(c["fresh"]) for c in sw["cards"]]))
        pg.screenshot(path=str(OUT / "sim-swap.png"),
                      clip={"x": 0, "y": 0, "width": 1280, "height": 1000})
        aft = watch(pg, "run", limit=20)
        st3, ax3, pool3 = read(aft)
        check(ax3 and ax3 != ax2, "the axis being evaluated changes", f"{ax2} -> {ax3}")
        check((ax3, st3, pool3) in rungs, "onto a rung of that axis's own stream",
              f"H{st3}, {pool3} {ax3}")
        check({x["ax"] for c in aft["cards"] for x in c["caps"]} == {ax3},
              "and the floor is holding that axis's capabilities, not the last one's",
              str(sorted({x["ax"] for c in aft["cards"] for x in c["caps"]})))
        check(max(c["on"] for c in aft["cards"]) <= 1,
              "with nothing carried into it, z_t included",
              str([c["on"] for c in aft["cards"]]))
        # And the picture is redrawn for what that axis releases. A skill is a procedure: it
        # is read and complied with, so nothing is called and the traffic runs inward.
        if ax3 == "skills":
            check(aft["look"]["out"] == 0 and aft["look"]["back"] > 0,
                  "a skill is complied with, not called: the traffic runs inward",
                  str(aft["look"]))
            check(aft["look"]["dash"] != "none", "and it is drawn as a procedure, not an edge",
                  str(aft["look"]))

        # Three axes means three separate evaluations, and the reader who came for one of
        # them should not have to wait for it to come round. The chips are the way in.
        print("\nThe reader can pick the axis")
        kind = pg.evaluate("() => [...document.querySelectorAll('[data-met]')]"
                           ".map((m) => m.tagName + ':' + m.getAttribute('aria-pressed'))")
        check(all(k.startswith("BUTTON") for k in kind), "every axis is a button", str(kind))
        check(kind.count("BUTTON:true") == 1,
              "and the pressed one is the axis being evaluated", str(kind))
        pg.click('[data-met="agents"]')
        pg.wait_for_timeout(700)
        axis = pg.evaluate(STATE)
        st4, ax4, pool4 = read(axis)
        check(ax4 == "agents", "clicking one hands the floor to that axis", ax4)
        check((ax4, st4, pool4) in rungs, "at a rung of its own stream",
              f"H{st4}, {pool4} {ax4}")
        check(max(c["on"] for c in axis["cards"]) <= 1,
              "with nothing carried over from the axis it left",
              str([c["on"] for c in axis["cards"]]))
        pg.click('[data-met="agents"]')
        pg.wait_for_timeout(300)
        check(read(pg.evaluate(STATE))[:2] == (st4, ax4),
              "and clicking the one already running changes nothing", f"H{st4} {ax4}")

        # The arrivals on the agents axis are members of the system, not things it calls, so
        # the generic workers give way to them and the floor draws as many as the pool holds.
        print("\nWhen the axis changes, so does the picture")
        check(not [x for x in axis["nodes"] if x in ("worker", "specialist")],
              "and the generic members are gone, because the arrivals are the members",
              str(axis["nodes"]))
        check({x["ax"] for c in axis["cards"] for x in c["caps"]} == {"agents"}
              and axis["look"]["rx"] >= 8,
              "each drawn as a member of the system", str(axis["look"]))
        check(all(len(c["caps"]) == min(pool4, 3) for c in axis["cards"]),
              "as many of them as that stage's pool holds",
              f"{pool4} in the pool, {[len(c['caps']) for c in axis['cards']]} drawn")
        pg.screenshot(path=str(OUT / "sim-agents.png"),
                      clip={"x": 0, "y": 0, "width": 1280, "height": 1000})

        print("\nMotion nobody asked for")
        pg.click("[data-btn]")
        pg.wait_for_timeout(250)
        held = pg.evaluate(STATE)
        # Every animation that would otherwise run forever, whichever beat the button was
        # pressed on: each phase drives its own set, and a pause that only reaches the one
        # the reader happened to interrupt is not a pause. One-shots -- a count flashing as
        # it lands, a transition -- are already on their way out and are not the complaint.
        LOOPING = ("() => document.querySelector('[data-sim]').getAnimations({subtree: true})"
                   ".filter((a) => a.constructor.name === 'CSSAnimation'"
                   " && a.effect.getTiming().iterations === Infinity)")
        play = pg.evaluate(LOOPING + ".map((a) => a.playState)")
        check(held["held"] and bool(play) and set(play) == {"paused"},
              "the button stops the motion, not only the clock",
              f"{len(play)} animations, {sorted(set(play))}")
        # A full cycle is run + drop + adapt; sit through one and nothing may move on.
        pg.wait_for_timeout(13000)
        after = pg.evaluate(STATE)
        check(after["phase"] == held["phase"] and after["st"] == held["st"],
              "and it stays where it was stopped",
              f"{held['phase']} {held['st']} -> {after['phase']} {after['st']}")
        pg.click("[data-btn]")
        pg.wait_for_timeout(400)
        check(pg.evaluate(LOOPING + ".every((a) => a.playState === 'running')"),
              "and gives it back")

        # A clock running behind a tab nobody is looking at is heat, not information.
        pg.click('.pv-tab[data-pv="results"]')
        pg.wait_for_timeout(900)
        away = pg.evaluate(STATE)
        pg.wait_for_timeout(13000)
        check(pg.evaluate(STATE)["phase"] == away["phase"],
              "the floor idles while another view is open", away["phase"])
        pg.click('.pv-tab[data-pv="overview"]')
        pg.wait_for_timeout(1200)
        check(pg.evaluate(STATE)["phase"] in ("run", "drop", "adapt"),
              "and picks up again when it is back on screen")
        pg.evaluate("() => scrollTo(0, document.querySelector('.mq-sec')"
                    ".getBoundingClientRect().top + scrollY - 60)")
        pg.wait_for_timeout(400)
        pg.locator("[data-sim]").screenshot(path=str(OUT / "sim-run.png"))
        b.close()

        print("\nAsked for no motion")
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 1050}, reduced_motion="reduce",
                        device_scale_factor=2)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE, wait_until="networkidle")
        pg.wait_for_timeout(900)
        s = pg.evaluate(STATE)
        check(len(s["cards"]) == 4 and all(c["caps"] for c in s["cards"]),
              "the floor still says who runs and what they hold")
        check(pg.evaluate("() => document.querySelector('[data-sim]')"
                          ".getAnimations({subtree: true}).length") == 0, "with nothing moving")
        check(pg.evaluate("() => document.querySelector('[data-btn]').hidden"),
              "and no button to stop motion that is not there")
        pg.wait_for_timeout(13000)
        check(pg.evaluate(STATE)["phase"] == s["phase"], "no clock either", s["phase"])
        check(not pg.query_selector(".sim-fly"), "and nothing falls out of the band")
        # Picking an axis is not motion, so it still works: the floor redraws for the axis
        # asked for and stays there.
        pg.click('[data-met="agents"]')
        pg.wait_for_timeout(400)
        pick = pg.evaluate(STATE)
        check(pick["lives"] == ["agents"] and pick["look"]["rx"] >= 8,
              "the reader can still pick an axis, and it is drawn for that axis",
              f"{pick['lives']}, {pick['look']}")
        check(pg.evaluate("() => document.querySelector('[data-sim]')"
                          ".getAnimations({subtree: true}).length") == 0,
              "and nothing starts moving because they did")
        pg.locator("[data-sim]").screenshot(path=str(OUT / "sim-still.png"))
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
