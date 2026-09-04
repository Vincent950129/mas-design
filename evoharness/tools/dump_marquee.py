#!/usr/bin/env python3
"""Pick the panels for the drifting band on the overview tab.

The band is the first thing on the page that shows what a task actually is, so
every panel is a real figure from the corpus rather than an illustration: for an
ALE task the artifact it hands the agent, for an EOG task the sandbox it starts
in. Both already ship thumbnails for the gallery, which is what the band uses --
26 panels come to a few hundred KB, and the manifest itself to a couple of KB,
so the overview tab does not have to touch the 4.3MB gallery payload to draw it.

Selection spreads the band across disciplines and gyms rather than taking the
first N: a band that reads as five Blender scenes in a row says the corpus is
narrower than it is.

    python tools/dump_marquee.py
"""
from __future__ import annotations

import collections
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "static" / "tasks.json"
OUT = ROOT / "static" / "marquee.json"
ALE_DIR = "static/images/ale/"
ENV_DIR = "static/images/env/"

# Columns of a task row, mirroring T in app.js. An index of -1 means the row has
# no such value, which Python would otherwise read as the last of the pool.
COL = dict(track=0, env=1, dom=2, cat=3, sub=4, stage=6, tid=7, title=8, prompt=11,
           oracle=12, cum=13)

# The paper reads tools, skills, agents; ties between axes break that way.
AXES = ["tools", "skills", "agents"]

PER_SUBDOMAIN = 2   # a discipline may show twice, no more
PER_GYM = 2
# Three or so per stage: a band this length keeps a stage boundary on screen at
# most scroll positions, which is what makes the ordering legible at a glance
# rather than something you have to watch for half a minute to notice.
TARGET = 18

# Prefer what the task starts from over what it should end at: the input is the
# thing a reader can look at and understand the job from.
ROLE_RANK = {"input": 0, "starter": 1, "reference": 2}


def pretty(s: str) -> str:
    return s.replace("_", " ").replace("-", " ").title()


def load() -> dict:
    with SRC.open() as fh:
        return json.load(fh)


def by_task(d: dict) -> dict[str, list]:
    out: dict[str, list] = collections.defaultdict(list)
    for r in d["tasks"]:
        out[r[COL["tid"]]].append(r)
    return out


def heading(d: dict, row: list) -> str:
    """The name the gallery would show. No EOG task carries a title and a third of
    the ALE ones do not either, so both fall back to the opening line of the
    prompt, clipped the same way the gallery clips it."""
    i = row[COL["title"]]
    if i >= 0:
        return d["titles"][i]
    lines = d["prompts"][row[COL["prompt"]]].split("\n")
    one = " ".join(next((l for l in lines if l.strip()), "").split())
    if len(one) <= 96:
        return one
    return re.sub(r"[\s,;.]+\S*$", "", one[:95]) + "\u2026"


def names(d: dict, i: int) -> list[str]:
    """A row's interned name list, the way app.js reads one."""
    return [d["names"][j] for j in d["lists"][i]] if i >= 0 else []


def stream(d: dict, row: list) -> tuple[str, str, str]:
    """Which of the 17 streams a row belongs to.

    Environment, domain and axis together come to exactly the 17 the paper counts,
    and the pools they offer nest: at every one of the 52 stage steps, the pool a
    stage offers contains the whole of the stage before it. That is what lets a
    panel say what the harness gained by the time its task arrived.
    """
    return (d["envs"][row[COL["env"]]], d["domains"][row[COL["dom"]]],
            d["tracks"][row[COL["track"]]])


def pools(d: dict) -> dict[tuple, dict[int, set[str]]]:
    out: dict[tuple, dict[int, set[str]]] = collections.defaultdict(
        lambda: collections.defaultdict(set))
    for r in d["tasks"]:
        out[stream(d, r)][r[COL["stage"]]] |= set(names(d, r[COL["cum"]]))
    return out


