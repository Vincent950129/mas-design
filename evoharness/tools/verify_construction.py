#!/usr/bin/env python3
"""Checks the construction guide and its exact TB2 and APEX-Agents routes.

Every public block is lifted from the rendered DOM and compared with its private reference
source. The rest guards nested seed, section, and track-step tabs so opening one branch never
changes another. It also pins the Evaluate Your Agent label and position after Leaderboard.

Expects the static page on port 8777 and, by default, the local evaluation service
on port 8077. Set ``EVOLVE_VERIFY_SERVICE`` to test another service instance.
"""
from __future__ import annotations

import json
import hashlib
import os
import pathlib
import random
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "tools/proofs"
BASE = "http://127.0.0.1:8777/evoharness/index.html"
SERVICE = os.environ.get("EVOLVE_VERIFY_SERVICE", "http://127.0.0.1:8077").rstrip("/")


def service_request(path: str) -> urllib.request.Request:
    headers = {"ngrok-skip-browser-warning": "true"}
    eval_key = os.environ.get("EVAL_SERVICE_API_KEY", "").strip()
    if eval_key:
        headers["Authorization"] = f"Bearer {eval_key}"
    return urllib.request.Request(SERVICE + path, headers=headers)

# The tab strip, in order. The label a reader sees and the view key the router uses differ
# for Evaluate Your Agent on purpose; the comment in index.html says why.
TABS = [("overview", "Overview"), ("benchmark", "Benchmark"), ("tasks", "Tasks"),
        ("results", "Results"), ("cases", "Cases"), ("leaderboard", "Leaderboard"),
        ("evaluate", "Evaluate Your Agent"),
        ("construction", "Create Your Benchmark")]
# The detailed route is a hierarchy: seed -> section -> one track's pipeline step.
GROUPS = {
    "seed-benchmarks": ["tb2-seed", "apex-seed"],
    "tb2-sections": ["tb2-download", "tb2-tools", "tb2-skills", "tb2-agents", "tb2-output"],
    "tools-steps": ["tools-annotate", "tools-release", "tools-write"],
    "skills-steps": ["skills-annotate", "skills-release", "skills-write"],
    "agents-steps": ["agents-annotate", "agents-release", "agents-write"],
    "apex-sections": ["apex-download", "apex-tools", "apex-skills", "apex-agents", "apex-output"],
    "apex-tools-steps": ["apex-tools-annotate", "apex-tools-release", "apex-tools-write"],
    "apex-skills-steps": ["apex-skills-annotate", "apex-skills-release", "apex-skills-write"],
    "apex-agents-steps": ["apex-agents-annotate", "apex-agents-release", "apex-agents-write"],
    "evaluate": None,
}
PARENTS = {
    "tb2-sections": [("seed-benchmarks", "tb2-seed")],
    "tools-steps": [("seed-benchmarks", "tb2-seed"), ("tb2-sections", "tb2-tools")],
    "skills-steps": [("seed-benchmarks", "tb2-seed"), ("tb2-sections", "tb2-skills")],
    "agents-steps": [("seed-benchmarks", "tb2-seed"), ("tb2-sections", "tb2-agents")],
    "apex-sections": [("seed-benchmarks", "apex-seed")],
    "apex-tools-steps": [("seed-benchmarks", "apex-seed"), ("apex-sections", "apex-tools")],
    "apex-skills-steps": [("seed-benchmarks", "apex-seed"), ("apex-sections", "apex-skills")],
    "apex-agents-steps": [("seed-benchmarks", "apex-seed"), ("apex-sections", "apex-agents")],
}
SEEDS = {
    "https://github.com/harbor-framework/terminal-bench-2/tree/2fd12b88aafdd04a52c298e3940bcb189f9766d6": "Terminal-Bench 2",
    "https://huggingface.co/datasets/mercor/apex-agents": "APEX-Agents",
}
SKILL_URL = "https://educator-marrow-cultural.ngrok-free.dev/resources/evolve-benchmark/SKILL.md"
CHARTS = {
    "tools": {
        "train": [12, 3, 4, 3, 4], "test": [28, 8, 8, 8, 8],
        "added": [13, 8, 8, 8, 13], "cumulative": [13, 21, 29, 37, 50],
    },
    "skills": {
        "train": [6, 4, 4, 4, 8], "test": [15, 10, 11, 10, 17],
        "added": [8, 5, 2, 3, 8], "cumulative": [8, 13, 15, 18, 26],
    },
    "agents": {
        "train": [6, 8, 4, 3, 5], "test": [14, 11, 11, 16, 8],
        "added": [3, 3, 3, 3, 5], "cumulative": [3, 6, 9, 12, 17],
    },
}
APEX_CHARTS = {
    "operations": {
        "train": [87, 12, 9, 10], "test": [202, 28, 20, 24],
        "added": [5, 4, 3, 10], "cumulative": [5, 9, 12, 22],
    },
    "skills": {
        "train": [31, 30, 23, 16, 19, 22], "test": [72, 70, 53, 37, 45, 52],
        "added": [7, 2, 2, 1, 2, 5], "cumulative": [7, 9, 11, 12, 14, 19],
    },
    "specialists": {
        "train": [66, 38, 14], "test": [146, 93, 35],
        "added": [2, 2, 6], "cumulative": [2, 4, 10],
    },
}

