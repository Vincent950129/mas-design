#!/usr/bin/env python3
"""Checks for the Create Your Benchmark tab: bring your own seed benchmark.

The tab's whole claim is that a reader can build a stream out of their own suite from
what is printed on this page. So none of it is trusted here. Every code block is lifted
off the rendered DOM, assembled the way a reader would assemble it, and run: the four
steps against a synthetic seed, each axis helper against the shape it says it reads, and
both worked examples against a fake Terminal-Bench checkout and a fake APEX-Agents load.
Printing an algorithm that does not run is worse than printing none.

The rest guards the wiring. Two views carry a .sv-tab strip, and those strips used to be
one global group, so a click in either would blank the other's panels -- a regression
that is invisible on the tab you are looking at and obvious on the one you are not. Also
pins the Evaluate -> Evaluation rename: the label is a noun now, but the view key has to
stay `evaluate`, because the floor's own CTA links to #evaluate.

No network needed. Expects a static server: python3 -m http.server 8777 from the
directory above evoharness/.
"""
from __future__ import annotations

import json
import os
import pathlib
import random
import re
import sys
import tempfile

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "tools/proofs"
BASE = "http://127.0.0.1:8777/evoharness/index.html"

# The tab strip, in order. The label a reader sees, and the view key the router uses --
# they differ for Evaluation on purpose and the comment in index.html says why.
TABS = [("overview", "Overview"), ("benchmark", "Benchmark"), ("tasks", "Tasks"),
        ("results", "Results"), ("cases", "Cases"), ("evaluate", "Evaluation"),
        ("leaderboard", "Leaderboard"), ("construction", "Create Your Benchmark")]
AXES = ["tools", "skills", "agents"]        # the construction strip
# Figures the prose quotes from the paper. Every one of them is a number a reader could
# repeat in a review, so a silent edit here should fail rather than ship.
FIGURES = ["17 streams", "76.6%", "85.2%", "62 specialists", "42 skills",
           "three of our eight",
           # And what it says about the two seeds, which is other people's work: APEX's
           # own card gives 480 tasks over 33 worlds graded by a judge model against a
           # rubric, and a Terminal-Bench task is scored by running its own tests.
           "480 long-horizon", "33 worlds", "judge", "its own tests"]
SEEDS = {"https://www.tbench.ai/": "Terminal-Bench",
         "https://huggingface.co/datasets/mercor/apex-agents": "APEX-Agents"}

