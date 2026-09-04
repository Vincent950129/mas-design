#!/usr/bin/env python3
"""Checks for the tool descriptions behind the Task Gallery's chips.

    python tools/verify_tool_docs.py

A task lists the tools it was handed by name, and the names alone do not say
what any of them does. Each one now opens its description, which introduces two
things that can go quietly wrong.

The first is provenance. 29 tool names are served by more than one gym and every
one of them means something different in each -- `list_users` filters employees
on HR and returns Microsoft Graph objects on Teams. A lookup by name alone would
be right most of the time and silently wrong the rest, so these checks open the
same name on tasks from different gyms and insist the answers differ.

The second is cost. The docs are 424 KB on a tab that already fetches four
megabytes, and they exist for a reader who opens a chip, so they must not be
fetched until one is opened.
"""
from __future__ import annotations

import functools
import http.server
import json
import pathlib
import socketserver
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT.parent
DOCS = ROOT / "static/tool_docs.json"
TASKS = ROOT / "static/tasks.json"
PAGE = "/evoharness/index.html"

# Field offsets into the interned task tuples, mirroring app.js.
T_TRACK, T_ENV, T_ORACLE, T_CUM, T_SEL, T_GYM = 0, 1, 12, 13, 14, 19

fails: list[str] = []
checks = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global checks
    checks += 1
    print(f"  {'ok  ' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        fails.append(label)


def serve() -> tuple[socketserver.TCPServer, str]:
    """Serve the site on whatever port is free, so a stray server cannot block a run."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
    srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}{PAGE}"


def main() -> int:
    d = json.loads(TASKS.read_text())
    docs = json.loads(DOCS.read_text())
    lists = d["lists"]
    pool = d["names"]

    def names(i: int) -> list[str]:
        return [pool[j] for j in lists[i]] if i >= 0 else []

    print("Payload")
    check(bool(docs.get("servers")) and bool(docs.get("gyms")),
          "tool_docs.json carries both the server map and the gyms")
    missing_gym = [s for s, g in docs["servers"].items() if g not in docs["gyms"]]
    check(not missing_gym, "every server maps to a gym that is present", str(missing_gym))
    # The page resolves a chip through this map, so a corpus server missing from it means
    # a whole domain's tools quietly stop being inspectable.
    corpus_servers = {s for t in d["tasks"] for s in names(t[T_GYM])}
    unmapped = sorted(corpus_servers - set(docs["servers"]))
    check(not unmapped, "every server the corpus names is mapped", str(unmapped))

    shared = {}
    for gym, entries in docs["gyms"].items():
        for name in entries:
            shared.setdefault(name, []).append(gym)
    multi = {n: gs for n, gs in shared.items() if len(gs) > 1}
    collapsed = [n for n, gs in multi.items()
                 if len({docs["gyms"][g][n]["d"] for g in gs}) == 1]
    check(len(multi) >= 20, f"{len(multi)} names are kept per gym rather than by name alone")
    # If these ever agree, one gym's text is standing in for another's.
    check(not collapsed, "no shared name was collapsed onto one description",
          str(collapsed[:5]))

    # Resolution the way the page does it: the task's own gyms answer first, then any gym
    # that serves the name. The fallback is not a nicety -- a fifth of what a task is
    # offered comes from another domain's gym, because the cumulative harness keeps adding
    # to the pool, so scoping this to the task's own servers would leave one chip in five
    # claiming its tool has no description.
    everywhere = {n for g in docs["gyms"].values() for n in g}
    total = own = cross = unknown = 0
    for t in d["tasks"]:
        if d["tracks"][t[T_TRACK]] != "tools" or d["envs"][t[T_ENV]] != "eog":
            continue
        gyms = [docs["servers"].get(s) for s in names(t[T_GYM])]
        for n in set(names(t[T_ORACLE])) | set(names(t[T_CUM])):
            total += 1
            if any(g and n in docs["gyms"][g] for g in gyms):
                own += 1
            elif n in everywhere:
                cross += 1
            else:
                unknown += 1
    rate = (own + cross) / total if total else 0
    check(rate > 0.99, "nearly every tool a task names resolves to a description",
          f"{own + cross}/{total} = {rate:.1%}")
    check(cross / total > 0.1, "the cross-gym fallback carries a real share of the pool",
          f"{cross} mentions ({cross / total:.1%}) come from another domain's gym")
    check(unknown < total * 0.01, "only a handful resolve nowhere", f"{unknown} mentions")

    srv, base = serve()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            pg = browser.new_page(viewport={"width": 1100, "height": 1000})
            errs: list[str] = []
            fetched: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("request", lambda r: "tool_docs.json" in r.url and fetched.append(r.url))
            pg.goto(base, wait_until="load")
            pg.evaluate("PV.open('tasks')")
            pg.wait_for_timeout(800)

            print("\nCost")
            pg.select_option("#tg-env", "eog")
            pg.select_option("#tg-track", "tools")
            pg.wait_for_timeout(400)
            pg.eval_on_selector_all(".tg-card", "ns => ns[0].click()")
            pg.wait_for_timeout(400)
            check(not fetched, "the descriptions are not fetched until one is opened")
            n_chips = pg.eval_on_selector_all("[data-tg-detail] .tg-chip.is-doc", "ns => ns.length")
            check(n_chips > 0, "tool chips offer themselves as openable", f"{n_chips} chips")

            print("\nOpening one")
            pg.eval_on_selector_all("[data-tg-detail] .tg-chip.is-doc", "ns => ns[0].click()")
            pg.wait_for_timeout(1200)
            check(len(fetched) == 1, "opening one fetches them exactly once", str(len(fetched)))
            panel = pg.evaluate("""() => {
                const d = document.querySelector('[data-tg-detail] .tg-doc:not([hidden])');
                if (!d) return null;
                return { name: d.querySelector('.tg-doc-name')?.textContent || '',
                         gym: d.querySelector('.tg-doc-gym')?.textContent || '',
                         desc: d.querySelector('.tg-doc-d')?.textContent || '',
                         args: d.querySelectorAll('.tg-doc-args tbody tr').length,
                         req: d.querySelectorAll('.tg-doc-req').length }; }""")
            check(panel is not None, "a panel opens with the answer")
            if panel:
                chip = pg.eval_on_selector("[data-tg-detail] .tg-chip.is-doc", "n => n.dataset.tool")
                check(panel["name"] == chip, "the panel answers about the chip that was clicked",
                      f"{panel['name']} vs {chip}")
                check(len(panel["desc"]) > 20, "it reads as a description, not a name echoed back",
                      panel["desc"][:60])
                check("gym describes it" in panel["gym"],
                      "it says which gym answered", panel["gym"])
                check(panel["args"] > 0 and panel["req"] > 0,
                      "arguments are listed and the required ones marked",
                      f"{panel['args']} args, {panel['req']} required")
            # A second click on the same chip is how a reader closes it again.
            pg.eval_on_selector_all("[data-tg-detail] .tg-chip.is-doc.is-open", "ns => ns[0].click()")
            pg.wait_for_timeout(300)
            check(pg.eval_on_selector_all("[data-tg-detail] .tg-doc:not([hidden])", "ns => ns.length") == 0,
                  "clicking the open chip again closes it")

            print("\nProvenance")
            seen = {}
            for domain in ("teams", "itsm", "csm", "hr"):
                pg.evaluate("() => document.querySelector('[data-tg-close]')?.click()")
                pg.select_option("#tg-domain", domain)
                pg.wait_for_timeout(350)
                for i in range(6):
                    pg.eval_on_selector_all(".tg-card", f"ns => ns[{i}] && ns[{i}].click()")
                    pg.wait_for_timeout(250)
                    hit = pg.evaluate("""(n) => { const c = [...document.querySelectorAll(
                        '[data-tg-detail] .tg-chip.is-doc')].find(x => x.dataset.tool === n);
                        if (!c) return false; c.click(); return true; }""", "list_users")
                    if hit:
                        pg.wait_for_timeout(500)
                        seen[domain] = pg.evaluate("""() => {
                            const d = document.querySelector('[data-tg-detail] .tg-doc:not([hidden])');
                            return { gym: d.querySelector('.tg-doc-gym')?.textContent || '',
                                     desc: d.querySelector('.tg-doc-d')?.textContent || '' }; }""")
                        break
                    pg.evaluate("() => document.querySelector('[data-tg-close]')?.click()")
                    pg.wait_for_timeout(120)
            check(len(seen) >= 2, "found `list_users` under more than one gym", str(list(seen)))
            for domain, got in seen.items():
                check(domain.lower() in got["gym"].lower(),
                      f"a {domain} task credits the {domain} gym", got["gym"])
            texts = {d_: g["desc"] for d_, g in seen.items()}
            check(len(set(texts.values())) == len(texts),
                  "the same name reads differently on each gym, as the gyms define it",
                  " | ".join(f"{k}: {v[:34]}" for k, v in texts.items()))

            print("\nTools the cumulative pool brought in from elsewhere")
            # Pick the case from the data rather than guessing at names: a task whose pool
            # holds a tool its own gyms do not serve, which some other gym does.
            target = None
            for t in d["tasks"]:
                if d["tracks"][t[T_TRACK]] != "tools" or d["envs"][t[T_ENV]] != "eog":
                    continue
                mine = {g for g in (docs["servers"].get(s) for s in names(t[T_GYM])) if g}
                if not mine:
                    continue
                served = {n for g in mine for n in docs["gyms"][g]}
                odd = sorted((set(names(t[T_ORACLE])) | set(names(t[T_CUM])))
                             & everywhere - served)
                if odd:
                    target = (t[7], odd[0], sorted(mine))
                    break
            check(target is not None, "the corpus has a task offered another gym's tool")
            pg.evaluate("() => document.querySelector('[data-tg-close]')?.click()")
            pg.select_option("#tg-domain", "")
            pg.fill('#tasks input[data-f="q"]', target[0])
            pg.wait_for_timeout(600)
            pg.eval_on_selector_all(".tg-card", "ns => ns[0] && ns[0].click()")
            pg.wait_for_timeout(350)
            foreign = pg.evaluate("""(n) => { const c = [...document.querySelectorAll(
                '[data-tg-detail] .tg-chip.is-doc')].find(x => x.dataset.tool === n);
                if (!c) return null; c.click(); return c.dataset.tool; }""", target[1])
            print(f"       (a {'/'.join(target[2])} task offered `{target[1]}`)")
            if foreign:
                pg.wait_for_timeout(700)
                got = pg.evaluate("""() => { const d = document.querySelector(
                    '[data-tg-detail] .tg-doc:not([hidden])');
                    return { gym: d.querySelector('.tg-doc-gym')?.textContent.replace(/\\s+/g,' ') || '',
                             desc: d.querySelector('.tg-doc-d')?.textContent || '',
                             none: !!d.querySelector('.tg-doc-none') }; }""")
                check(not got["none"] and len(got["desc"]) > 20,
                      f"`{foreign}` still has a description", got["desc"][:60])
                check("into this task's pool" in got["gym"],
                      "and it says the tool was served in from another gym", got["gym"][:90])
            else:
                check(False, f"the chip for `{target[1]}` was there to open")

            print("\nWhere the gyms cannot answer")
            pg.evaluate("() => document.querySelector('[data-tg-close]')?.click()")
            pg.fill('#tasks input[data-f="q"]', "")     # the id search above still narrows to one
            pg.select_option("#tg-domain", "")
            for env, track, lab in (("ale", "tools", "ALE software"),
                                    ("eog", "skills", "EOG skills"),
                                    ("eog", "agents", "EOG agents")):
                pg.select_option("#tg-env", env)
                pg.select_option("#tg-track", track)
                pg.wait_for_timeout(400)
                pg.eval_on_selector_all(".tg-card", "ns => ns[0].click()")
                pg.wait_for_timeout(300)
                groups = pg.evaluate("""() => {
                    const out = [];
                    document.querySelectorAll('[data-tg-detail] .tg-h4').forEach(h => {
                      let n = h.nextElementSibling, chips = [];
                      while (n && !n.classList.contains('tg-h4')) {
                        chips.push(...n.querySelectorAll('.tg-chip')); n = n.nextElementSibling; }
                      if (chips.length) out.push([h.textContent.trim(),
                        chips.filter(c => c.classList.contains('is-doc')).length, chips.length]);
                    });
                    return out; }""")
                # Only tool groups may be openable. On a skills or agents task that is the
                # mounted-tools group: those are gym tools whoever the task is about, while
                # the skills and agents themselves are documented nowhere the page can read.
                wrong = [g for g in groups if g[1] and "ools mounted" not in g[0]
                         and not g[0].startswith("Oracle tools")]
                check(not wrong, f"{lab}: nothing but tools is openable",
                      str([g[0] for g in wrong]))
                pg.evaluate("() => document.querySelector('[data-tg-close]')?.click()")
                pg.wait_for_timeout(150)

            check(not errs, "no page errors throughout", str(errs[:2]))
            browser.close()
    finally:
        srv.shutdown()

    print(f"\n{checks - len(fails)}/{checks} checks passed")
    for f in fails:
        print(f"  FAIL  {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