def gain(d: dict, pool: dict, row: list) -> dict:
    """What the harness holds for one task, and what of it had just arrived."""
    st, key = row[COL["stage"]], stream(d, row)
    stages = pool[key]
    before: set[str] = set().union(*(v for s, v in stages.items() if s < st)) \
        if any(s < st for s in stages) else set()
    fresh = stages[st] - before
    need = set(names(d, row[COL["oracle"]]))
    # Name what the task needs out of what just arrived, since a new capability the
    # task leans on is the whole point; anything new, failing that. Shortest first:
    # a panel is only as wide as its picture, and two names that fit say more than
    # one that fills the strip on its own.
    show = sorted(need & fresh or fresh or need, key=lambda s: (len(s), s))
    return {"ax": d["tracks"][row[COL["track"]]], "pool": len(stages[st]),
            "new": len(fresh), "need": len(need), "first": not before,
            "items": show[:2]}


def facts(d: dict, pool: dict, rows: list) -> dict:
    """What the band can say about a task: where it sits, and which harness it is
    handed there. A task is graded on an axis at a time, so the panel speaks for
    the axis with the most to show at the stage the task enters -- the one whose
    pool had just grown the most.
    """
    subs = [d["subdomains"][r[COL["sub"]]] for r in rows if r[COL["sub"]] >= 0]
    cats = [d["categories"][r[COL["cat"]]] for r in rows if r[COL["cat"]] >= 0]
    st = min(r[COL["stage"]] for r in rows)
    hx = sorted((gain(d, pool, r) for r in rows if r[COL["stage"]] == st),
                key=lambda g: (-g["new"], -len(g["items"]), AXES.index(g["ax"])))
    return {
        "title": heading(d, rows[0]),
        "sub": collections.Counter(subs).most_common(1)[0][0] if subs else "",
        "cat": collections.Counter(cats).most_common(1)[0][0] if cats else "",
        # The stage a task first appears at: what a panel's badge counts from.
        "st": st,
        "ax": sorted({d["tracks"][r[COL["track"]]] for r in rows}),
        "hx": hx[0],
    }


def dims(rel: str, w: int, h: int) -> tuple[int, int]:
    """Thumbnail size, so a panel reserves its aspect before the file lands."""
    try:
        from PIL import Image
        with Image.open(ROOT / rel) as im:
            return im.size
    except Exception:
        return w, h


def ale_panels(d: dict, byid: dict, pool: dict) -> list[dict]:
    out: list[dict] = []
    for tid, figs in d["aleFigures"].items():
        rows = byid.get(tid)
        if not rows:
            continue
        pick = min(figs, key=lambda f: (ROLE_RANK.get(f.get("role"), 3),
                                        f["kind"] != "image"))
        thumb = pick.get("thumb") or pick["file"]
        f = facts(d, pool, rows)
        w, h = dims(ALE_DIR + thumb, pick["w"], pick["h"])
        out.append({
            "src": ALE_DIR + thumb, "w": w, "h": h,
            "lab": f["sub"] or pretty(f["cat"]),
            "tid": tid, "title": f["title"], "st": f["st"], "env": "ale",
            "ax": f["ax"], "hx": f["hx"], "cap": pick["caption"],
            "clip": pick["kind"] == "video",
        })
    return out


def eog_panels(d: dict, byid: dict, pool: dict) -> list[dict]:
    """One panel per gym snapshot, carrying a task that actually starts there."""
    starts: dict[str, list[str]] = collections.defaultdict(list)
    for tid, envs in d["taskEnvs"].items():
        for e in envs:
            starts[e].append(tid)

    out: list[dict] = []
    for eid, e in d["envFigures"].items():
        tids = [t for t in starts.get(eid, []) if t in byid]
        if not tids:
            continue
        # The task with the most rows is graded on the most axes, so its panel
        # is the one whose click lands on the fullest detail view.
        tid = max(tids, key=lambda t: (len(byid[t]), t))
        thumb = e.get("thumb") or e["file"]
        f = facts(d, pool, byid[tid])
        w, h = dims(ENV_DIR + thumb, e["w"], e["h"])
        out.append({
            "src": ENV_DIR + thumb, "w": w, "h": h,
            "lab": e["label"], "gym": e["gym"],
            "tid": tid, "title": f["title"], "st": f["st"], "env": "eog",
            "ax": f["ax"], "hx": f["hx"], "cap": e["caption"],
            "rows": e.get("rows", 0), "n": len(tids),
        })
    return out