fails: list[str] = []
checks = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global checks
    checks += 1
    print(f"  {'ok  ' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        fails.append(label + (f": {detail}" if detail else ""))


def strips(pg) -> dict:
    """Which panel is active in each of the page's .sv-tab strips, by owning view."""
    return pg.evaluate("""() => {
      const out = {};
      document.querySelectorAll('.pv-view').forEach((v) => {
        const tabs = [...v.querySelectorAll('.sv-tab')];
        if (!tabs.length) return;
        out[v.dataset.pvView] = {
          tab: tabs.filter((t) => t.classList.contains('is-active')).map((t) => t.dataset.sv),
          panel: [...v.querySelectorAll('.sv-panel.is-active')].map((p) => p.dataset.svPanel),
        };
      });
      return out;
    }""")


def blocks(pg) -> list[tuple[str, str]]:
    """(file label, source) for every code block in the view, in the order it prints."""
    return [tuple(b) for b in pg.evaluate("""() => [...document.querySelectorAll(
      '[data-pv-view="construction"] .sv-codewrap')].map((w) => [
        w.querySelector('.sv-lang').textContent.replace(/^python\\s*·?\\s*/, '').trim(),
        w.querySelector('.sv-code code').textContent])""")]


def run(src: str, label: str, ns: dict | None = None) -> dict:
    """Exec one block the way a reader would, with its evolve/datasets imports resolved
    from what has already been defined rather than from the filesystem."""
    ns = dict(ns or {})
    src = re.sub(r"^from (?:evolve|datasets) import .*$", "", src, flags=re.M)
    exec(compile(src, f"<{label}>", "exec"), ns)          # noqa: S102
    return ns


def synth_seed(n: int = 140, seed: int = 0):
    """A seed with the shape the tab says it needs: a small core, a long tail. Labels
    are mixed-case on purpose -- canonicalization is step 1's whole job."""
    rng = random.Random(seed)
    core = [f"Core_{i}" for i in range(7)]
    tail = [f"tail_{i}" for i in range(26)]
    tasks = []
    for i in range(n):
        caps = rng.sample(core, rng.randint(1, 3))
        if rng.random() < 0.6:
            caps += rng.sample(tail, rng.randint(1, 2))
        tasks.append({"task_id": f"t{i}", "required_tools": caps})
    tasks.append({"task_id": "unannotated", "required_tools": []})
    tasks.append({"task_id": "private", "required_tools": ["Seen_once_only"]})
    return tasks, [c.lower() for c in core], [c.lower() for c in tail]


def check_library(lib: dict, tmp: pathlib.Path) -> dict:
    """The four steps, on a seed built to the tab's own preconditions."""
    print("\nThe four steps, as printed")
    want = {"annotate", "release_schedule", "date_tasks", "harness", "stream", "manifest",
            "write"}
    check(want <= set(lib), "the blocks assemble into one module",
          f"missing {sorted(want - set(lib))}" if want - set(lib) else f"{len(want)} functions")
    if not want <= set(lib):
        return {}

    tasks, core, _ = synth_seed()
    ann = lib["annotate"](tasks, lambda t: t["required_tools"])
    check("core_0" in {c for caps in ann.values() for c in caps},
          "step 1 folds aliases: Core_0 and core_0 are one capability")
    check("unannotated" not in ann, "and an unannotated task is dropped, not guessed at",
          f"{len(ann)} of {len(tasks)} tasks kept")

    staged, release = lib["release_schedule"](ann, stages=5, min_uses=2, min_new=5)
    check("seen_once_only" not in release and "private" not in staged,
          "step 2 drops a capability one task needs, and that task with it")
    check(min(release[c] for c in core) == 1 and max(release[c] for c in core) <= 2,
          "the capabilities most tasks need are released first",
          f"core lands at stages {sorted({release[c] for c in core})}")

    H, at = lib["harness"](release), lib["date_tasks"](staged, release)
    check(3 <= len(H) <= 5, "step 3 gives a stream of stages, not a pile", f"{len(H)} stages")
    check(all(H[t] < H[t + 1] for t in range(1, len(H))),
          "the harness grows strictly, and never withdraws",
          " → ".join(str(len(H[t])) for t in sorted(H)))
    check(all(staged[i] <= H[t] for i, t in at.items()),
          "step 4 dates every task to a stage that can already solve it")
    check(all(staged[i] & (H[t] - H.get(t - 1, frozenset())) for i, t in at.items()),
          "and every task needs something its own stage introduced")

    try:
        rows = lib["stream"](staged, release, domain="synth")
    except AssertionError as e:
        check(False, "stream() holds its own two asserts", f"assert failed: {e}")
        return lib
    landed = {t: sum(r["version"] == f"v{t}" for r in rows) for t in sorted(H)}
    check(min(landed.values()) >= 5, "no stage is left too thin to read",
          " ".join(f"v{t}:{n}" for t, n in landed.items()))
    per = {t: [r["split"] for r in rows if r["version"] == f"v{t}"] for t in sorted(H)}
    check(all(s.count("train") >= 1 and s.count("test") >= 3 for s in per.values()),
          "and both split floors hold at every stage",
          " ".join(f"v{t}:{s.count('train')}/{s.count('test')}" for t, s in per.items()))
    check(all(set(r["oracle"]) <= set(r["cumulative"]) for r in rows),
          "every row's gold set is inside what its stage offers")
    check(any(set(r["cumulative"]) - set(r["oracle"]) for r in rows),
          "and the pool carries distractors, so selection is part of the task")

    again = lib["release_schedule"](lib["annotate"](tasks, lambda t: t["required_tools"]),
                                   stages=5, min_uses=2, min_new=5)
    check(again[1] == release, "a second build releases identically")
    check(lib["stream"](*again, domain="synth") == rows, "and writes identical rows")

    out = tmp / "synth"
    lib["write"](rows, out, lib["manifest"](staged, release, rows, judge="none"))
    on_disk = sum(1 for f in sorted(out.rglob("*.jsonl")) for _ in f.read_text().splitlines())
    check(on_disk == len(rows), "write() puts every row in v_k/{train,test}.jsonl",
          f"{on_disk} rows over {len(list(out.rglob('*.jsonl')))} files")
    meta = json.loads((out / "manifest.json").read_text())
    check(meta["stages"] == len(H) and meta["release"] == release and meta["judge"] == "none",
          "and the manifest beside them says what arrived when", str(sorted(meta)))

    try:
        lib["release_schedule"]({"a": frozenset({"x"}), "b": frozenset({"y"})}, min_uses=2)
        check(False, "a seed with no repeated capability is refused")
    except ValueError as e:
        check(True, "a seed with no repeated capability is refused, by name", str(e)[:44])
    return lib


def check_axes(lib: dict, per_file: dict) -> None:
    """Each axis panel's step 1: the annotation it produces on the shape it describes."""
    print("\nThe annotation, per axis")

    tools = run(per_file["tools_axis.py"], "tools_axis", lib)
    got = tools["tool_capabilities"]({"task_id": "a", "oracle_tools": ["mail.send"]})
    check(got == ["mail.send"], "tools: it finds the annotation field the seed happens to use",
          str(got))
    check(tools["tool_capabilities"]({"task_id": "a", "notes": "x"}) == [],
          "and returns nothing rather than a guess when there is no field")
    given = tools["as_given"]({"task_id": "a"}, {"cumulative": ["a.x", "b.y"], "oracle": ["a.x"]},
                              {"a.x": {"n": 1}, "b.y": {"n": 2}})
    check(given["selected_tools"] == ["a.x", "b.y"] and len(given["tool_specs"]) == 2,
          "and the agent is handed the cumulative pool, not the oracle set", str(given))

    skills = run(per_file["skills_axis.py"], "skills_axis", lib)
    prompt = ("General setup, always applicable.\n"
              "## Refund policy\n" + "Follow the refund ladder. " * 30 +
              "\n## Note\ntoo short to be a procedure\n")
    mined, left = skills["mine_skills"](prompt)
    check(list(mined) == ["refund_policy"], "skills: a shared policy is cut on its own headings",
          str(list(mined)))
    check("refund ladder" not in left and "too short" in left,
          "and what was cut is REMOVED from the prompt, which is the point")
    reads = {"t_value": {"fields": ["amount"], "values": ["refund ladder"]},
             "t_field": {"fields": ["amount"], "values": []},
             "t_book": {"fields": ["id", "status"], "values": []}}
    need = {i: skills["skill_capabilities"]({"task_id": i}, mined, lambda t: reads[t["task_id"]])
            for i in reads}
    check(need["t_value"] == {"refund_policy"}, "a value the grader asserts decides on its own")
    check(need["t_field"] == set(), "one bare field name does not")
    check(need["t_book"] == set(), "and bookkeeping columns are ignored")

    agents = run(per_file["agents_axis.py"], "agents_axis", lib)
    tool_ann = {"t1": frozenset({"mail.send", "mail.search"}), "t2": frozenset({"sheet.write"}),
                "t3": frozenset({"mail.send", "sheet.write", "cal.add"})}
    bundles, agent_ann = agents["induce_agents"](tool_ann)
    check(set(bundles) == {"mail", "sheet", "cal"}, "agents: the namespace is the partition",
          str({k: sorted(v) for k, v in bundles.items()}))
    check(agent_ann["t3"] == frozenset({"mail", "sheet", "cal"}),
          "a task needs the owners of the tools it needed", str(sorted(agent_ann["t3"])))
    staged, release = lib["release_schedule"](agent_ann, stages=3, min_uses=1, min_new=1)
    check(set(release) == set(bundles), "and the specialists go through the same steps 2-4",
          str(release))


def fake_terminal_bench(root: pathlib.Path) -> None:
    """Both task layouts that are in the wild, plus two directories that should be
    skipped: one with no reference solution, one that is not a task at all."""
    classic = root / "tasks/fix-the-pipeline"
    (classic / "tests").mkdir(parents=True)
    (classic / "Dockerfile").write_text(
        "FROM ghcr.io/laude-institute/t-bench:latest\n"
        "RUN apt-get update && apt-get install -y jq curl\n"
        "RUN pip install pandas==2.2.0 pyarrow\n")
    (classic / "solution.sh").write_text(
        "#!/bin/bash\ncd /app\njq '.rows' in.json > out.json\n"
        "python3 clean.py\nfor f in *.csv; do echo $f; done\n")
    (classic / "tests/test_outputs.py").write_text("import pytest\n")  # never read
    (classic / "task.yaml").write_text("instruction: fix it\n")

    harbor = root / "tasks/rotate-the-key"
    (harbor / "environment").mkdir(parents=True)
    (harbor / "solution").mkdir(parents=True)
    (harbor / "environment/Dockerfile").write_text(
        "FROM python:3.12\nRUN pip3 install pandas cryptography\n"
        "RUN apt-get install -y jq\n")
    (harbor / "solution/solve.sh").write_text("set -e\njq . keys.json\nopenssl rand -hex 16\n")
    (harbor / "task.toml").write_text('id = "rotate-the-key"\n')

    for i in range(14):     # enough tasks that a stream is not degenerate
        d = root / f"tasks/bulk-{i}"
        (d / "solution").mkdir(parents=True)
        (d / "environment").mkdir(parents=True)
        (d / "environment/Dockerfile").write_text(
            "FROM python:3.12\nRUN pip install pandas requests\n"
            + ("RUN apt-get install -y jq\n" if i % 2 else "RUN apt-get install -y curl\n"))
        (d / "solution/solve.sh").write_text(
            "python3 run.py\n" + ("jq . a.json\n" if i % 2 else "curl -s localhost\n")
            + ("openssl rand -hex 4\n" if i % 5 == 0 else ""))

    noise = root / "tasks/no-solution"
    noise.mkdir(parents=True)
    (noise / "Dockerfile").write_text("FROM python:3.12\n")
    (root / "tasks/.cache").mkdir(parents=True)


def check_worked_examples(lib: dict, per_file: dict, tmp: pathlib.Path) -> None:
    """Both examples, run end to end against a stand-in for the real seed."""
    print("\nWorked example 1 — Terminal-Bench, against a fake checkout")
    tb_root = tmp / "tb"
    fake_terminal_bench(tb_root / "terminal-bench")
    here = pathlib.Path.cwd()
    try:
        os.chdir(tb_root)          # so the snippet's own relative paths resolve
        tb = run(per_file["seed_terminal_bench.py"], "seed_terminal_bench", lib)
    except Exception as e:         # noqa: BLE001
        check(False, "the script runs", f"{type(e).__name__}: {e}")
        return
    finally:
        os.chdir(here)

    ids = {t["task_id"] for t in tb["tb_tasks"](tb_root / "terminal-bench/tasks")}
    check("fix-the-pipeline" in ids and "rotate-the-key" in ids,
          "it reads both task layouts, classic and Harbor", f"{len(ids)} tasks")
    check("no-solution" not in ids, "and skips a directory with no reference solution")

    caps = tb["tb_capabilities"]({
        "env": "RUN apt-get install -y jq\nRUN pip install pandas==2.2.0\n",
        "solution": "cd /app\nopenssl rand -hex 4\necho done\n"})
    check({"jq", "pandas", "openssl"} <= caps, "the Dockerfile gives libraries", str(sorted(caps)))
    check("cd" not in caps and "echo" not in caps, "shell noise is not a capability")
    check("pandas==2.2.0" not in caps, "and a pinned version is the same capability as the pin")
    folded = tb["tb_capabilities"]({"env": "RUN apt-get install -y nodejs\n",
                                    "solution": "pip3 install httpx\npython3 a.py\n"})
    check({"node", "pip", "python", "httpx"} == folded,
          "families fold, and a solution that installs something needs it", str(sorted(folded)))

    built = tb_root / "data/terminal_bench"
    stages = sorted(p.name for p in built.iterdir() if p.is_dir())
    check(len(stages) >= 3 and stages[0] == "v1",
          "and the run leaves a staged stream on disk, from v1 up", " ".join(stages))
    meta = json.loads((built / "manifest.json").read_text())
    check(meta.get("enforcement") == "allowlist-in-instruction",
          "with the enforcement choice pinned in its manifest", str(meta.get("enforcement")))

    print("\nWorked example 2 — APEX-Agents, against a fake load_dataset")
    rng = random.Random(7)
    prompts = [
        ("Reply to the email from the CFO and attach the xlsx model.", ["the email states the fee"]),
        ("Draft a memo in a document summarizing the filing.", ["the memo cites the pdf"]),
        ("Build a deck of 5 slides from the spreadsheet.", ["the presentation has a slide per year"]),
        ("Schedule a meeting and post to the channel.", ["the calendar invite exists"]),
    ]
    rows = []
    for i in range(60):
        prompt, crit = prompts[i % len(prompts)]
        rows.append({"task_id": f"apex_{i}", "world_id": f"w{i % 9}", "prompt": prompt,
                     "rubric": [{"criterion": c} for c in crit] +
                               ([{"criterion": "the python script runs"}] if i % 3 else [])})
    rng.shuffle(rows)
    ns = dict(lib, load_dataset=lambda *a, **k: rows)
    ax_root = tmp / "apex"
    ax_root.mkdir(parents=True)
    try:
        os.chdir(ax_root)
        ax = run(per_file["seed_apex_agents.py"], "seed_apex_agents", ns)
    except Exception as e:         # noqa: BLE001
        check(False, "the script runs", f"{type(e).__name__}: {e}")
        return
    finally:
        os.chdir(here)

    read = {t["task_id"]: t for t in ax["apex_tasks"]()}
    check(len(read) == len(rows), "it reads the rows the card documents", f"{len(read)} tasks")
    check(all("world" in t and t["text"] == t["text"].lower() for t in read.values()),
          "prompt and rubric criteria, folded into one lowercase field to match on")
    one = ax["apex_capabilities"](read["apex_0"])
    check(one == {"mail", "spreadsheets"},
          "a criterion about an email needs Mail, and an xlsx needs Spreadsheets", str(sorted(one)))
    built = ax_root / "data/apex_agents"
    stages = sorted(p.name for p in built.iterdir() if p.is_dir())
    check(len(stages) >= 3 and stages[0] == "v1", "and it too leaves a staged stream",
          " ".join(stages))
    meta = json.loads((built / "manifest.json").read_text())
    check(meta.get("judge"), "with the judge pinned, which is this seed's open requirement",
          str(meta.get("judge")))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    html = (ROOT / "index.html").read_text()

    print("\nThe tab strip")
    bar = re.findall(r'data-pv="([a-z]+)">([^<]+)<', html)
    check(bar == TABS, "eight views, in order, each under the label it shows a reader",
          " · ".join(f"{k}:{v}" for k, v in bar))
    check(re.search(r'href="#evaluate"', (ROOT / "app.js").read_text()) is not None,
          "the floor's CTA still points at #evaluate, which the rename left alone")

    logs: list[str] = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 1000})
        pg.on("console", lambda m: logs.append(f"{m.type}: {m.text}")
              if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
        pg.goto(BASE, wait_until="load")
        pg.wait_for_timeout(900)

        print("\nOpening it")
        st = strips(pg)
        check(set(st) == {"evaluate", "construction"},
              "two views own a tab strip", " ".join(sorted(st)))
        check(all(len(s["tab"]) == 1 and s["panel"] == s["tab"] for s in st.values()),
              "and each opens on exactly one of its own panels", str(st))

        pg.click('.pv-tab[data-pv="construction"]')
        pg.wait_for_timeout(350)
        open_views = pg.evaluate(
            "() => [...document.querySelectorAll('.pv-view.is-active')].map((v) => v.dataset.pvView)")
        check(open_views == ["construction"], "the tab opens one view", str(open_views))
        check(pg.is_visible("#construction h2"), "and the section renders")
        head = pg.inner_text("#construction h2").strip()
        check(head == "Construct Your Own Evolving Benchmark", "under its own heading", head)

        # textContent, not inner_text: two of the three axis panels are hidden at any time
        # and the figures in them still have to be there.
        body = pg.evaluate(
            "() => document.querySelector('[data-pv-view=\"construction\"]').textContent")
        missing = [f for f in FIGURES if f not in body]
        check(not missing, "the figures it quotes from the paper are all still there",
              str(missing))
        check("no LLM in the loop" in body and "GPU" in body,
              "and it says what construction does not need")

        print("\nThe seeds it points at")
        out = pg.evaluate("""() => [...document.querySelectorAll(
          '[data-pv-view="construction"] a[href^="http"]')].map((a) => ({
            href: a.href, text: a.textContent.trim(),
            safe: a.target === '_blank' && (a.rel || '').includes('noopener')}))""")
        for url, name in SEEDS.items():
            hits = [a for a in out if a["href"].rstrip("/") == url.rstrip("/")]
            check(bool(hits), f"{name} is linked", url)
            check(all(a["safe"] for a in hits), f"{name} opens in a new tab, safely",
                  str([a for a in hits if not a["safe"]]))
            check(any(name in a["text"] for a in hits), f"and the link is named {name}",
                  str([a["text"] for a in hits]))
        stray = [a["href"] for a in out if not any(
            a["href"].rstrip("/") == u.rstrip("/") for u in SEEDS)]
        check(not stray, "and nothing else leaves the page from here", str(stray))

        print("\nThe axis strip switches on its own")
        for ax in AXES:
            pg.click(f'[data-pv-view="construction"] .sv-tab[data-sv="{ax}"]')
            pg.wait_for_timeout(220)
            st = strips(pg)
            check(st["construction"]["panel"] == [ax],
                  f"{ax}: one panel open, and it is the one asked for",
                  str(st["construction"]))
            check(len(st["evaluate"]["panel"]) == 1,
                  f"{ax}: the service quickstart keeps its own panel",
                  str(st["evaluate"]["panel"]))
        pg.screenshot(path=str(OUT / "construction.png"), full_page=True)

        print("\nAnd the service strip is still independent of it")
        pg.click('.pv-tab[data-pv="evaluate"]')
        pg.wait_for_timeout(300)
        pg.click('[data-pv-view="evaluate"] .sv-tab[data-sv="ports"]')
        pg.wait_for_timeout(220)
        st = strips(pg)
        check(st["evaluate"]["panel"] == ["ports"], "clicking one moves that strip",
              str(st["evaluate"]))
        check(st["construction"]["panel"] == [AXES[-1]],
              "and leaves the construction strip where the reader left it",
              str(st["construction"]))

        print("\nWhere it sends the reader")
        pg.click('.pv-tab[data-pv="construction"]')
        pg.wait_for_timeout(250)
        hrefs = pg.evaluate("""() => [...document.querySelectorAll(
          '[data-pv-view="construction"] a[href^="#"]')].map((a) => a.getAttribute('href'))""")
        check(bool(hrefs), "it links out", str(hrefs))
        for h in dict.fromkeys(hrefs):
            pg.click('.pv-tab[data-pv="construction"]')
            pg.wait_for_timeout(200)
            pg.click(f'[data-pv-view="construction"] a[href="{h}"]')
            pg.wait_for_timeout(350)
            got = pg.evaluate("""() => {
              const v = document.querySelector('.pv-view.is-active');
              return v ? v.dataset.pvView : "";
            }""")
            check(got not in ("", "construction"), f"{h} opens the view that owns it", got)

        pg.click('.pv-tab[data-pv="construction"]')
        pg.wait_for_timeout(250)
        code = blocks(pg)
        print("\nQuiet console")
        check(not logs, "nothing logged an error", "; ".join(logs[:4]))
        b.close()

    print("\nThe code it prints")
    labels = [lab for lab, _ in code]
    check(labels.count("evolve.py") == 3, "the library arrives in three blocks", str(labels))
    per_file: dict[str, str] = {}
    for label, src in code:
        per_file[label] = per_file.get(label, "") + "\n\n" + src
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        try:
            lib = run(per_file["evolve.py"], "evolve.py")
        except Exception as e:                                 # noqa: BLE001
            check(False, "evolve.py is valid Python", f"{type(e).__name__}: {e}")
            lib = {}
        if lib:
            check(True, "evolve.py imports and defines cleanly",
                  f"{sum(1 for v in lib.values() if callable(v))} callables")
            lib = check_library(lib, tmp)
        if lib:
            check_axes(lib, per_file)
            check_worked_examples(lib, per_file, tmp)

    print(f"\n{checks - len(fails)}/{checks} checks pass")
    for f in fails:
        print(f"  FAIL {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
