#!/usr/bin/env python3
"""Export all arms.py experiments from existing caches; no benchmark runs.

python tools/build_baseline_details.py /path/to/mas_evovle_enviroment
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import subprocess
import sys
import zipfile
from baseline_profiles import profile

ROOT = Path(__file__).resolve().parent.parent
STREAMS = {"calendar": "Calendar", "csm": "CSM", "drive": "Drive", "email": "Email",
           "hr": "HR", "hybrid": "Hybrid", "itsm": "ITSM", "teams": "Teams", "ale": "Agents’ Last Exam"}
FILES = {"tools": "trials_tools_eog.jsonl", "skills": "trials_skills.jsonl", "agents": "trials_agents.jsonl"}


def portable(path, repo):
    text = str(path)
    if text.startswith(str(repo) + "/"):
        return text[len(str(repo)) + 1:]
    if "/evolving-mas-benchmark/" in text:
        return "external/evolving-mas-benchmark/" + text.split("/evolving-mas-benchmark/", 1)[1]
    if Path(text).is_absolute():
        raise ValueError(f"Unrecognized external source: {text}")
    return text


def source_info(path, label):
    return dict(file=label, modified_utc=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def write_csv(path, rows):
    assert rows, path
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path, lines):
    text = "\n".join(line.rstrip() for line in "\n".join(lines).splitlines())
    path.write_text(text.rstrip() + "\n")


def summarize(records):
    """Micro-average inside a run; equally weight the run means."""
    runs = defaultdict(list)
    for r in records:
        runs[r["run"]].append(r)
    scores, passes, counts = [], [], []
    for run, rr in sorted(runs.items()):
        n = sum(r["n"] for r in rr)
        counts.append(n)
        scores.append(100 * sum(r["score_sum"] for r in rr) / n)
        passes.append(100 * sum(r["passes"] for r in rr) / n)
    return {"score": round(statistics.mean(scores), 6), "scoreSd": round(statistics.pstdev(scores), 6),
            "pass": round(statistics.mean(passes), 6), "passSd": round(statistics.pstdev(passes), 6),
            "runs": len(runs), "runIds": sorted(runs), "tasks": counts}


def csv_metric(r):
    return dict(score_pct=r["score"], score_std_pct=r["scoreSd"], pass_pct=r["pass"],
                pass_std_pct=r["passSd"], num_runs=r["runs"],
                tasks_per_run=";".join(f"{i}:{n}" for i, n in zip(r["runIds"], r["tasks"])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment_repo", type=Path)
    repo = parser.parse_args().experiment_repo.resolve()
    spec = importlib.util.spec_from_file_location("evoharness_arms", repo / "analysis/arms.py")
    registry = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = registry
    spec.loader.exec_module(registry)
    arms = registry.ARMS
    dest = ROOT / "static/baselines"
    dest.mkdir(parents=True, exist_ok=True)
    sources = [source_info(repo / "analysis/arms.py", "analysis/arms.py")]
    recipes_path = Path(__file__).with_name("reproduction_recipes.json")
    recipes = json.loads(recipes_path.read_text())
    search_evidence_path = Path(__file__).with_name("search_stage_evidence.json")
    search_evidence = json.loads(search_evidence_path.read_text())
    search_checks = verify_search_artifacts(repo, search_evidence)
    expected_keys = {f"{a.track}-{'meta-harness' if a.key == 'meta' else a.key}" for a in arms}
    if set(recipes) != expected_keys:
        raise ValueError("Reproduction recipes must cover exactly the registered experiments")
    data = {"schema": 3, "snapshot": "August 2026", "registry": "analysis/arms.py", "systems": {}}
    all_rows = {}
    all_trials = {}
    cached_trials = 0
    for track, filename in FILES.items():
        trial_path = repo / "analysis/cache" / filename
        cell_path = repo / "analysis/cache" / f"cells_{track}.tsv"
        sources += [source_info(p, str(p.relative_to(repo))) for p in (trial_path, cell_path)]
        valid = {a.key for a in arms if a.track == track}
        def arm_key(key):
            return "react" if track == "tools" and key == "frontier" else key
        raw = defaultdict(lambda: dict(n=0, score_sum=0., passes=0, tokens=0., secs=0., priced=0, timed=0))
        public_trials = []
        with trial_path.open() as f:
            for line in f:
                r = json.loads(line)
                arm = arm_key(r["arm"])
                if arm not in valid or r["run"] not in (1, 2, 3):
                    continue
                k = r["j"] if r["k"] is None else r["k"]
                key = arm, r["bench"], r["domain"], k, r["j"], r["run"]
                v = raw[key]
                v["n"] += 1
                v["score_sum"] += r["score"]
                v["passes"] += r["success"]
                v["tokens"] += r.get("tokens") or 0
                v["secs"] += r.get("secs") or 0
                v["priced"] += (r.get("tokens") or 0) > 0
                v["timed"] += (r.get("secs") or 0) > 0
                cached_trials += 1
                public_trials.append(dict(track=track, arm=arm, benchmark=r["bench"], stream=r["domain"],
                                          adapt_stage=k, eval_cohort=r["j"], run=r["run"], task_id=r["task"],
                                          score=r["score"], success=r["success"],
                                          recorded_tokens=r.get("tokens") or 0, recorded_seconds=r.get("secs") or 0))
        rows = []
        with cell_path.open() as f:
            for c in csv.DictReader(f, delimiter="\t"):
                arm, run = arm_key(c["arm"]), int(c["run"])
                if arm not in valid or run not in (1, 2, 3):
                    continue
                k, j = int(c["k"] or c["j"]), int(c["j"])
                key = arm, c["bench"], c["domain"], k, j, run
                r = raw.pop(key)
                if r["n"] != int(c["n"]) or r["passes"] != int(c["passes"]) or abs(r["score_sum"] - float(c["score_sum"])) >= 1e-5:
                    raise ValueError(f"Cached trial/cell mismatch: {track} {key}")
                rows.append(dict(arm=arm, benchmark=c["bench"], stream=c["domain"], k=k, j=j, run=run, **r))
        if raw:
            raise ValueError(f"{track}: trials without matching cells: {list(raw)[:3]}")
        all_rows[track] = rows
        all_trials[track] = public_trials

    stage_count = cell_count = run_count = 0
    configurations = {}
    for arm in arms:
        p = profile(arm)
        # Preserve existing GEPA/Meta-Harness download URLs.
        key = f"{arm.track}-{'meta-harness' if arm.key == 'meta' else arm.key}"
        p["reproduction"] = recipes[key]
        p["reproduction"]["result_reconstruction"] = "Included per-task scores and success flags reproduce all archived aggregates offline."
        if key in search_evidence:
            p["searchBudget"] = [dict(domain=s["stream"], version=s["stage"], n_train=s.get("train_tasks"),
                                       n_val=s.get("validation_tasks"), trials_per_task=s.get("trials_per_task"),
                                       searched=s.get("searched", True), max_metric_calls=s.get("metric_call_threshold"),
                                       configured_iterations=s.get("configured_proposer_iterations"),
                                       retained_candidate_trials=s.get("retained_validation_trials"),
                                       retained_adapter_statistics=s.get("retained_adapter_statistics", {}))
                                 for s in search_evidence[key]["stages"]]
        rows = [r for r in all_rows[arm.track] if r["arm"] == arm.key]
        assert rows, (key, "no archived evaluations")
        p["sourceRoots"] = {d.split("/")[-1]: portable(path, repo) for d, path in zip(arm.domains, arm.dirs(repo))}
        p["sources"] = [portable(s, repo) for s in p["sources"]]
        configurations[key] = p
        result = dict(p, streams={}, aggregates={})
        stages_csv, cells_csv, runs_csv, final_rows = [], [], [], []
        control = arm.role == "baseline"
        for domain in STREAMS:
            rr = [r for r in rows if r["stream"] == domain]
            if not rr:
                continue
            ks, js = sorted({r["k"] for r in rr}), sorted({r["j"] for r in rr})
            stream = dict(label=STREAMS[domain], benchmark=rr[0]["benchmark"], stages=[], cells=[], adaptStages=ks, cohorts=js)
            base = dict(track=arm.track, arm=arm.key, method=p["name"], benchmark=rr[0]["benchmark"], stream=domain)
            for k in ks:
                seen = [r for r in rr if r["k"] == k and (r["j"] == k if control else r["j"] <= k)]
                if seen:
                    stat = dict(stage=k, cohorts=sorted({r["j"] for r in seen}), **summarize(seen))
                    stream["stages"].append(stat)
                    stages_csv.append(dict(**base, adapt_stage=k, scope="cohort_only" if control else "seen_cohorts",
                                           evaluated_cohorts=";".join(map(str, stat["cohorts"])), **csv_metric(stat)))
                for j in js:
                    cell = [r for r in rr if r["k"] == k and r["j"] == j]
                    if not cell:
                        continue
                    regime = "cohort_control" if control else "forward" if j > k else "diagonal" if j == k else "retention"
                    stat = dict(stage=k, cohort=j, regime=regime, **summarize(cell))
                    stream["cells"].append(stat)
                    cells_csv.append(dict(**base, adapt_stage=k, eval_cohort=j, regime=regime, **csv_metric(stat)))
            result["streams"][domain] = stream
            final_rows += [r for r in rr if r["j"] == r["k"]] if control else [r for r in rr if r["k"] == max(ks) and r["j"] <= r["k"]]
            for r in sorted(rr, key=lambda v: (v["k"], v["j"], v["run"])):
                runs_csv.append(dict(**base, adapt_stage=r["k"], eval_cohort=r["j"], run=r["run"], n_tasks=r["n"],
                                     score_sum=r["score_sum"], passes=r["passes"],
                                     score_pct=round(100 * r["score_sum"] / r["n"], 6), pass_pct=round(100 * r["passes"] / r["n"], 6),
                                     recorded_tokens=int(r["tokens"]), trials_with_tokens=r["priced"],
                                     recorded_seconds=round(r["secs"], 3), trials_with_seconds=r["timed"]))
        for benchmark in ("eog", "ale"):
            rr = [r for r in final_rows if r["benchmark"] == benchmark]
            if rr:
                result["aggregates"][benchmark] = summarize(rr)
        result["evaluationTrials"], result["evaluationCells"] = sum(r["n"] for r in rows), len(cells_csv)
        p["coverage"] = {domain: dict(benchmark=s["benchmark"], recorded_stages=s["adaptStages"],
                                     evaluation_cohorts=s["cohorts"], summary_scope="cohort_only" if control else "seen_cohorts")
                         for domain, s in result["streams"].items()}
        result["coverage"] = p["coverage"]
        data["systems"][key] = result
        for suffix, csv_rows in (("stages", stages_csv), ("matrix", cells_csv), ("runs", runs_csv)):
            write_csv(dest / f"{key}-{suffix}.csv", csv_rows)
        (dest / f"{key}-configuration.json").write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n")
        trials = [r for r in all_trials[arm.track] if r["arm"] == arm.key]
        trials.sort(key=lambda r: (r["benchmark"], r["stream"], r["adapt_stage"], r["eval_cohort"], r["run"], r["task_id"]))
        write_csv(dest / f"{key}-trials.csv", trials)
        stage_count += len(stages_csv)
        cell_count += len(cells_csv)
        run_count += len(runs_csv)

    historical = repo / "analysis/ale_excluded_tasks_iclr.json"
    sources.append(source_info(historical, str(historical.relative_to(repo))))
    (dest / "historical_ale_exclusions.json").write_bytes(historical.read_bytes())
    provenance = dict(snapshot=data["snapshot"], registry="analysis/arms.py", sources=sources,
                      exported_utc=datetime.now(timezone.utc).isoformat(),
                      counts=dict(systems=len(arms), matrix_cells=cell_count, stage_scores=stage_count, cell_runs=run_count, cached_trials=cached_trials),
                      validation="Every exported per-run task count, success count and score sum checked against cached trials and cached cells. The included offline checker independently reconstructs cells, stages and benchmark aggregates from exported task records. This is not a rerun of original trajectories.",
                      aggregation="Task-weighted within run; equal-weight mean and population SD across runs 1–3. Controls pool cohort-only results; cumulative benchmark aggregates use each stream’s final recorded stage. Forward cells are excluded from stage summaries.",
                      limitations="August snapshot, not a fresh evaluation. Missing records are not zero-filled. Usage can be incomplete or from a separate telemetry run; it excludes adaptation/search. Current exclusion filters are not reapplied.",
                      profile_source=source_info(Path(__file__).with_name("baseline_profiles.py"), "tools/baseline_profiles.py"),
                      recipe_source=source_info(recipes_path, "tools/reproduction_recipes.json"),
                      search_evidence_source=source_info(search_evidence_path, "tools/search_stage_evidence.json"),
                      search_artifact_validation=search_checks,
                      current_source_fingerprints=current_fingerprints(repo, configurations),
                      exports={f"{key}-{suffix}.csv": hashlib.sha256((dest / f"{key}-{suffix}.csv").read_bytes()).hexdigest()
                               for key in data["systems"] for suffix in ("stages", "matrix", "runs", "trials")})
    (dest / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    (dest / "data.js").write_text("/* Generated by tools/build_baseline_details.py. */\nconst LB_BASELINE_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")
    (dest / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    write_readme(dest, data, configurations)
    write_reproduction_guide(dest, data)
    (dest / "search-stage-evidence.json").write_bytes(search_evidence_path.read_bytes())
    verifier = Path(__file__).with_name("verify_baseline_reproduction.py")
    (dest / "verify_results.py").write_bytes(verifier.read_bytes())
    # Explicit inventory: never publish unrelated files or a stale artifact via glob.
    names = ["data.json", "data.js", "README.md", "REPRODUCE.md", "provenance.json", "historical_ale_exclusions.json", "verify_results.py", "search-stage-evidence.json"]
    names += [f"{key}-{suffix}" for key in data["systems"] for suffix in
              ("stages.csv", "matrix.csv", "runs.csv", "trials.csv", "configuration.json")]
    checksums = {name: hashlib.sha256((dest / name).read_bytes()).hexdigest() for name in sorted(names)}
    (dest / "checksums.json").write_text(json.dumps(checksums, indent=2) + "\n")
    subprocess.run([sys.executable, str(dest / "verify_results.py"), str(dest)], check=True)
    with zipfile.ZipFile(dest / "reproducibility-kit.zip", "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(names + ["checksums.json"]):
            entry = zipfile.ZipInfo("evoharness-baselines/" + name, (2026, 9, 27, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, (dest / name).read_bytes())
    print(f"Exported {len(arms)} experiments, {stage_count} stages, {cell_count} cells, {run_count} cell/runs; crosschecked {cached_trials} cached trials.")


def write_readme(dest, data, configurations):
    lines = ["# Registered baseline experiments", "", "Every entry in `analysis/arms.py`, using the existing August 2026 analysis snapshot. No new benchmark runs were performed.", "",
             "Click a system name in the leaderboard for its configuration and results. Additional archived variants are linked inside the corresponding system details. Configuration JSONs distinguish saved values, current defaults and unavailable launch settings.", "",
             "**Reproduce the numbers offline:** download [reproducibility-kit.zip](reproducibility-kit.zip), extract it, and run `python3 verify_results.py` inside `evoharness-baselines/`. Python 3.10+; standard library only; no API key, network, experiment checkout or model calls required. [Full instructions and experiment rerun requirements](REPRODUCE.md).", "",
             "Rebuild from the experiment checkout: `python tools/build_baseline_details.py /path/to/mas_evovle_enviroment`. The exporter imports the registry, crosschecks trial and cell caches, and preserves their historical task filtering.", "",
             "## Results and coverage", "", "| Track | Registry arm | System | EOG Score / Pass (%) | ALE Score / Pass (%) |", "|---|---|---|---:|---:|"]
    for key, r in data["systems"].items():
        def value(b):
            m = r["aggregates"].get(b)
            return f"{m['score']:.1f} / {m['pass']:.1f}" if m else "Not evaluated"
        lines.append(f"| {r['track']} | {r['arm']} | [{r['name']}]({key}-configuration.json) | {value('eog')} | {value('ale')} |")
    lines += ["", "Score is partial credit; Pass is strict task success. Task-weighted within each run, then averaged over runs 1–3. SD is population SD of run means, not a confidence interval or independent-search variance.", "",
              "For cumulative experiments, `*-stages.csv` pools recorded cohorts j ≤ k at each stage; `*-matrix.csv` preserves all R[k,j] cells including forward evaluations. Task-specific controls show each cohort separately. Benchmark aggregates pool all control cohorts or each cumulative stream’s final recorded row. Missing cells are never filled or copied.", "",
              "`*-trials.csv` is the exact counted task/run manifest with score and success flag, including failures. `*-runs.csv` includes exact score sums, success counts, denominators and recorded usage. No prompts or trajectories are needed for the offline reconstruction. Zero usage can mean missing telemetry. SkillOpt duration is unrecorded. Some Claude usage comes from a separate telemetry pass. These are evaluation costs, not training/search budgets.", "",
              "Known headline differences: tools/oracle cache has 455 EOG tasks versus 454 on the website; tools/react uses the local ALE run while the website matches react-ale-v; agents/memory ALE is 16.6 Score / 3.7 Pass here versus 15.4 / 3.4 on the website. Evaluation exports retain their recorded values; the leaderboard retains the paper’s reported ranking.", "",
              "Historical ALE counts are 63 for tools/agents and 68 for skills. The current exclusion manifest changed September 16; this export preserves cached denominators. The historical manifest is included for provenance and is not reapplied as a new filter.", "",
              "Source paths are relative to the experiment repository; `external/evolving-mas-benchmark/` denotes a separate checkout. Each configuration JSON locates all stream roots. No credentials, prompts or private absolute paths are copied.", "",
              "## Configurations and budgets", ""]
    for key, p in configurations.items():
        lines += [f"### {p['track']} / {p['name']} (`{p['arm']}`)", "", p["description"], "", "| Setting | Value | Evidence |", "|---|---|---|"]
        lines += [f"| {a} | {b} | {c} |" for a, b, c in p["settings"]]
        lines += [""] + ["- " + n for n in p["notes"]] + ["", "Sources: " + "; ".join(f"`{s}`" for s in p["sources"]), ""]
    write_markdown(dest / "README.md", lines)


def current_fingerprints(repo, configurations):
    """Hashes identify the inspected code, never assert an August runtime pin."""
    paths = {"analysis/arms.py", "analysis/main_results_table.py", "analysis/evolution_probe.py", "install.md"}
    for p in configurations.values():
        for name in p["sources"] + p["reproduction"].get("evidence", []):
            name = name.split(" (", 1)[0].split(":", 1)[0]
            if not any(c in name for c in "*<>") and not name.startswith("external/"):
                paths.add(name)
    for folder in ("reference/gepa", "reference/EnterpriseOps-Gym", "reference/agents-last-exam"):
        for filename in ("pyproject.toml", "uv.lock"):
            paths.add(f"{folder}/{filename}")
    return dict(basis="Current checkout inspected at export time, not a historical source/environment lock. Hashes do not provide the source files themselves.",
                files=[source_info(repo / name, name) for name in sorted(paths) if (repo / name).is_file()])


def verify_search_artifacts(repo, evidence):
    """Validate every exported search-artifact fingerprint against the checkout."""
    sources = {}
    stages = 0
    for experiment in evidence.values():
        for stage in experiment["stages"]:
            stages += 1
            fingerprints = list(stage["state_checkpoints"].values()) + stage["candidate_module_fingerprints"]
            if stage.get("source_fingerprint"):
                fingerprints.append(dict(path=stage["source"], **stage["source_fingerprint"]))
            for v in stage.get("validation_evidence", []):
                if v.get("source_fingerprint"):
                    fingerprints.append(dict(path=v["source"], **v["source_fingerprint"]))
            for entry in fingerprints:
                if not entry.get("sha256"):
                    continue
                path = entry["path"]
                if Path(path).is_absolute() or ".." in Path(path).parts:
                    raise ValueError("Search artifact path must be repository-relative")
                if path in sources and sources[path] != entry["sha256"]:
                    raise ValueError(f"Conflicting artifact fingerprints: {path}")
                sources[path] = entry["sha256"]
    for path, digest in sources.items():
        if hashlib.sha256((repo / path).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Search artifact changed since audit: {path}")
    return dict(stages=stages, unique_files=len(sources),
                scope="State checkpoints, candidate modules and recorded search/validation evidence with supplied hashes. Files are identified but not bundled for executable replay.")


def write_reproduction_guide(dest, data):
    lines = ["# Reproducing the baseline results", "",
             "## 1. Reconstruct the archived numbers (complete, offline)", "",
             "Download `reproducibility-kit.zip` from the leaderboard, extract it, and run:", "", "```sh", "cd evoharness-baselines", "python3 verify_results.py", "```", "",
             "Requires Python 3.10 or newer and its standard library. This operation uses no API, network, benchmark runtime, credentials, or source checkout. It verifies SHA-256 checksums, task/run identities, filtering, exact run numerators, all 1,346 matrix cells, 518 stage summaries and 46 benchmark aggregates for all 25 registered experiments. A nonzero exit means a missing artifact or inconsistency.", "",
             "The ZIP contains a lossless export of each cached task’s score/success flag, the exact task IDs retained in each cell/run, configuration and rerun notes, all result CSVs, data.json, provenance, historical exclusions and the checker. Individual scores in the source cache have six-decimal precision; exact sums here mean sums of those cached values, not full-precision original outcomes. Original prompts, environments, trajectories and trained harness checkpoints are not in the kit.", "",
             "`search-stage-evidence.json` provides 150 search-stage records for GEPA/Meta-Harness and oracle-skills GEPA: recorded train/validation counts, repetition schedules, requested budgets, retained work, available validation task IDs, checkpoint locations and hashes. The exporter verifies every supplied artifact hash against the source checkout. Multiple task counts can reflect different retained candidates or fallback training sets; they are not independent run counts. All 37 tools Meta-Harness lineage entries require the explicit recorded_path → path remapping documented there, in a copied lineage tree before archived reevaluation.", "",
             "### Metric definitions and denominators", "",
             "For each run r, Score = 100 × sum(task score)/number of recorded tasks and Pass = 100 × sum(recorded binary success)/number of recorded tasks. The displayed value is the equally weighted mean of runs 1, 2, 3; SD = sqrt(mean((run value − mean)²)), with population denominator 3. Pass uses the recorded success flag, not an invented threshold on rounded Score.", "",
             "For R[k,j], k is the available harness stage and j the evaluated cohort. A cumulative stage summary pools recorded tasks from j ≤ k within each run. Forward cells j > k are shown separately. A task-specific control evaluates only cohort j with its selected capabilities; its stage points do not accumulate cohorts. Benchmark headlines pool each cumulative stream’s final recorded stage, or all cohort-only control cells. No averaging across EOG and ALE is performed here.", "",
             "Failures with recorded zero scores remain in the denominator. Missing records are not invented or zero-filled; unequal counts are retained. No September filters are applied to these August caches. The per-task CSVs, rather than a union of task names or the exclusion file alone, define the exact cohort/run membership. A fresh ALE run also needs the historical Linux-supported task selection (`reference/agents-last-exam/selected_tasks/docker_support.txt`) as well as the environment-failure exclusions and cohort/split manifests. Some EOG source sweeps have eight runs; only runs 1–3 are included here.", "",
             "Known coverage differences: tools/meta-harness Hybrid R[1,1] has 15/24/24 tasks; agents/meta-harness ALE R[5,6] has 7/8/7 tasks (a forward cell). Tools/oracle counts the additional EOG task `task_20251205_154853_044_d4a463c3_fce76046`, yielding 455 rather than 454 tasks. Skills/gepa-oracle has final-stage results only: CSM/HR v3, ITSM v4. Earlier search stages are not earlier held-out measurements.", "",
             "Three published-row differences remain explicit: tools/oracle EOG; tools/react ALE (the website headline matches react-ale-v); agents/memory ALE. The archive does not silently alter the paper’s ranking.", "",
             "### What the checker establishes", "",
             "It establishes that the downloadable task outcomes reproduce the published archive and their checksums. The exporter also checked those outcomes against the repository’s cached cell tables. It does not independently replay the original trajectories, confirm the task verifiers by execution, or prove that source/runtime versions match August.", "",
             "## 2. Rerun the experiments (additional artifacts required)", "",
             "A full historical rerun cannot currently be guaranteed for every arm. The recipe for each arm below records source-supported entrypoints and explicit settings, and lists missing artifacts. Commands are templates from the inspected current source; they are not recovered historical shell histories and have not been executed as new benchmark runs. An LLM rerun can vary even with the same setup.", "",
             "Obtain the experiment source/data checkout and the separate external checkout where named. Source locations in configuration JSONs are repository-relative; they are not public download URLs. This website kit does not bundle the benchmark runtimes, EOG databases, ALE task environments or trained harness checkpoints. Configure your own model/service credentials privately. Use fresh output roots or isolated checkouts, never the archived result directories.", "",
             "Before comparing methods, freeze task IDs and train/validation/test split, per-stage capability pools, solver and proposer model snapshots, candidate-search budget, validation repeats, evaluation repeats, timeout/retry/concurrency policy, initial and inherited state, and source/dependency/container versions. Unknown historical values must remain unknown; a current default is not evidence that the August run used it. Current source hashes are in provenance.json, labeled as current inspection evidence.", "",
             "GEPA’s metric-call limit and Meta-Harness’s proposer iterations are different units. Neither establishes equal compute. Report adaptation/search episodes, proposer/reflection tokens, retries and evaluation spend separately. CSV usage is evaluation telemetry only and can be incomplete; it is not a complete training/search budget.", "",
             "## Per-experiment rerun recipes", ""]
    for key, result in data["systems"].items():
        r = result["reproduction"]
        lines += [f"### {key} — {result['name']}", "", f"Historical rerun status: **{r['status']}**.", ""]
        lines += ["Prerequisites:", ""] + ["- " + x for x in r.get("prerequisites", [])] + [""]
        for step in r.get("steps", []):
            lines += ["**" + step["title"] + "**", ""]
            if step.get("command"):
                lines += ["```sh", step["command"], "```", ""]
            if step.get("notes"):
                lines += [step["notes"], ""]
        lines += ["Missing information / conditions:", ""] + ["- " + x for x in r.get("missing", [])] + [""]
        if r.get("evidence"):
            lines += ["Evidence: " + "; ".join(f"`{s}`" for s in r["evidence"]), ""]
    write_markdown(dest / "REPRODUCE.md", lines)


if __name__ == "__main__":
    main()