def allocate(ale: list[dict], eog: list[dict]) -> list[dict]:
    """Fill the band evenly across stages, then order it by stage.

    Left to right by the stage a task enters at is what makes the band mean
    something: the drift carries panels leftwards, so what arrives from the right
    is what the harness releases later. That only reads if the stages are spread
    rather than sampled in corpus proportion -- 61 of the 88 available figures
    belong to stage 1, which would be one long stage-1 run and a short tail.

    The repetition caps are enforced here rather than before the fill: applied to
    the candidates first they would spend a discipline's two slots on whichever
    stage it happens to appear in, and stages left holding one environment only
    read as a run of near-identical panels.
    """
    queues: dict[int, dict[str, list[dict]]] = collections.defaultdict(
        lambda: {"ale": [], "eog": []})
    for p in ale + eog:
        queues[p["st"]][p["env"]].append(p)
    caps = {"ale": (PER_SUBDOMAIN, "lab"), "eog": (PER_GYM, "gym")}
    used: collections.Counter = collections.Counter()
    titles: set[str] = set()

    def take(st: int, env: str) -> dict | None:
        cap, key = caps[env]
        q = queues[st][env]
        while q:
            p = q.pop(0)
            # Distinct titles only: task families share names, and two panels
            # reading the same words look like a bug.
            if used[env, p[key]] < cap and p["title"] not in titles:
                used[env, p[key]] += 1
                titles.add(p["title"])
                return p
        return None

    # One at a time from each stage, so the scarce late stages fill first and
    # stage 1, which has figures to spare, takes whatever is left over. The turn
    # is counted per stage: counted globally it would come back to each stage an
    # even number of turns later and hand every one of them the same environment
    # every time.
    picked: list[dict] = []
    turn: collections.Counter = collections.Counter()
    while len(picked) < TARGET:
        took = False
        for st in sorted(queues):
            for env in (("eog", "ale") if turn[st] % 2 else ("ale", "eog")):
                p = take(st, env)
                if p:
                    picked.append(p)
                    turn[st] += 1
                    took = True
                    break
            if len(picked) >= TARGET:
                break
        if not took:
            break

    out: list[dict] = []
    for st in sorted({p["st"] for p in picked}):
        a = [p for p in picked if p["st"] == st and p["env"] == "ale"]
        e = [p for p in picked if p["st"] == st and p["env"] == "eog"]
        # Alternate the two within a stage, so the band keeps changing texture
        # without ever going backwards through the stages.
        for i in range(max(len(a), len(e))):
            out += a[i:i + 1] + e[i:i + 1]
    return out


def main() -> None:
    d = load()
    byid = by_task(d)

    pool = pools(d)
    ale = ale_panels(d, byid, pool)
    # Richest snapshot first: a sandbox with more rows in it reads as a real one.
    eog = sorted(eog_panels(d, byid, pool), key=lambda p: (-p["rows"], p["tid"]))

    panels = allocate(ale, eog)

    OUT.write_text(json.dumps(panels, separators=(",", ":")) + "\n")
    kb = OUT.stat().st_size / 1024
    imgs = sum((ROOT / p["src"]).stat().st_size for p in panels) / 1024
    print(f"{len(panels)} panels -> {OUT.relative_to(ROOT)}  ({kb:.1f} KB manifest, "
          f"{imgs:.0f} KB of thumbnails)")
    print(f"  {sum(p['env'] == 'ale' for p in panels)} ALE artifacts, "
          f"{sum(p['env'] == 'eog' for p in panels)} EOG sandboxes")
    print(f"  stages: {dict(sorted(collections.Counter(p['st'] for p in panels).items()))}")
    print(f"  {len({p['lab'] for p in panels})} distinct labels, "
          f"{sum(p.get('clip', False) for p in panels)} from clips")
    unit = lambda n, ax: ax[:-1] if n == 1 else ax    # the pill app.js will draw
    for p in panels:
        h = p["hx"]
        got = (f"{h['pool']} {unit(h['pool'], h['ax'])} to start" if h["first"]
               else f"+{h['new']} {unit(h['new'], h['ax'])}" if h["new"]
               else f"{h['pool']} {unit(h['pool'], h['ax'])} in the pool")
        print(f"    stage {p['st']} {p['env']:>3}  {got:18.18} {', '.join(h['items'])[:40]:40.40}"
              f"  {p['lab'][:26]:26.26}  {p['title'][:34]}")


if __name__ == "__main__":
    main()
