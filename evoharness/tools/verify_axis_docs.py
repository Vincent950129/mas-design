#!/usr/bin/env python3
"""Checks for the skill, agent and software descriptions behind the Task Gallery's chips.

    python tools/verify_axis_docs.py

Companion to verify_tool_docs.py, which covers the gym tools. Every other chip a
task carries now opens too, and each axis can go wrong in its own way.

Skills are the easy case: one definition per name, identical wherever it is
staged. Agents are not. 37 of the 38 EOG specialist names mean something
different depending on the system they belong to -- `user_group` owns four
different tool sets across CSM, HR, ITSM and the hybrid -- so a lookup by name
alone would be right most of the time and silently wrong the rest. These checks
open the same specialist on tasks from different domains and insist the answers
differ, the same way the tool checks do across gyms.

ALE software has the opposite problem. Nothing in the environment says what
Blender is, and the panel must not pretend otherwise: what it shows is how the
harness provisions and polices each label, and which specialist owns it. The
checks here hold it to that, and to resolving both spellings the corpus uses --
the tools axis lowercases to `anndata`, the software list keeps `AnnData`.

Cost is the last of it. This payload is fetched only when a chip is opened, and
opening a piece of software must not also drag in the gym schemas.
"""
from __future__ import annotations

import functools
import http.server
import json
import pathlib
import re
import socketserver
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT.parent
DOCS = ROOT / "static/axis_docs.json"
TASKS = ROOT / "static/tasks.json"
PAGE = "/evoharness/index.html"

# Field offsets into the interned task tuples, mirroring app.js.
T_TRACK, T_ENV, T_DOM, T_TID, T_ORACLE, T_CUM, T_SOFT = 0, 1, 2, 7, 12, 13, 15

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


def texts(doc: dict) -> list[str]:
    """Every string the panel would render from one entry."""
    out = [doc.get("t", ""), doc.get("d", "")] + list(doc.get("w") or [])
    for _head, blocks, *_ in doc.get("s") or []:
        for b in blocks:
            if b[0] in ("p", "h"):
                out.append(b[1])
            elif b[0] in ("ul", "ol"):
                out += b[1]
            elif b[0] == "t":
                out += b[1] + [c for row in b[2] for c in row]
    return out