fails: list[str] = []
checks = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global checks
    checks += 1
    print(f"  {'ok  ' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        fails.append(label + (f": {detail}" if detail else ""))


def strips(pg) -> dict:
    """Which panel is open in each of the page's tab strips, keyed by the group that owns
    it -- a group where a view runs more than one strip, and the view itself otherwise."""
    return pg.evaluate("""() => {
      const out = {};
      const mine = (el, s) => el.closest('[data-sv-group], .pv-view') === s;
      document.querySelectorAll('[data-sv-group], .pv-view').forEach((s) => {
        const tabs = [...s.querySelectorAll('.sv-tab')].filter((t) => mine(t, s));
        if (!tabs.length) return;
        out[s.dataset.svGroup || s.dataset.pvView] = {
          tab: tabs.filter((t) => t.classList.contains('is-active')).map((t) => t.dataset.sv),
          panel: [...s.querySelectorAll('.sv-panel.is-active')].filter((p) => mine(p, s))
            .map((p) => p.dataset.svPanel),
        };
      });
      return out;
    }""")


def open_panels(pg) -> list[str]:
    """The panels a reader can actually see in the construction view right now."""
    return pg.evaluate("""() => [...document.querySelectorAll(
      '[data-pv-view="construction"] .sv-panel')].filter((p) => p.offsetParent !== null)
      .map((p) => p.dataset.svPanel)""")


def blocks(pg) -> list[tuple[str, str]]:
    """(file label, source) for every code block in the view, in the order it prints."""
    return [tuple(b) for b in pg.evaluate("""() => [...document.querySelectorAll(
      '[data-pv-view="construction"] .sv-codewrap')].map((w) => [
        w.querySelector('.sv-lang').textContent.replace(/^python\\s*·?\\s*/, '').trim(),
        w.querySelector('.sv-code code').textContent])""")]


def exact_tb2_blocks(pg) -> list[tuple[str, str]]:
    """The exact TB2 shell blocks, lifted only from the rendered DOM."""
    return [tuple(b) for b in pg.evaluate("""() => [...document.querySelectorAll(
      '[data-pv-view="construction"] [data-tb2-executable]')].map((pre) => [
        pre.dataset.tb2Executable, pre.querySelector('code').textContent])""")]


def exact_apex_blocks(pg) -> list[tuple[str, str]]:
    """The exact APEX shell blocks, lifted only from the rendered DOM."""
    return [tuple(b) for b in pg.evaluate("""() => [...document.querySelectorAll(
      '[data-pv-view="construction"] [data-apex-executable]')].map((pre) => [
        pre.dataset.apexExecutable, pre.querySelector('code').textContent])""")]


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


def check_public_tb2_path(exact: list[tuple[str, str]], tmp: pathlib.Path) -> None:
    print("\nWorked example 1 — exact public Terminal-Bench 2 path")
    expected_order = ["setup", "tools", "annotate", "release", "package", "skills",
                      "agents", "terminal"]
    check([name for name, _ in exact] == expected_order,
          "all eight exact blocks render in construction order", str([n for n, _ in exact]))
    joined = "\n".join(src for _, src in exact)
    check("/export/" not in joined and "references/tb2/v1/source" not in joined,
          "the rendered route contains no private path or downloaded Python builder")
    check("git clone --filter=blob:none --no-checkout" in dict(exact)["setup"]
          and "2fd12b88aafdd04a52c298e3940bcb189f9766d6" in dict(exact)["setup"],
          "the download tab fetches the pinned Terminal-Bench 2 seed snapshot")
    check(joined.count("/resources/evolve-benchmark/references/tb2/v1/") == 2,
          "the axis tabs download only the two versioned closed catalogs from the service")
    check("python -m tb_builder all" in dict(exact)["terminal"],
          "the final block runs fetch, inspect, double build, validate and smoke")

    request = service_request(
        "/resources/evolve-benchmark/references/terminal-bench-2.md"
    )
    with urllib.request.urlopen(request) as response:
        reference = response.read().decode()
    reference_blocks = re.findall(r"```bash\n(.*?)\n```", reference, flags=re.S)
    check(reference_blocks == [src.rstrip() for _, src in exact],
          "the coding-agent skill and rendered website carry the same runnable blocks")

    work = tmp / "rendered-tb2"
    env = dict(os.environ, EVOLVE_TB2_SERVICE=SERVICE,
               EVOLVE_TB2_WORKDIR=str(work))
    for name, src in exact:
        if name == "terminal":
            src = src.rsplit('\ncd "$EVOLVE_TB2_WORKDIR/data_dry_run"', 1)[0]
        result = subprocess.run(["bash"], input=src, text=True, cwd=tmp, env=env,
                                capture_output=True)
        check(result.returncode == 0, f"rendered exact block executes: {name}",
              result.stderr[-300:] if result.returncode else "")
        if result.returncode:
            return

    private_root = pathlib.Path(
        "/export/xgen-finance/meta_agent/mas_evovle_enviroment"
    )
    sources = {
        "data_dry_run/tb_builder/__init__.py": private_root / "data_dry_run/tb_builder/__init__.py",
        "data_dry_run/tb_builder/__main__.py": private_root / "data_dry_run/tb_builder/__main__.py",
        "data_dry_run/tb_builder/builder.py": private_root / "data_dry_run/tb_builder/builder.py",
        "data_dry_run/tb_builder/config.py": private_root / "data_dry_run/tb_builder/config.py",
        "data_dry_run/tb_builder/remote_docker.py": private_root / "data_dry_run/tb_builder/remote_docker.py",
        "evolve_tools/builder/frequency_config.py": private_root / "evolve_tools/builder/frequency_config.py",
        "evovle_skills/builder/sequencer.py": private_root / "evovle_skills/builder/sequencer.py",
        "evovle_skills/builder/shared/paths.py": private_root / "evovle_skills/builder/shared/paths.py",
    }
    mismatches = [relative for relative, oracle in sources.items()
                  if (work / relative).read_bytes() != oracle.read_bytes()]
    check(not mismatches, "rendered blocks reconstruct every private-oracle source byte",
          str(mismatches))
    catalog_hashes = {
        "catalog.json": "022cd1dc3dd686da146a2aca5d184901c07726b08eba5294e7d4edd1e33e437a",
        "skills.json": "91deca9269aedb5c00c27cae8bb639112a52bbe56939d61eaefac7d4e98a25ef",
    }
    got = {name: hashlib.sha256((work / "data_dry_run/tb_builder" / name).read_bytes()).hexdigest()
           for name in catalog_hashes}
    check(got == catalog_hashes, "the rendered route installs the exact closed catalogs", str(got))


def check_public_apex_path(exact: list[tuple[str, str]], tmp: pathlib.Path) -> None:
    print("\nWorked example 2 — exact public APEX-Agents path")
    expected_order = ["setup", "tools", "annotate", "release", "package", "skills",
                      "agents", "terminal"]
    check([name for name, _ in exact] == expected_order,
          "all eight APEX blocks render in construction order", str([n for n, _ in exact]))
    joined = "\n".join(src for _, src in exact)
    check("/export/" not in joined and "references/apex/v1/source" not in joined,
          "the APEX route contains no private path or downloaded Python builder")
    setup = dict(exact).get("setup", "")
    check("read -rsp" in setup and "HF_TOKEN" in setup
          and "92c86856cf1b11f9833a8a076b3a45a63afa3929" in setup,
          "the download asks securely for the user's token and pins APEX-Agents")
    check("world archives were not downloaded" in setup,
          "the download explicitly excludes the large world archives")
    check(joined.count("/resources/evolve-benchmark/references/apex/v1/") == 2,
          "only the two closed APEX catalogs come from the construction service")
    check("-m apex_builder all" in dict(exact).get("terminal", ""),
          "the final block runs inspection, double build, validation and preflight")

    request = service_request(
        "/resources/evolve-benchmark/references/apex-agents.md"
    )
    with urllib.request.urlopen(request) as response:
        reference = response.read().decode()
    reference_blocks = re.findall(r"```bash\n(.*?)\n```", reference, flags=re.S)
    check(reference_blocks == [src.rstrip() for _, src in exact],
          "the coding-agent skill and webpage carry identical APEX blocks")

    # Reconstruct the public implementation without downloading the gated seed. The clean
    # source cache is copied only after the rendered blocks have been checked and assembled.
    work = tmp / "rendered-apex"
    work.mkdir()
    env = dict(os.environ, EVOLVE_APEX_SERVICE=SERVICE,
               EVOLVE_APEX_WORKDIR=str(work), EVOLVE_APEX_PYTHON=sys.executable)
    for name, src in exact:
        if name == "setup":
            continue
        if name == "terminal":
            src = src.rsplit('\ncd "$EVOLVE_APEX_WORKDIR/data_dry_run"', 1)[0]
        result = subprocess.run(["bash"], input=src, text=True, cwd=tmp, env=env,
                                capture_output=True)
        check(result.returncode == 0, f"rendered APEX block executes: {name}",
              result.stderr[-300:] if result.returncode else "")
        if result.returncode:
            return

    private_root = pathlib.Path("/export/xgen-finance/meta_agent/mas_evovle_enviroment")
    sources = {
        "data_dry_run/apex_builder/__init__.py": private_root / "data_dry_run/apex_builder/__init__.py",
        "data_dry_run/apex_builder/__main__.py": private_root / "data_dry_run/apex_builder/__main__.py",
        "data_dry_run/apex_builder/builder.py": private_root / "data_dry_run/apex_builder/builder.py",
        "data_dry_run/apex_builder/config.py": private_root / "data_dry_run/apex_builder/config.py",
        "evolve_tools/builder/frequency_config.py": private_root / "evolve_tools/builder/frequency_config.py",
        "evovle_skills/builder/sequencer.py": private_root / "evovle_skills/builder/sequencer.py",
        "evovle_skills/builder/shared/paths.py": private_root / "evovle_skills/builder/shared/paths.py",
    }
    mismatches = [relative for relative, oracle in sources.items()
                  if (work / relative).read_bytes() != oracle.read_bytes()]
    check(not mismatches, "APEX blocks reconstruct every private reference source byte",
          str(mismatches))
    catalog_hashes = {
        "catalog.json": "65a621a15d86a609677a8957482bfd42836bd30f8cc3be749ce787a10d90d4b6",
        "skills.json": "de76f39ff5a32d3fcd48f9e1ff8e1062f2c577451c81fa12903bd06c77a9c714",
    }
    got = {name: hashlib.sha256((work / "data_dry_run/apex_builder" / name).read_bytes()).hexdigest()
           for name in catalog_hashes}
    check(got == catalog_hashes, "the APEX route installs the exact closed catalogs", str(got))

    private_builder = private_root / "data_dry_run/apex_builder"
    cache = work / "data_dry_run/apex_builder/cache"
    shutil.copytree(private_builder / "cache/seed", cache / "seed")
    shutil.copytree(private_builder / "cache/archipelago", cache / "archipelago")
    result = subprocess.run(
        [sys.executable, "-m", "apex_builder", "build"],
        cwd=work / "data_dry_run", env=env, text=True, capture_output=True,
    )
    check(result.returncode == 0, "the reconstructed APEX builder completes a fresh double build",
          result.stderr[-300:] if result.returncode else "")
    if result.returncode:
        return
    latest = json.loads((work / "data_dry_run/apex_builder/latest_candidate.json").read_text())
    check(latest["content_hash"] ==
          "8ef9f9aaf2ea5f53447cb90e5a5716a7a0063d9450c5c488e3ac4f13714e088c",
          "the rendered APEX route reproduces the validated dataset hash",
          latest["content_hash"])
    public_candidate = pathlib.Path(latest["candidate"])
    private_latest = json.loads((private_builder / "latest_candidate.json").read_text())
    private_candidate = pathlib.Path(private_latest["candidate"])
    public_files = {path.relative_to(public_candidate).as_posix(): path
                    for path in public_candidate.rglob("*") if path.is_file()}
    private_files = {path.relative_to(private_candidate).as_posix(): path
                     for path in private_candidate.rglob("*") if path.is_file()}
    byte_mismatches = [relative for relative in sorted(set(public_files) & set(private_files))
                       if public_files[relative].read_bytes() != private_files[relative].read_bytes()]
    check(set(public_files) == set(private_files) and not byte_mismatches,
          "the rendered APEX dataset matches the private baseline file-for-file and byte-for-byte",
          str({"missing": sorted(set(private_files) - set(public_files)),
               "extra": sorted(set(public_files) - set(private_files)),
               "changed": byte_mismatches}))


def check_apex_example(lib: dict, per_file: dict, tmp: pathlib.Path) -> None:
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
    here = pathlib.Path.cwd()
    try:
        os.chdir(ax_root)
        ax = run(per_file["seed_apex_agents.py"], "seed_apex_agents", ns)
    except Exception as e:  # noqa: BLE001
        check(False, "the APEX script runs", f"{type(e).__name__}: {e}")
        return
    finally:
        os.chdir(here)

    read = {t["task_id"]: t for t in ax["apex_tasks"]()}
    check(len(read) == len(rows), "APEX reads the rows the card documents", f"{len(read)} tasks")
    one = ax["apex_capabilities"](read["apex_0"])
    check(one == {"mail", "spreadsheets"}, "APEX capability annotation remains unchanged",
          str(sorted(one)))
    built = ax_root / "data/apex_agents"
    stages = sorted(p.name for p in built.iterdir() if p.is_dir())
    check(len(stages) >= 3 and stages[0] == "v1", "APEX still leaves a staged stream",
          " ".join(stages))


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
        check(set(st) == set(GROUPS), "ten tab strips, each scoped to its own group",
              " ".join(sorted(st)))
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

        # textContent includes the inactive nested panels, whose labels and guidance must
        # remain available even though the reader sees only one branch at a time.
        body = pg.evaluate(
            "() => document.querySelector('[data-pv-view=\"construction\"]').textContent")
        seed_signals = ["tool annotations", "rich explanations", "procedural prompts"]
        check(all(signal in body.lower() for signal in seed_signals),
              "it presents the three axis-construction signals as the easy conversion path",
              str([s for s in seed_signals if s not in body.lower()]))
        construction_sections = [heading.strip().casefold() for heading in pg.locator(
            '[data-pv-view="construction"] h3.sv-h3'
        ).all_inner_texts()]
        expected_sections = ["When the pipeline fits your seed",
                             "Two properties hold by construction", "Detailed build"]
        expected_sections = [section.casefold() for section in expected_sections]
        positions = [construction_sections.index(section) if section in construction_sections else -1
                     for section in expected_sections]
        check(all(position >= 0 for position in positions) and positions == sorted(positions),
              "seed fit, construction properties, then detailed build appear in that order",
              str(construction_sections))
        properties = pg.evaluate("""() => {
          const host = document.querySelector('[data-construction-properties]');
          return host ? [...host.querySelectorAll('.sv-card')].map((card) => ({
            tag: card.querySelector('.sv-tag')?.textContent.trim(),
            heading: card.querySelector('h3')?.textContent.trim(),
            text: card.textContent,
          })) : [];
        }""")
        check([card["tag"] for card in properties] ==
              ["Feasibility", "New-capability pressure"],
              "the two guarantees use the paper's terminology", str(properties))
        check(len(properties) == 2
              and "Cᵢ ⊆ Hₜᵢ" in properties[0]["text"]
              and "Cᵢ ∩ (Hₜᵢ ∖ Hₜᵢ₋₁) ≠ ∅" in properties[1]["text"]
              and "execution-tested" in properties[0]["text"],
              "both formal conditions render, with feasibility scoped precisely",
              str(properties))
        check("Terminal-Bench 2" in body and "APEX-Agents" in body,
              "both seed routes are unmistakable")
        check("The recipe, in four steps" not in body and "seed_apex_agents.py" not in body
              and "application names only guard availability" in body.lower(),
              "stale application-as-tool and rubric-mining guidance is gone")

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
        skill_hits = [a for a in out if a["href"].rstrip("/") == SKILL_URL.rstrip("/")]
        check(bool(skill_hits) and all(a["safe"] for a in skill_hits),
              "the public construction skill is linked safely", SKILL_URL)
        stray = [a["href"] for a in out if not any(
            a["href"].rstrip("/") == u.rstrip("/") for u in (*SEEDS, SKILL_URL))]
        check(not stray, "and nothing else leaves the page from here", str(stray))

        print("\nOne seed, section and track step at a time")
        st = strips(pg)
        firsts = {g: st[g]["panel"] for g, keys in GROUPS.items() if keys}
        check(all(firsts[g] == [keys[0]] for g, keys in GROUPS.items() if keys),
              "each group opens on its first chip, not on all of them", str(firsts))
        check(sorted(open_panels(pg)) == ["tb2-download", "tb2-seed"],
              "the initial view shows only the chosen seed and its download", str(open_panels(pg)))

        for group, keys in GROUPS.items():
            if not keys:
                continue
            for parent_group, parent_key in PARENTS.get(group, []):
                pg.click(
                    f'[data-sv-group="{parent_group}"] .sv-tab[data-sv="{parent_key}"]'
                )
                pg.wait_for_timeout(120)
            for key in keys:
                pg.click(f'[data-sv-group="{group}"] .sv-tab[data-sv="{key}"]')
                pg.wait_for_timeout(200)
                st = strips(pg)
                check(st[group]["panel"] == [key] and st[group]["tab"] == [key],
                      f"{group}/{key}: the chip opens its own panel and only that one",
                      str(st[group]))
                panel = pg.locator(
                    f'[data-sv-group="{group}"] .sv-panel[data-sv-panel="{key}"]'
                )
                check(panel.is_visible() and bool(panel.inner_text().strip()),
                      f"{group}/{key}: the selected panel has visible content",
                      f"chars={len(panel.inner_text())}")
                if group.endswith("-steps"):
                    code_sizes = panel.locator(".sv-code code").evaluate_all(
                        "els => els.map(el => el.textContent.trim().length)"
                    )
                    check(bool(code_sizes) and sum(code_sizes) >= 250,
                          f"{group}/{key}: the step includes substantive corresponding code",
                          str(code_sizes))
                others = {g: st[g]["panel"] for g in st if g != group}
                check(all(len(v) == 1 for v in others.values()),
                      f"{group}/{key}: every other strip keeps exactly one panel", str(others))
            pg.click(f'[data-sv-group="{group}"] .sv-tab[data-sv="{keys[0]}"]')
            pg.wait_for_timeout(150)

        guides = pg.evaluate("""() => ({
          tb2: [...document.querySelectorAll('[data-tb2-guide]')].map((host) => ({
            key: host.dataset.tb2Guide,
            code: host.querySelector('code')?.textContent.length || 0,
          })),
          apex: [...document.querySelectorAll('[data-apex-guide]')].map((host) => ({
            key: host.dataset.apexGuide,
            code: host.querySelector('code')?.textContent.length || 0,
          })),
        })""")
        for seed, items in guides.items():
            check(len(items) == 6 and all(item["code"] >= 250 for item in items),
                  f"{seed}: all six skills/agents step guides render exact builder code",
                  str(items))

        print("\nTB2 expected output is a stage picture, not a checksum table")
        pg.click('[data-sv-group="seed-benchmarks"] .sv-tab[data-sv="tb2-seed"]')
        pg.click('[data-sv-group="tb2-sections"] .sv-tab[data-sv="tb2-output"]')
        pg.wait_for_timeout(180)
        chart_state = pg.evaluate("""() => {
          const panel = document.querySelector('[data-sv-panel="tb2-output"]');
          return {
            text: panel.textContent,
            tables: panel.querySelectorAll('.table-container').length,
            charts: [...panel.querySelectorAll('[data-stage-chart]')].map((node) => ({
              axis: node.dataset.axis,
              train: node.dataset.train.split(',').map(Number),
              test: node.dataset.test.split(',').map(Number),
              added: node.dataset.added.split(',').map(Number),
              cumulative: node.dataset.cumulative.split(',').map(Number),
              svg: node.querySelectorAll('svg[role="img"]').length,
              stages: node.querySelectorAll('.tb2-stage').length,
              curve: node.querySelectorAll('[data-cumulative-curve]').length,
              tooltip: node.querySelectorAll('.tb2-chart-tooltip[role="tooltip"]').length,
              numberSize: parseFloat(getComputedStyle(node.querySelector('.tb2-total')).fontSize),
              label: node.querySelector('svg')?.getAttribute('aria-label') || '',
            })),
          };
        }""")
        chart_data = {chart.pop("axis"): chart for chart in chart_state["charts"]}
        check(set(chart_data) == set(CHARTS),
              "tools, skills, and agents each have a chart", str(sorted(chart_data)))
        for axis, expected in CHARTS.items():
            actual = chart_data.get(axis, {})
            series = {key: actual.get(key) for key in expected}
            check(series == expected, f"{axis}: chart data matches the validated output", str(series))
            check(actual.get("svg") == 1 and actual.get("stages") == 5
                  and actual.get("curve") == 1 and actual.get("tooltip") == 1
                  and actual.get("numberSize", 0) >= 11 and bool(actual.get("label")),
                  f"{axis}: five bars and one accessible cumulative curve render", str(actual))
        check(chart_state["tables"] == 0,
              "the three dense tables have been replaced", str(chart_state["tables"]))
        check("7dd14ca35796ad7a91fdc08a825d53d298aed527cd67497317c78064fbef50a0"
              not in chart_state["text"] and "hash" not in chart_state["text"].lower(),
              "no implementation hash is exposed to the reader")
        tools_h2 = pg.locator('[data-axis="tools"] .tb2-stage[data-stage="H2"]')
        tools_tip = pg.locator('[data-axis="tools"] .tb2-chart-tooltip')
        tools_h2.hover()
        pg.wait_for_timeout(120)
        tip_text = tools_tip.inner_text()
        check(tools_tip.is_visible()
              and all(part in tip_text for part in
                      ("H2", "3 adaptation", "8 test", "11 tasks",
                       "21 tools available", "+8 tools released")),
              "hovering a stage reveals its full task and harness counts", tip_text)
        tools_h2.focus()
        check(tools_tip.is_visible(), "the same detail is available from the keyboard")

        print("\nAPEX expected output supports independent stage counts")
        pg.click('[data-sv-group="seed-benchmarks"] .sv-tab[data-sv="apex-seed"]')
        pg.click('[data-sv-group="apex-sections"] .sv-tab[data-sv="apex-output"]')
        pg.wait_for_timeout(180)
        apex_charts = pg.evaluate("""() => [...document.querySelectorAll(
          '[data-sv-panel="apex-output"] [data-stage-chart]')].map((node) => ({
            axis: node.dataset.axis,
            train: node.dataset.train.split(',').map(Number),
            test: node.dataset.test.split(',').map(Number),
            added: node.dataset.added.split(',').map(Number),
            cumulative: node.dataset.cumulative.split(',').map(Number),
            stages: node.querySelectorAll('.tb2-stage').length,
            tooltip: node.querySelectorAll('.tb2-chart-tooltip[role="tooltip"]').length,
            label: node.querySelector('svg')?.getAttribute('aria-label') || '',
          }))""")
        apex_data = {chart.pop("axis"): chart for chart in apex_charts}
        check(set(apex_data) == set(APEX_CHARTS),
              "operations, skills, and specialists each have an APEX chart",
              str(sorted(apex_data)))
        for axis, expected in APEX_CHARTS.items():
            actual = apex_data.get(axis, {})
            series = {key: actual.get(key) for key in expected}
            check(series == expected, f"APEX {axis}: chart data matches validated output",
                  str(series))
            check(actual.get("stages") == len(expected["train"])
                  and actual.get("tooltip") == 1 and bool(actual.get("label")),
                  f"APEX {axis}: its independent stage count renders accessibly", str(actual))
        apex_h2 = pg.locator('[data-sv-panel="apex-output"] [data-axis="operations"] '
                             '.tb2-stage[data-stage="H2"]')
        apex_tip = pg.locator('[data-sv-panel="apex-output"] [data-axis="operations"] '
                              '.tb2-chart-tooltip')
        apex_h2.hover()
        pg.wait_for_timeout(120)
        tip_text = apex_tip.inner_text()
        check(apex_tip.is_visible()
              and all(part in tip_text for part in
                      ("H2", "12 adaptation", "28 test", "40 tasks",
                       "9 operations available", "+4 operations released")),
              "APEX hover reveals its full task and harness counts", tip_text)

        pg.screenshot(path=str(OUT / "construction.png"), full_page=True)

        print("\nAnd the service strip is still independent of construction")
        pg.click('[data-sv-group="seed-benchmarks"] .sv-tab[data-sv="tb2-seed"]')
        pg.click('[data-sv-group="tb2-sections"] .sv-tab[data-sv="tb2-agents"]')
        pg.wait_for_timeout(200)
        pg.click('.pv-tab[data-pv="evaluate"]')
        pg.wait_for_timeout(300)
        pg.click('[data-pv-view="evaluate"] .sv-tab[data-sv="ports"]')
        pg.wait_for_timeout(220)
        st = strips(pg)
        check(st["evaluate"]["panel"] == ["ports"], "clicking one moves that strip",
              str(st["evaluate"]))
        check(st["tb2-sections"]["panel"] == ["tb2-agents"],
              "and leaves the construction strips where the reader left them",
              str({g: st[g]["panel"] for g in GROUPS if GROUPS[g]}))

        pg.click('.pv-tab[data-pv="construction"]')
        pg.wait_for_timeout(250)
        pg.click('[data-sv-group="seed-benchmarks"] .sv-tab[data-sv="tb2-seed"]')
        pg.click('[data-sv-group="tb2-sections"] .sv-tab[data-sv="tb2-download"]')
        pg.wait_for_timeout(150)
        code = blocks(pg)
        exact = exact_tb2_blocks(pg)
        exact_apex = exact_apex_blocks(pg)
        pg.context.grant_permissions(["clipboard-read", "clipboard-write"],
                                     origin="http://127.0.0.1:8777")
        setup_pre = pg.locator('[data-tb2-executable="setup"]')
        setup_pre.locator("xpath=..").locator(".sv-copy").click()
        copied = pg.evaluate("navigator.clipboard.readText()")
        check(copied == dict(exact)["setup"],
              "the exact-block copy button copies every rendered byte")
        pg.click('[data-sv-group="seed-benchmarks"] .sv-tab[data-sv="apex-seed"]')
        pg.click('[data-sv-group="apex-sections"] .sv-tab[data-sv="apex-download"]')
        apex_setup_pre = pg.locator('[data-apex-executable="setup"]')
        apex_setup_pre.locator("xpath=..").locator(".sv-copy").click()
        apex_copied = pg.evaluate("navigator.clipboard.readText()")
        check(apex_copied == dict(exact_apex)["setup"],
              "the APEX copy button copies every rendered byte")

        mobile = b.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(BASE, wait_until="load")
        mobile.click('.pv-tab[data-pv="construction"]')
        mobile.wait_for_timeout(250)
        mobile_fit = mobile.evaluate("""() => ({
          page: document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
          code: [...document.querySelectorAll('.tb2-exact-code')].every((pre) =>
            pre.clientWidth <= pre.parentElement.clientWidth &&
            getComputedStyle(pre).overflowY === 'auto')
        })""")
        check(mobile_fit["page"] and mobile_fit["code"],
              "the construction page and exact source stay contained on mobile", str(mobile_fit))
        mobile.close()
        print("\nQuiet console")
        check(not logs, "nothing logged an error", "; ".join(logs[:4]))
        b.close()

    print("\nThe code it prints")
    labels = [lab for lab, _ in code]
    installer = next((src for label, src in code
                      if label == "bash · install evolve-benchmark"), "")
    check("/resources/evolve-benchmark/install.sh | bash" in installer
          and len(installer.strip().splitlines()) <= 5,
          "the coding-agent installer stays as compact as the evaluation quickstart")
    check("evolve.py" not in labels and "seed_apex_agents.py" not in labels,
          "no stale generic APEX code remains", str(labels))
    check(len(exact) == 8, "the complete TB2 route is shown once", str([n for n, _ in exact]))
    check(len(exact_apex) == 8, "the complete APEX route is shown once",
          str([n for n, _ in exact_apex]))
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        check_public_tb2_path(exact, tmp)
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        check_public_apex_path(exact_apex, tmp)

    print(f"\n{checks - len(fails)}/{checks} checks pass")
    for f in fails:
        print(f"  FAIL {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
