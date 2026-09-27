#!/usr/bin/env python3
"""Verify archive aggregation, registry identity, all detail panels and downloads."""
from __future__ import annotations
import csv
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import threading
import zipfile
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tools/proofs/baseline_details"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def expected_arm(axis, row):
    name = row["name"]
    if name in ("GEPA", "Meta-Harness", "Codex memory", "SkillOpt"):
        return {"GEPA": "gepa", "Meta-Harness": "meta-harness", "Codex memory": "memory", "SkillOpt": "skillopt"}[name]
    if name in ("Codex", "Claude Code"):
        return ("oracle" if row["cat"] == "ref" else "codex") if name == "Codex" else ("oracle-claude" if row["cat"] == "ref" else "claude")
    if axis == "tools":
        if name == "ReAct / Codex":
            return "oracle" if row["cat"] == "ref" else "react"
        return {"Raw Memory": "raw-memory", "Reasoning Bank": "reasoning-bank", "MemToolAgent": "memtoolagent"}.get(name)


def open_experiment_from_ranking(page, axis, key, result, rows):
    """Reach each archive through a system name, then an inline variant if needed."""
    parents = {
        "tools-react-ale-v": "tools-react",
        "skills-oracle-gpt55": "skills-oracle",
        "skills-gepa-oracle": "skills-gepa",
    }
    parent = parents.get(key, key)
    index, row = next((i, r) for i, r in enumerate(rows) if f"{axis}-{expected_arm(axis, r)}" == parent)
    trigger = page.locator(f'[data-lb-rank] [data-lb-system="{index}"]')
    trigger.focus()
    page.keyboard.press("Enter")
    expect(page.locator("#lb-system-title")).to_have_text(row["name"])
    if key in parents:
        page.locator(f'[data-lbd-experiment="{key}"]').click()
        expect(page.locator("#lb-system-title")).to_have_text(result["name"])
    return trigger


def assert_public_details(page, axis):
    expect(page.locator(".lbd-eyebrow")).to_have_text("Evolving " + axis)
    expect(page.locator(".lbd-headlines")).to_have_attribute("aria-label", "Evaluation results")
    expect(page.locator(".lbd-headlines > div > span")).to_have_text(["EOG", "ALE"])
    assert page.locator("[data-lbd-mismatch]").count() == 0
    content = page.locator(".lbd-body").inner_text()
    for removed in (
        "Archived Score and Pass agree", "Archived and published results differ",
        "Additional archived run.", "Registry:", "Archived evaluation coverage",
        "· archived result", "· published result", "No evaluation registered",
    ):
        assert removed not in content, removed


def assert_metrics(expected, rows):
    runs = sorted({r["run"] for r in rows})
    assert len(runs) == expected["runs"]
    assert [sum(int(r["n_tasks"]) for r in rows if r["run"] == run) for run in runs] == expected["tasks"]
    for metric in ("score", "pass"):
        means = []
        for run in runs:
            rr = [r for r in rows if r["run"] == run]
            n = sum(int(r["n_tasks"]) for r in rr)
            means.append(sum(float(r[metric + "_pct"]) * int(r["n_tasks"]) for r in rr) / n)
        assert abs(statistics.mean(means) - expected[metric]) < 0.00001
        assert abs(statistics.pstdev(means) - expected[metric + "Sd"]) < 0.00001