def main() -> int:
    d = json.loads(TASKS.read_text())
    ax = json.loads(DOCS.read_text())
    lists, pool = d["lists"], d["names"]

    def names(i: int) -> list[str]:
        return [pool[j] for j in lists[i]] if i >= 0 else []

    skills = ax.get("skills") or {}
    agents = ax.get("agents") or {}
    soft = ax.get("software") or {}

    # Resolution exactly as app.js does it.
    def skill_of(env: str, name: str):
        return (skills.get(env) or {}).get(name)

    def agent_of(env: str, dom: str, name: str):
        if env == "ale":
            return (agents.get("ale") or {}).get(name), True
        by_dom = agents.get("eog") or {}
        if name in (by_dom.get(dom) or {}):
            return by_dom[dom][name], True
        others = [k for k in by_dom if name in by_dom[k]]
        return (by_dom[others[0]][name], False) if others else (None, False)

    def soft_of(name: str):
        return (soft.get("items") or {}).get((soft.get("alias") or {}).get(name, name.lower()))

    print("Payload")
    check(bool(skills) and bool(agents) and bool(soft),
          "axis_docs.json carries all three axes")
    check(set(skills) == {"eog", "ale"} and set(agents) == {"eog", "ale"},
          "each is split by environment", f"skills {sorted(skills)}, agents {sorted(agents)}")
    kb = DOCS.stat().st_size // 1024
    check(kb < 400, "it stays a fraction of the corpus it annotates", f"{kb} KB")

    # What the corpus asks of each axis, per task, the way a reader would open it.
    want: dict[tuple[str, str], set[str]] = {}
    for t in d["tasks"]:
        env, track = d["envs"][t[T_ENV]], d["tracks"][t[T_TRACK]]
        axis = "software" if (env == "ale" and track == "tools") else track
        want.setdefault((env, axis), set()).update(names(t[T_ORACLE]), names(t[T_CUM]))
        if names(t[T_SOFT]):
            want.setdefault((env, "software"), set()).update(names(t[T_SOFT]))

    print("\nCoverage")
    for env in ("eog", "ale"):
        asked = want.get((env, "skills"), set())
        missing = sorted(n for n in asked if not skill_of(env, n))
        check(not missing and asked, f"{env.upper()}: all {len(asked)} skills have a definition",
              str(missing[:4]))
    asked = want.get(("ale", "agents"), set())
    missing = sorted(n for n in asked if not agent_of("ale", "ale", n)[0])
    check(not missing and asked, f"ALE: all {len(asked)} specialists are on the roster",
          str(missing[:4]))

    # An EOG task answers for its agents out of its own library. This is where the axes
    # part company: a tool pool spills across gyms, because the cumulative harness keeps
    # handing a CSM task calendar and drive tools it has no use for, and a fifth of those
    # chips are documented by a gym the task never declares. Specialists do not travel that
    # way -- the roster a stage grows is its own domain's -- so the fallback in app.js is a
    # guard against a corpus that does, not a path this one takes.
    own = cross = unknown = 0
    own_oracle = miss_oracle = 0
    for t in d["tasks"]:
        if d["envs"][t[T_ENV]] != "eog" or d["tracks"][t[T_TRACK]] != "agents":
            continue
        dom = d["domains"][t[T_DOM]]
        for n in set(names(t[T_ORACLE])):
            hit, mine = agent_of("eog", dom, n)
            own_oracle += 1 if (hit and mine) else 0
            miss_oracle += 0 if hit else 1
        for n in set(names(t[T_ORACLE])) | set(names(t[T_CUM])):
            hit, mine = agent_of("eog", dom, n)
            if hit and mine:
                own += 1
            elif hit:
                cross += 1
            else:
                unknown += 1
    total = own + cross + unknown
    check(not miss_oracle and own_oracle,
          "every specialist a task actually needs is defined by its own domain",
          f"{own_oracle} oracle mentions, {miss_oracle} unresolved")
    check(not unknown, "and everything its pool offers resolves too", f"{unknown} unresolved")
    check(not cross, "no agents pool reaches outside its own domain, as the tool pools do",
          f"{cross} of {total} mentions would fall back")

    literals = want.get(("ale", "software"), set())
    missing = sorted(n for n in literals if not soft_of(n))
    check(not missing, f"all {len(literals)} software labels resolve", str(missing[:4]))
    pairs = [(n, n.lower()) for n in literals if n != n.lower() and n.lower() in literals]
    same = [n for n, low in pairs if soft["alias"][n] != soft["alias"][low]]
    check(pairs and not same, f"{len(pairs)} labels the two axes spell differently collapse to one",
          str(same[:4]))
    versioned = {n: soft["alias"][n] for n in literals if re.search(r"\d|/", n)}
    check(len(versioned) >= 8, "versions and wrapper scripts collapse onto the software itself",
          f"{len(versioned)} such labels, e.g. " + ", ".join(
              f"{k!r}\u2192{v}" for k, v in sorted(versioned.items())[:2]))

    print("\nWhat a panel has to show")
    thin = [f"{env}/{n}" for env in ("eog", "ale") for n, e in (skills.get(env) or {}).items()
            if not e.get("t") or len(e.get("d", "")) < 20 or not e.get("s")]
    check(not thin, "every skill carries a title, a description and its brief", str(thin[:4]))
    all_agents = [(f"eog/{dom}", n, e) for dom, docs in (agents.get("eog") or {}).items()
                  for n, e in docs.items()]
    all_agents += [("ale", n, e) for n, e in (agents.get("ale") or {}).items()]
    thin = [f"{w}/{n}" for w, n, e in all_agents
            if not e.get("t") or len(e.get("d", "")) < 20 or not e.get("w")]
    check(not thin, f"all {len(all_agents)} specialists say what they are and what they own",
          str(thin[:4]))
    echoed = [f"{w}/{n}" for w, n, e in all_agents if e.get("d", "").strip() == n]
    check(not echoed, "no description is the name handed back", str(echoed[:4]))

    items = soft.get("items") or {}
    unowned = sorted(c for c, i in items.items() if not i.get("ft"))
    check(not unowned, f"all {len(items)} pieces of software have an owning specialist",
          str(unowned[:4]))
    known = [c for c, i in items.items() if i.get("k")]
    check(len(known) / len(items) > 0.8, "most carry an identity from the registry",
          f"{len(known)}/{len(items)}")
    check(all("e" in i for i in items.values() if i.get("k")),
          "and each of those says whether a guard can hold it to its stage")
    guarded = [c for c, i in items.items() if i.get("e")]
    check(0 < len(guarded) < len(items),
          "which is true of some and not others, as the registry has it",
          f"{len(guarded)} guarded, {len(items) - len(guarded)} on the prompt's word")

    print("\nWhy agents are kept per domain")
    by_dom = agents.get("eog") or {}
    shared = {}
    for dom, docs in by_dom.items():
        for n in docs:
            shared.setdefault(n, []).append(dom)
    multi = {n: ds for n, ds in shared.items() if len(ds) > 1}
    collapsed = [n for n, ds in multi.items()
                 if len({by_dom[x][n]["d"] for x in ds}) == 1
                 and len({tuple(by_dom[x][n].get("w") or ()) for x in ds}) == 1]
    check(len(multi) >= 20, f"{len(multi)} names appear in more than one library")
    check(len(collapsed) <= 1, "and nearly none of them mean the same thing in two",
          f"{len(collapsed)} identical: {collapsed[:3]}")
    spread = max((len({tuple(by_dom[x][n].get("w") or ()) for x in ds}) for n, ds in multi.items()),
                 default=0)
    check(spread >= 3, "one name reaches three or more different tool sets", f"{spread} sets")

    print("\nBriefs, as they will be rendered")
    ragged, tainted, empty = [], [], []
    for label, name, e in all_agents + [(f"skill/{env}", n, s)
                                        for env in ("eog", "ale")
                                        for n, s in (skills.get(env) or {}).items()]:
        for head, blocks, *abridged in e.get("s") or []:
            if not blocks:
                empty.append(f"{label}/{name}/{head}")
            if abridged and not any(b[0] == "ul" for b in blocks):
                empty.append(f"{label}/{name}/{head} abridged to nothing")
            for b in blocks:
                if b[0] == "t" and any(len(r) != len(b[1]) for r in b[2]):
                    ragged.append(f"{label}/{name}/{head}")
        if any("<script" in x.lower() or "javascript:" in x.lower() for x in texts(e)):
            tainted.append(f"{label}/{name}")
    check(not empty, "no section was kept with nothing in it", str(empty[:3]))
    check(not ragged, "every table's rows match its header", str(ragged[:3]))
    check(not tainted, "nothing in the payload is trying to be markup", str(tainted[:3]))

    srv, base = serve()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            pg = browser.new_page(viewport={"width": 1100, "height": 1000})
            errs: list[str] = []
            got: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("request", lambda r: r.url.endswith("_docs.json") and got.append(
                r.url.rsplit("/", 1)[-1]))
            pg.goto(base, wait_until="load")
            pg.evaluate("PV.open('tasks')")
            pg.wait_for_timeout(800)

            def open_first(env: str, track: str, domain: str = "") -> None:
                pg.evaluate("() => document.querySelector('[data-tg-close]')?.click()")
                pg.select_option("#tg-env", env)
                pg.select_option("#tg-track", track)
                pg.select_option("#tg-domain", domain)
                pg.wait_for_timeout(450)
                pg.eval_on_selector_all(".tg-card", "ns => ns[0] && ns[0].click()")
                pg.wait_for_timeout(350)

            def click(kind: str, name: str | None = None):
                """Open a chip of one kind, by name or the first there is.

                Across every group of that kind, not just the first: a specialist a task
                does not need still sits in the pool below the oracle set.
                """
                return pg.evaluate(
                    """([kind, name]) => {
                        const cs = [...document.querySelectorAll(
                          `[data-tg-detail] [data-kind="${kind}"] .tg-chip.is-doc`)];
                        const c = name ? cs.find((x) => x.dataset.doc === name) : cs[0];
                        if (!c) return null;
                        c.click();
                        return c.dataset.doc; }""", [kind, name])

            def panel():
                return pg.evaluate("""() => {
                    const d = document.querySelector('[data-tg-detail] .tg-doc:not([hidden])');
                    if (!d) return null;
                    const dt = [...d.querySelectorAll('.tg-doc-facts dt')].map(x => x.textContent);
                    return { name: d.querySelector('.tg-doc-name')?.textContent.trim() || '',
                             title: d.querySelector('.tg-doc-title')?.textContent.trim() || '',
                             note: (d.querySelector('.tg-doc-gym')?.textContent || '')
                                     .replace(/\\s+/g, ' ').trim(),
                             desc: d.querySelector('.tg-doc-d')?.textContent.trim() || '',
                             secs: [...d.querySelectorAll('.tg-doc-sec')].map(x =>
                                     x.textContent.replace(/\\s+/g, ' ').trim()),
                             facts: dt,
                             factText: [...d.querySelectorAll('.tg-doc-facts dd')]
                                     .map(x => x.textContent.replace(/\\s+/g, ' ').trim()),
                             steps: d.querySelectorAll('.tg-doc-list li').length,
                             none: !!d.querySelector('.tg-doc-none') }; }""")

            print("\nCost")
            open_first("eog", "skills")
            check(not got, "nothing is fetched until a chip is opened", str(got))

            print("\nAn EOG skill")
            name = click("skill")
            pg.wait_for_timeout(1200)
            check(got == ["axis_docs.json"], "opening one fetches this payload and only it",
                  str(got))
            got_skill = panel()
            check(bool(got_skill) and not got_skill["none"], "a panel opens with the answer")
            if got_skill:
                check(got_skill["name"] == name, "about the chip that was clicked",
                      f"{got_skill['name']} vs {name}")
                check(len(got_skill["title"]) > 3 and got_skill["title"] != name,
                      "titled in prose rather than by its slug", got_skill["title"])
                check(len(got_skill["desc"]) > 40, "with the routing description it was written with",
                      got_skill["desc"][:60])
                check(len(got_skill["secs"]) >= 2, "and its brief, section by section",
                      " / ".join(got_skill["secs"]))
                check(any("Records" in f for f in got_skill["facts"]),
                      "including the records a run of it touches", str(got_skill["facts"]))
            pg.eval_on_selector_all("[data-tg-detail] .tg-chip.is-doc.is-open", "ns => ns[0].click()")
            pg.wait_for_timeout(250)
            check(pg.eval_on_selector_all(
                "[data-tg-detail] .tg-doc:not([hidden])", "ns => ns.length") == 0,
                "clicking the open chip again closes it")

            print("\nAn EOG specialist, read from three libraries")
            # The name to try comes from the corpus, not a guess: one that tasks in all
            # three browsable domains reach for, and that all three libraries describe
            # differently and hand a different tool set.
            HOMES = ("csm", "hr", "itsm")
            asked_in: dict[str, dict[str, str]] = {}
            for t in d["tasks"]:
                if d["envs"][t[T_ENV]] != "eog" or d["tracks"][t[T_TRACK]] != "agents":
                    continue
                dom = d["domains"][t[T_DOM]]
                if dom not in HOMES:
                    continue
                for n in set(names(t[T_ORACLE])) | set(names(t[T_CUM])):
                    asked_in.setdefault(n, {}).setdefault(dom, t[T_TID])
            reading = lambda n, x: (by_dom[x][n]["d"], tuple(by_dom[x][n].get("w") or ()))
            candidates = sorted(
                (n for n, ds in multi.items()
                 if all(x in ds and x in asked_in.get(n, {}) for x in HOMES)
                 and len({reading(n, x) for x in HOMES}) == 3
                 and len({reading(n, x)[1] for x in HOMES}) == 3),
                key=lambda n: -len(multi[n]))
            check(bool(candidates), "the corpus has a specialist all three domains disagree about",
                  str(candidates[:3]))
            seen = {}
            if candidates:
                pick = candidates[0]
                # Which task to open is a question for the corpus too: however the gallery
                # happens to sort today, the first row of a domain need not be one that
                # carries this specialist.
                where = asked_in[pick]
                pg.evaluate("() => document.querySelector('[data-tg-close]')?.click()")
                pg.select_option("#tg-env", "eog")
                pg.select_option("#tg-track", "agents")
                pg.select_option("#tg-domain", "")
                for dom, tid in sorted(where.items()):
                    pg.evaluate("() => document.querySelector('[data-tg-close]')?.click()")
                    pg.fill('#tasks input[data-f="q"]', tid)
                    pg.wait_for_timeout(500)
                    pg.eval_on_selector_all(".tg-card", "ns => ns[0] && ns[0].click()")
                    pg.wait_for_timeout(350)
                    if click("agent", pick):
                        pg.wait_for_timeout(400)
                        seen[dom] = panel()
                pg.evaluate("() => document.querySelector('[data-tg-close]')?.click()")
                pg.fill('#tasks input[data-f="q"]', "")
                check(len(seen) == len(HOMES), f"opened `{pick}` in all three domains",
                      str(sorted(seen)))
                for dom, p_ in seen.items():
                    check(dom.lower() in p_["note"].lower(),
                          f"a {dom.upper()} task credits the {dom.upper()} library", p_["note"][:70])
                    check(any("Owns" in f for f in p_["facts"]),
                          f"and lists what the {dom.upper()} one owns", str(p_["facts"]))
                said = {dom: p_["desc"] for dom, p_ in seen.items()}
                check(len(set(said.values())) == len(said),
                      "the same name reads differently in each, as the libraries have it",
                      " | ".join(f"{k}: {v[:30]}" for k, v in said.items()))
                owns = {dom: tuple(p_["factText"]) for dom, p_ in seen.items()}
                check(len(set(owns.values())) > 1, "and owns a different set of tools")

            print("\nALE software")
            open_first("ale", "tools")
            name = click("software")
            pg.wait_for_timeout(500)
            p_ = panel()
            check(bool(p_) and not p_["none"], f"`{name}` opens", str(name))
            if p_:
                check(bool(p_["title"]), "saying what kind of thing it is", p_["title"])
                check(any("stage" in f.lower() for f in p_["facts"]),
                      "how far the stage limit can reach it", str(p_["facts"]))
                check(any("Owned by" in f for f in p_["facts"]),
                      "and which specialist owns it", str(p_["facts"]))
                check("provisions" in p_["note"], "framed as provisioning, not as a product blurb",
                      p_["note"])
                check(not p_["secs"], "with no brief invented for it")
            check(got == ["axis_docs.json"], "and no gym schemas fetched for it", str(got))

            print("\nALE skills and specialists")
            open_first("ale", "skills")
            name = click("skill")
            pg.wait_for_timeout(400)
            p_ = panel()
            check(bool(p_) and not p_["none"], f"an ALE skill opens", str(name))
            if p_:
                check(p_["steps"] >= 3, "with the procedure it teaches", f"{p_['steps']} list items")
                check("mined from the ALE corpus" in p_["note"], "and where it came from",
                      p_["note"])
            check(bool(click("software")), "its software chips open in the same modal")
            open_first("ale", "agents")
            name = click("agent")
            pg.wait_for_timeout(400)
            p_ = panel()
            check(bool(p_) and not p_["none"], f"an ALE specialist opens", str(name))
            if p_:
                check(any("software" in f for f in p_["facts"]),
                      "listing the software stack it owns", str(p_["facts"]))

            print("\nReachable by keyboard")
            open_first("eog", "agents")
            pg.evaluate("""() => document.querySelector(
                '[data-tg-detail] .tg-chip.is-doc').focus()""")
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(400)
            check(bool(panel()), "a focused chip opens on Enter")
            check(pg.evaluate("""() => document.activeElement ===
                document.querySelector('[data-tg-detail] .tg-chip.is-doc.is-open')"""),
                  "and keeps the focus that opened it")

            check(not errs, "no page errors throughout", str(errs[:2]))

            print("\nWhen the payload cannot be had")
            # A fresh page, because the loaded copy is kept for the session.
            blind = browser.new_page(viewport={"width": 1100, "height": 900})
            blind_errs: list[str] = []
            blind.on("pageerror", lambda e: blind_errs.append(str(e)))
            blind.route("**/axis_docs.json", lambda route: route.abort())
            blind.goto(base, wait_until="load")
            blind.evaluate("PV.open('tasks')")
            blind.wait_for_timeout(900)
            blind.select_option("#tg-env", "eog")
            blind.select_option("#tg-track", "skills")
            blind.wait_for_timeout(450)
            blind.eval_on_selector_all(".tg-card", "ns => ns[0] && ns[0].click()")
            blind.wait_for_timeout(350)
            blind.eval_on_selector_all(
                '[data-tg-detail] [data-kind="skill"] .tg-chip.is-doc', "ns => ns[0].click()")
            blind.wait_for_timeout(1200)
            said = blind.evaluate("""() => { const d = document.querySelector(
                '[data-tg-detail] .tg-doc:not([hidden])');
                return d ? d.textContent.replace(/\\s+/g, ' ').trim() : null; }""")
            check(bool(said) and "could not be loaded" in said,
                  "a chip says so rather than sitting on a spinner", str(said)[:70])
            check(not blind_errs, "and nothing throws on the way", str(blind_errs[:2]))
            browser.close()
    finally:
        srv.shutdown()

    print(f"\n{checks - len(fails)}/{checks} checks passed")
    for f in fails:
        print(f"  FAIL  {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
