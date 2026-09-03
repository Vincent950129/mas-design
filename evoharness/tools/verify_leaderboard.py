#!/usr/bin/env python3
"""Regression checks for the merged leaderboard.

The leaderboard now ranks the paper's main-results rows and the appendix rows
(Claude Code, the skill-learning ablations) in one field, which only stays
honest if every row keeps its own model and harness. These checks pin the
things that would quietly break that: an appendix row losing its attribution,
a stray backbone label, a skill-learning row acquiring ALE numbers it never
had, or the Results tab drifting away from the paper's tables.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app.js"
HTML = ROOT / "index.html"
CSS = ROOT / "paper.css"

fails: list[str] = []
checks = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global checks
    checks += 1
    if not ok:
        fails.append(f"{label}{': ' + detail if detail else ''}")


def load_results() -> dict:
    """Pull the RESULTS literal out of app.js and evaluate it with node."""
    src = APP.read_text()
    start = src.index("const RESULTS = {")
    end = src.index("\n};", start) + 3
    literal = src[start:end].replace("const RESULTS = ", "", 1).rstrip(";\n ")
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as fh:
        fh.write(f"console.log(JSON.stringify({literal}));")
        path = fh.name
    out = subprocess.run([NODE, path], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


NODE = "node"


def main() -> int:
    app = APP.read_text()
    html = HTML.read_text()
    css = CSS.read_text()

    # -- the file still parses ------------------------------------------- #
    syn = subprocess.run([NODE, "--check", str(APP)], capture_output=True, text=True)
    check(syn.returncode == 0, "app.js parses", syn.stderr.strip()[:200])
    if syn.returncode != 0:
        report()
        return 1

    R = load_results()

    def facet(row: dict, axis: str, key: str) -> str:
        if key == "agency":
            return row.get("agency") or ("mas" if row.get("mas") else R[axis]["agency"])
        return row.get(key) or R[axis][key]

    def rows_of(axis: str) -> list[dict]:
        main = [r for r in R[axis]["rows"] if "sec" not in r]
        return main + R[axis].get("more", [])

    # -- every axis declares its defaults -------------------------------- #
    for axis in ("tools", "skills", "agents"):
        for key in ("llm", "harness", "agency"):
            check(bool(R[axis].get(key)), f"{axis} axis declares {key}")
    check(R["tools"]["agency"] == "sas", "tools axis defaults to single-agent")
    check(R["agents"]["agency"] == "mas", "agents axis defaults to multi-agent",
          "the paper says every row there is a native MAS")

    # -- the appendix rows are in the ranked field ----------------------- #
    for axis in ("skills", "agents"):
        names = [r["name"] for r in rows_of(axis)]
        check(names.count("Claude Code") == 2,
              f"{axis}: both Claude Code rows are ranked", str(names.count("Claude Code")))
    check("Claude Code" not in [r["name"] for r in rows_of("tools")],
          "tools: no Claude Code row", "Table G.1 covers skills and agents only")

    skill = [r for r in rows_of("skills") if r.get("cat") == "skill"]
    check(len(skill) == 9, "skills: 9 skill-learning rows", str(len(skill)))
    check("SkillOpt" in [r["name"] for r in skill], "skills: SkillOpt is present")
    for axis in ("tools", "agents"):
        check(not [r for r in rows_of(axis) if r.get("cat") == "skill"],
              f"{axis}: no skill-learning rows", "Table I.2 is an EOG skills ablation")

    # -- attribution is exactly what the paper says ---------------------- #
    for axis in ("skills", "agents"):
        for r in rows_of(axis):
            if r["name"] == "Claude Code":
                check(facet(r, axis, "llm") == "Sonnet-4.6",
                      f"{axis}: Claude Code is Sonnet-4.6", facet(r, axis, "llm"))
                check(facet(r, axis, "harness") == "Claude Code",
                      f"{axis}: Claude Code runs its own harness", facet(r, axis, "harness"))
    for r in skill:
        want = "GPT-5.5" if r["name"] == "SkillOpt" else "GPT-5"
        check(facet(r, "skills", "llm") == want,
              f"skills: {r['name']} backbone is {want}", facet(r, "skills", "llm"))
        check(facet(r, "skills", "harness") == "Codex",
              f"skills: {r['name']} runs in Codex", facet(r, "skills", "harness"))

    # Only Claude Code and SkillOpt deviate from the controlled backbone.
    off = {r["name"] for axis in R for r in rows_of(axis)
           if facet(r, axis, "llm") != R[axis]["llm"]}
    check(off == {"Claude Code", "SkillOpt"},
          "only Claude Code and SkillOpt change the backbone", str(sorted(off)))

    # MAS attribution: G-Memory rides AutoGen, LegoMem is its own orchestrator.
    fw = {(axis, r["name"]): facet(r, axis, "harness") for axis in R for r in rows_of(axis)}
    check(fw[("tools", "G-Memory")] == "AutoGen",
          "tools: G-Memory runs on AutoGen", fw[("tools", "G-Memory")])
    check(fw[("agents", "G-Memory")] == "AutoGen",
          "agents: G-Memory runs on AutoGen", fw[("agents", "G-Memory")])
    check(fw[("tools", "LegoMem")] == "LegoMem",
          "tools: LegoMem is its own orchestrator", fw[("tools", "LegoMem")])
    check(fw[("tools", "AutoGen")] == "AutoGen", "tools: AutoGen names itself")
    check(fw[("tools", "DeLM")] == "DeLM", "tools: DeLM names itself")
    check(fw[("tools", "Raw Memory")] == R["tools"]["harness"],
          "tools: SAS memory rows inherit the axis host", fw[("tools", "Raw Memory")])

    # -- EOG-only rows stay EOG-only ------------------------------------- #
    for r in skill:
        for key in ("ale", "aleScore", "aleH", "aleTok", "overall"):
            check(r.get(key) is None, f"skills: {r['name']} has no {key}",
                  f"Table I.2 has no ALE arm; found {r.get(key)}")
        check(r.get("eog") is not None and r.get("eogScore") is not None,
              f"skills: {r['name']} reports EOG pass and score")

    # Numbers transcribed from Table I.2, including the commented SkillOpt row.
    want_skill = {
        "Empty skills": (16.9, 2.5, 56.1, 1.4),
        "Zero-shot": (17.6, 1.7, 54.5, 1.3),
        "One-shot": (11.5, 0.6, 41.1, 0.4),
        "Raw trajectories": (20.0, 1.7, 59.3, 0.6),
        "Self feedback": (12.8, 2.2, 42.1, 0.8),
        "Batch self feedback": (16.2, 2.4, 57.3, 2.5),
        "Batch teacher feedback": (22.1, 3.0, 59.7, 0.8),
        "Skill creator": (20.9, 1.5, 60.6, 1.0),
        "SkillOpt": (21.2, 3.1, 61.8, 1.6),
    }
    for r in skill:
        got = (r["eog"], r["eogSd"], r["eogScore"], r["eogScoreSd"])
        check(got == want_skill[r["name"]], f"skills: {r['name']} matches Table I.2",
              f"{got} != {want_skill[r['name']]}")

    # Claude Code, Table G.1.
    want_cc = {
        ("skills", True): (29.3, 13.2, 24.2),
        ("skills", False): (30.2, 13.2, 24.8),
        ("agents", True): (11.0, 16.9, 12.8),
        ("agents", False): (10.6, 15.3, 12.0),
    }
    for axis in ("skills", "agents"):
        for r in rows_of(axis):
            if r["name"] == "Claude Code":
                got = (r["eog"], r["ale"], r["overall"])
                key = (axis, bool(r.get("ref")))
                check(got == want_cc[key], f"{axis}: Claude Code {key[1] and 'control' or 'cumulative'} matches Table G.1",
                      f"{got} != {want_cc[key]}")

    # -- the Results tab keeps reproducing the paper's main tables ------- #
    main_counts = {"tools": 11, "skills": 8, "agents": 8}
    for axis, n in main_counts.items():
        got = len([r for r in R[axis]["rows"] if "sec" not in r])
        check(got == n, f"{axis}: main table still has {n} rows", str(got))
    check(re.search(r"function renderTable\(axis\) \{\s*const rows = RESULTS\[axis\]\.rows;", app)
          is not None, "Results tab reads rows only, not the appendix rows")
    check("RESULTS[axis].more" not in app.split("function renderXfer")[0].split("function renderBars")[1],
          "renderBars leaves the appendix rows out")

    # -- filtering is wired for every facet the user asked for ----------- #
    check('const FACETS = ["llm", "harness", "cat", "agency"]' in app,
          "all four facets are filterable")
    for key in ("llm", "harness", "cat", "agency"):
        check(f'data-lbf="{key}"' in html, f"{key} filter exists in the markup")
    check("data-lb-reset" in html and "data-lb-reset" in app, "reset control is wired")
    check("data-lb-count" in html and "data-lb-count" in app, "match count is wired")
    check(re.search(r"S\.f\[sel\.dataset\.lbf\] = sel\.value", app) is not None,
          "changing a filter updates state")
    check(re.search(r"FACETS\.every\(\(k\) => !S\.f\[k\] \|\| facet\(r, k, axis\) === S\.f\[k\]\)", app)
          is not None, "systems() applies every active filter")
    check("skill: { c:" in app and "Skill learning" in app, "skill learning is a method family")
    check(re.search(r"AGENCY = \{ sas: \"Single-agent\", mas: \"Multi-agent\" \}", app) is not None,
          "agency reads as single/multi-agent")

    # -- the separate blocks are gone ------------------------------------ #
    for gone in ("CLAUDE_CODE", "SKILL_LEARNING", "claudeBlock", "skillChart",
                 "data-lb-skill", 'data-view="skill"'):
        check(gone not in app and gone not in html, f"{gone} is removed")
    check("lb-side" not in css and "lb-drow" not in css and "lb-basel" not in css,
          "CSS for the removed blocks is gone")

    # -- the table shows what it is filtering on ------------------------- #
    check("<th>LLM</th>" in app, "table has an LLM column")
    check("<th>Harness</th>" in app, "table has a Harness column")
    check('<th colspan="4"></th>' in app, "group header spans the four left columns")
    check("min-width: 960px" in css, "table is wide enough for the new columns")
    check("lb-llm" in app and ".lb-llm.is-alt" in css, "a non-default backbone is marked")

    # -- the caveats the merge has to keep ------------------------------- #
    check("GPT-5.5" in html and "Sonnet-4.6" in html,
          "the lead names the backbones that differ")
    check("does not state their task count" in html,
          "provenance admits Table I.2 has no stated task count")
    check(re.search(r"EOG-only ablation with no \$\{ENV\[S\.env\]\} arm", app) is not None,
          "gap chart gives the right reason for a missing skill-learning bar")
    check(re.search(r"could not complete \$\{ENV\[S\.env\]\} within a", app) is not None,
          "gap chart keeps the compute-budget reason for unfinished runs")
    check("crowded" in app and "rotate(-40" in app,
          "gap chart tilts labels once the field is large")
    # A caveat offered for rows the filters removed is as wrong as a missing one.
    check(re.search(r'rows\.some\(\(r\) => facet\(r, "llm", axis\) !== spec\.llm\)', app)
          is not None, "backbone caveat keys off the visible rows, not the whole axis")
    check(re.search(r'rows\.some\(\(r\) => r\.cat === "skill"\)', app) is not None,
          "EOG-only caveat keys off the visible rows, not the whole axis")
    check(re.search(r"const plotted = systems\(axis\)\.filter", app) is not None
          and re.search(r"legend\(Array\.from\(new Set\(plotted\.map", app) is not None,
          "efficiency legend follows the points that exist")

    # -- the skill-learning ablation's cost figures ----------------------- #
    # Table I.2 reports duration and tokens per sweep for every row but SkillOpt.
    # Keyed by the name the page shows, since that is what a reader matches against
    # the paper. The pass rate goes in too: it is what identifies the row, and a
    # transcription that lands the cost on the wrong system would otherwise pass.
    I2 = {
        "Empty skills":           (16.9, 3.5, 74.7),
        "Zero-shot":              (17.6, 4.4, 111.6),
        "One-shot":               (11.5, 2.8, 61.1),
        "Raw trajectories":       (20.0, 4.3, 87.5),
        "Self feedback":          (12.8, 2.8, 57.3),
        "Batch self feedback":    (16.2, 3.2, 74.3),
        "Batch teacher feedback": (22.1, 3.1, 33.8),
        "Skill creator":          (20.9, 3.1, 33.8),
    }
    skill = {r["name"]: r for r in rows_of("skills") if r.get("cat") == "skill"}
    for name, (pass_, hours, toks) in I2.items():
        r = skill.get(name, {})
        check((r.get("eog"), r.get("eogH"), r.get("eogTok")) == (pass_, hours, toks),
              f"{name} keeps its Table I.2 pass rate, hours and tokens",
              f"{r.get('eog')}, {r.get('eogH')}, {r.get('eogTok')}")
    check(set(skill) - set(I2) == {"SkillOpt"},
          "SkillOpt is the only skill row without cost figures", str(set(skill) - set(I2)))
    check("eogH" not in skill.get("SkillOpt", {}) and "eogTok" not in skill.get("SkillOpt", {}),
          "SkillOpt reports no cost rather than a borrowed one")
    # The ablation not reporting cost was once true of the whole family and is now
    # true of one row, so the chart must not explain an absence by the family.
    check("skill-learning ablation reports pass and score only" not in app,
          "the efficiency caption no longer blames the whole family for a missing point")
    check(re.search(r"const noCost = gone\.filter\(\(r\) => n1\(r\[k\.pass\]\) != null\)", app)
          is not None,
          "the efficiency caption separates a missing arm from an unrecorded cost")
    # Every skill row is EOG-only, so ALE must not gain a point from this.
    check(all("ale" not in r and "aleH" not in r and "aleTok" not in r for r in skill.values()),
          "no skill row acquired ALE cost figures")

    # -- the scatter has to stay readable at 18 points -------------------- #
    # Eight more points nearly doubled the skills field, which the old label
    # placement could not seat: names came to rest on other systems' markers.
    check(re.search(r"const many = rows\.length > 12", app) is not None
          and re.search(r"const W = many \? 760 : 500", app) is not None,
          "a fuller field is drawn on a larger canvas, in viewBox units")
    check('.lb-effgrid.is-roomy { grid-template-columns: 1fr; }' in css
          and 'plotted.length > 12 ? " is-roomy"' in app,
          "the larger canvas gets the full column width")
    check(re.search(r"const covered = \(b\) =>", app) is not None
          and re.search(r"tries\.sort\(\(a, b\) => a\.n - b\.n", app) is not None,
          "a label prefers a placement that covers no point")
    # Filtering can leave a chart with one point or none; neither existed before
    # the filters, and both used to render NaN coordinates or bare axes.
    check("if (to - from < step / 2) { from -= step; to += step; }" in app,
          "niceScale gives a lone point an axis to sit on")
    check('<p class="lb-none">' in app and ".lb-none {" in css,
          "an empty chart says so instead of framing bare axes")
    check(app.count("const envBtns = ()") == 1
          and "const envBtns = `" not in app,
          "the environment switch is defined once")

    report()
    return 1 if fails else 0


def report() -> None:
    print(f"{checks - len(fails)}/{checks} checks passed")
    for f in fails:
        print(f"  FAIL  {f}")


if __name__ == "__main__":
    sys.exit(main())