def verify_data(data):
    assert len(data["systems"]) == 25
    assert {a: sum(r["track"] == a for r in data["systems"].values()) for a in ("tools", "skills", "agents")} == {"tools": 8, "skills": 10, "agents": 7}
    assert "/export/" not in json.dumps(data)
    counts = dict(stages=0, cells=0, aggregates=0)
    for key, result in data["systems"].items():
        with (ROOT / f"static/baselines/{key}-runs.csv").open() as f:
            rows = list(csv.DictReader(f))
        final = []
        for stream, values in result["streams"].items():
            rr = [r for r in rows if r["stream"] == stream]
            for cell in values["cells"]:
                assert_metrics(cell, [r for r in rr if int(r["adapt_stage"]) == cell["stage"] and int(r["eval_cohort"]) == cell["cohort"]])
                counts["cells"] += 1
            for stage in values["stages"]:
                assert_metrics(stage, [r for r in rr if int(r["adapt_stage"]) == stage["stage"] and int(r["eval_cohort"]) in stage["cohorts"]])
                counts["stages"] += 1
            if result["kind"] == "control":
                final += [r for r in rr if r["adapt_stage"] == r["eval_cohort"]]
            else:
                final += [r for r in rr if int(r["adapt_stage"]) == max(values["adaptStages"]) and int(r["eval_cohort"]) <= int(r["adapt_stage"])]
        for bench, expected in result["aggregates"].items():
            assert_metrics(expected, [r for r in final if r["benchmark"] == bench])
            counts["aggregates"] += 1
    assert counts == {"stages": 518, "cells": 1346, "aggregates": 46}, counts
    oracle = data["systems"]["skills-gepa-oracle"]
    assert {d: v["adaptStages"] for d, v in oracle["streams"].items()} == {"csm": [3], "hr": [3], "itsm": [4]}
    assert oracle["streams"]["csm"]["cohorts"] == [1, 2, 3]
    assert data["systems"]["tools-oracle"]["aggregates"]["eog"]["tasks"] == [455] * 3
    return counts


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}"
    OUT.mkdir(parents=True, exist_ok=True)
    checked = 0
    checked_experiments = set()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(url) else route.abort())
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url + "/index.html", wait_until="networkidle")
            page.click('[data-pv="leaderboard"]')
            published, data = page.evaluate("RESULTS"), page.evaluate("LB_BASELINE_DATA")
            counts = verify_data(data)
            for axis in ("tools", "skills", "agents"):
                page.click(f'[data-lb-axis] [data-axis="{axis}"]')
                assert page.locator(".lbd-catalog, [data-lbd-catalog], [data-lbd-catalog-open]").count() == 0
                buttons = page.locator("[data-lb-rank] [data-lb-system]")
                all_rows = [r for r in published[axis]["rows"] if "sec" not in r] + published[axis].get("more", [])
                assert buttons.count() == len(all_rows)
                for button in buttons.all():
                    row = all_rows[int(button.get_attribute("data-lb-system"))]
                    arm = expected_arm(axis, row)
                    button.click()
                    expect(page.locator("#lb-system-title")).to_have_text(row["name"])
                    assert_public_details(page, axis)
                    assert page.locator('.lbd-provenance, .lbd-reproduction, [data-lbd-jump="reproduction"]').count() == 0
                    if arm:
                        result = data["systems"][f"{axis}-{arm}"]
                        assert page.locator("[data-lbd-results]").count() == 1
                        if result["kind"] == "control":
                            expect(page.locator(".lbd-table caption")).to_contain_text("Cohorts are not accumulated")
                    else:
                        expect(page.locator(".lbd-body")).to_contain_text("Detailed configuration and stage-level results are not available for this system.")
                        assert page.locator("[data-lbd-results]").count() == 0
                    page.keyboard.press("Escape")
                    expect(button).to_be_focused()
                    checked += 1
                entries = {k: r for k, r in data["systems"].items() if r["track"] == axis}
                for key, result in entries.items():
                    trigger = open_experiment_from_ranking(page, axis, key, result, all_rows)
                    expect(page.locator("[data-lbd-close]")).to_be_focused()
                    assert_public_details(page, axis)
                    assert page.locator('.lbd-provenance, .lbd-reproduction, [data-lbd-jump="reproduction"]').count() == 0
                    expect(page.locator(".lbd-settings")).to_contain_text(result["settings"][0][1])
                    expect(page.locator(".lbd-settings dt").last).to_have_text("Evaluation coverage")
                    for index, benchmark in enumerate(("eog", "ale")):
                        summary = page.locator(".lbd-headlines > div").nth(index)
                        if benchmark in result["aggregates"]:
                            aggregate = result["aggregates"][benchmark]
                            expect(summary.locator("strong")).to_have_text(f"{aggregate['pass']:.1f}% Pass")
                            expect(summary.locator("p").first).to_have_text(f"{aggregate['score']:.1f}% Score ± {aggregate['scoreSd']:.1f}")
                        else:
                            expect(summary).to_contain_text("No results available")
                    page.click('[data-lbd-jump="configuration"]')
                    expect(page.locator('[data-lbd-part="configuration"] h3')).to_be_focused()
                    recorded_search = result["reproduction"].get("protocol", {}).get("search_stages", [])
                    assert page.locator(".lbd-search-budget tbody tr").count() == len(recorded_search)
                    page.click('[data-lbd-jump="results"]')
                    expect(page.locator('[data-lbd-part="results"] h3')).to_be_focused()
                    for stream, values in result["streams"].items():
                        page.select_option('[data-lbd-control="stream"]', stream)
                        page.select_option('[data-lbd-control="view"]', "stages")
                        page.select_option('[data-lbd-control="metric"]', "score")
                        assert page.locator("[data-lbd-results] .lbd-table tbody tr").count() == len(values["stages"])
                        expect(page.locator(".lbd-result-title")).to_contain_text(values["label"])
                        expect(page.locator("[data-lbd-results] .lbd-table tbody tr").last).to_contain_text(f"{values['stages'][-1]['score']:.1f}")
                        page.select_option('[data-lbd-control="metric"]', "pass")
                        expect(page.locator("[data-lbd-results] .lbd-table tbody tr").last).to_contain_text(f"{values['stages'][-1]['pass']:.1f}")
                        page.select_option('[data-lbd-control="view"]', "matrix")
                        assert page.locator(".lbd-matrix tbody tr").count() == len(values["adaptStages"])
                        assert page.locator(".lbd-matrix thead th").count() == 1 + len(values["cohorts"])
                        assert page.locator(".lbd-matrix td small").count() == len(values["cells"])
                        assert page.locator(".lbd-matrix td.is-forward").count() == sum(c["cohort"] > c["stage"] for c in values["cells"])
                        if key == "tools-meta-harness" and stream == "hybrid":
                            expect(page.locator("[data-lbd-results]")).to_contain_text("15 / 24 / 24")
                        if key == "agents-meta-harness" and stream == "ale":
                            expect(page.locator("[data-lbd-results]")).to_contain_text("7 / 8 / 7")
                        checked += 1
                    for link in page.locator(".lbd-downloads a").all():
                        href = link.get_attribute("href")
                        response = page.request.get(url + "/" + href)
                        assert response.status == 200
                        if href.endswith(".csv"):
                            records = list(csv.DictReader(response.text().splitlines()))
                            assert records and {r["track"] for r in records} == {axis}
                            assert {r["arm"] for r in records} == {result["arm"]}
                        else:
                            assert response.json()["arm"] == result["arm"]
                    with page.expect_download() as info:
                        page.get_by_role("link", name="Stage summary CSV ↓").click()
                    assert info.value.suggested_filename == f"{key}-stages.csv"
                    page.keyboard.press("Escape")
                    expect(trigger).to_be_focused()
                    checked_experiments.add(key)
            assert checked_experiments == set(data["systems"])
            # Verify the retained offline artifact independently, from a fresh
            # directory with Python isolated from the experiment checkout.
            kit_response = page.request.get(url + "/static/baselines/reproducibility-kit.zip")
            assert kit_response.status == 200
            with tempfile.TemporaryDirectory(prefix="evoharness-repro-") as temp:
                kit = Path(temp) / "kit.zip"
                kit.write_bytes(kit_response.body())
                with zipfile.ZipFile(kit) as z:
                    z.extractall(temp)
                packaged = Path(temp) / "evoharness-baselines"
                subprocess.run([sys.executable, "-I", "verify_results.py"], cwd=packaged, check=True)
            page.click('[data-lb-axis] [data-axis="tools"]')
            page.select_option('[data-lbf="cat"]', "prompt")
            page.click('th[data-sort="eogScore"]')
            page.locator("[data-lb-system]").click()
            page.keyboard.press("Escape")
            expect(page.locator('[data-lbf="cat"]')).to_have_value("prompt")
            assert page.locator("[data-lb-system]").count() == 1
            page.click("[data-lb-reset]")
            tool_rows = [r for r in published["tools"]["rows"] if "sec" not in r] + published["tools"].get("more", [])
            open_experiment_from_ranking(page, "tools", "tools-memtoolagent", data["systems"]["tools-memtoolagent"], tool_rows)
            page.locator("#lb-system-dialog").screenshot(path=str(OUT / "desktop-memtoolagent.png"))
            page.select_option('[data-lbd-control="stream"]', "ale")
            page.select_option('[data-lbd-control="view"]', "matrix")
            for width in (390, 768):
                page.set_viewport_size({"width": width, "height": 844})
                assert page.evaluate("document.querySelector('.lbd-body').scrollWidth <= document.querySelector('.lbd-body').clientWidth")
                page.locator(".lbd-controls").scroll_into_view_if_needed()
                page.locator("#lb-system-dialog").screenshot(path=str(OUT / f"matrix-{width}.png"))
                page.click('[data-lbd-jump="configuration"]')
                expect(page.locator('[data-lbd-part="configuration"] h3')).to_be_focused()
                assert page.evaluate("document.querySelector('.lbd-body').scrollWidth <= document.querySelector('.lbd-body').clientWidth")
                page.locator("#lb-system-dialog").screenshot(path=str(OUT / f"configuration-{width}.png"))
            page.keyboard.press("Escape")
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            assert not errors, errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print(f"Verified all 25 experiments; {checked} row/stream interactions; {counts}; 125 per-system downloads and the extracted offline kit; public-facing labels; keyboard and mobile layouts.")


if __name__ == "__main__":
    main()
