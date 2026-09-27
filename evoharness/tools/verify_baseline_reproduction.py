#!/usr/bin/env python3
"""Verify the archived EvoHarness result package offline (Python 3.10+, stdlib).

Usage: python verify_results.py [directory_containing_data.json]

Checks every included trial against run/cell/stage/benchmark summaries and the
SHA-256 manifest. This reproduces archived arithmetic, not a new benchmark run or
an audit of the original model traces. Missing trials are not zero-filled.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

EXPECTED = {
    "tools": {"oracle", "react", "meta-harness", "gepa", "react-ale-v", "raw-memory", "reasoning-bank", "memtoolagent"},
    "skills": {"oracle", "oracle-gpt55", "oracle-claude", "claude", "codex", "memory", "meta-harness", "gepa", "gepa-oracle", "skillopt"},
    "agents": {"oracle", "oracle-claude", "codex", "claude", "memory", "meta-harness", "gepa"},
}
EXPECTED_KEYS = {f"{track}-{arm}" for track, arms in EXPECTED.items() for arm in arms}
TOLERANCE = 1e-5  # Published percentage values have six decimal places.


class VerificationError(Exception):
    pass


def require(condition, message):
    # Deliberately not `assert`: validation remains active with python -O.
    if not condition:
        raise VerificationError(message)


def near(actual, expected, label, tolerance=TOLERANCE):
    try:
        actual, expected = float(actual), float(expected)
    except (TypeError, ValueError) as exc:
        raise VerificationError(f"{label}: nonnumeric value") from exc
    require(math.isfinite(actual) and math.isfinite(expected), f"{label}: nonfinite value")
    require(abs(actual - expected) <= tolerance,
            f"{label}: got {actual}, reconstructed {expected}")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    require(bool(rows), f"Empty CSV: {path.name}")
    return rows


def verify_hashes(root):
    manifest = read_json(root / "checksums.json")
    require(isinstance(manifest, dict) and bool(manifest), "Invalid checksums.json")
    mandatory = {"data.json", "README.md", "provenance.json", "historical_ale_exclusions.json", "verify_results.py"}
    mandatory |= {key + suffix for key in EXPECTED_KEYS for suffix in
                  ("-configuration.json", "-trials.csv", "-runs.csv", "-matrix.csv", "-stages.csv")}
    require(mandatory <= set(manifest), f"Manifest omits required artifacts: {sorted(mandatory - set(manifest))}")
    for name, expected in manifest.items():
        require(isinstance(name, str) and not Path(name).is_absolute() and ".." not in Path(name).parts,
                f"Unsafe manifest path: {name}")
        path = root / name
        require(path.is_file(), f"Missing artifact: {name}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        require(actual == expected, f"SHA-256 mismatch: {name}")
    return len(manifest)


def summarize(rows):
    by_run = defaultdict(list)
    for row in rows:
        by_run[row["run"]].append(row)
    require(bool(by_run), "Cannot summarize empty trial selection")
    ids = sorted(by_run)
    scores = [100 * math.fsum(row["score"] for row in by_run[run]) / len(by_run[run]) for run in ids]
    passes = [100 * sum(row["success"] for row in by_run[run]) / len(by_run[run]) for run in ids]
    return dict(score=statistics.mean(scores), scoreSd=statistics.pstdev(scores),
                **{"pass": statistics.mean(passes), "passSd": statistics.pstdev(passes)},
                runs=len(ids), runIds=ids, tasks=[len(by_run[run]) for run in ids])


def verify_summary(record, expected, label, csv_format=False):
    mapping = {"score": "score_pct", "scoreSd": "score_std_pct", "pass": "pass_pct", "passSd": "pass_std_pct"}
    for metric, column in mapping.items():
        near(record[column if csv_format else metric], expected[metric], f"{label}/{metric}")
    if csv_format:
        require(int(record["num_runs"]) == expected["runs"], f"{label}: number of runs")
        counts = ";".join(f"{run}:{count}" for run, count in zip(expected["runIds"], expected["tasks"]))
        require(record["tasks_per_run"] == counts, f"{label}: tasks_per_run")
    else:
        for field in ("runs", "runIds", "tasks"):
            require(record[field] == expected[field], f"{label}: {field}")


def index_unique(rows, fields, label):
    out = {}
    for row in rows:
        key = tuple(int(row[field]) if field in ("adapt_stage", "eval_cohort", "run") else row[field] for field in fields)
        require(key not in out, f"{label}: duplicate key {key}")
        out[key] = row
    return out


def verify_system(root, key, system, excluded):
    track, arm = system["track"], system["arm"]
    rows = read_csv(root / f"{key}-trials.csv")
    seen_ids = set()
    for i, row in enumerate(rows, 2):
        label = f"{key}-trials.csv:{i}"
        require(row["track"] == track and row["arm"] == arm, f"{label}: wrong experiment")
        require(row["benchmark"] in ("eog", "ale"), f"{label}: unknown benchmark")
        require((row["benchmark"] == "ale") == (row["stream"] == "ale"), f"{label}: benchmark/stream mismatch")
        for field in ("adapt_stage", "eval_cohort", "run", "success"):
            row[field] = int(row[field])
        row["score"] = float(row["score"])
        require(math.isfinite(row["score"]) and 0 <= row["score"] <= 1, f"{label}: invalid score")
        require(row["success"] in (0, 1), f"{label}: invalid success")
        require(row["run"] in (1, 2, 3), f"{label}: run must be 1, 2 or 3")
        require(row["adapt_stage"] >= 1 and row["eval_cohort"] >= 1, f"{label}: invalid stage/cohort")
        require(bool(row["task_id"]), f"{label}: missing task ID")
        identity = tuple(row[field] for field in ("benchmark", "stream", "adapt_stage", "eval_cohort", "run", "task_id"))
        require(identity not in seen_ids, f"{label}: duplicate task/run identity {identity}")
        seen_ids.add(identity)
        require(row["benchmark"] != "ale" or row["task_id"] not in excluded,
                f"{label}: includes historically excluded ALE task {row['task_id']}")

    config = read_json(root / f"{key}-configuration.json")
    require(config["track"] == track and config["arm"] == arm, f"{key}: configuration identity")
    runs = read_csv(root / f"{key}-runs.csv")
    stages = read_csv(root / f"{key}-stages.csv")
    matrices = read_csv(root / f"{key}-matrix.csv")
    for filename, records in (("runs", runs), ("stages", stages), ("matrix", matrices)):
        require(all(r["track"] == track and r["arm"] == arm for r in records), f"{key}-{filename}: experiment identity")
    runs_by_key = index_unique(runs, ("benchmark", "stream", "adapt_stage", "eval_cohort", "run"), f"{key}-runs")
    matrix_by_key = index_unique(matrices, ("benchmark", "stream", "adapt_stage", "eval_cohort"), f"{key}-matrix")
    stage_by_key = index_unique(stages, ("benchmark", "stream", "adapt_stage"), f"{key}-stages")
    trials_by_run, trials_by_cell = defaultdict(list), defaultdict(list)
    for row in rows:
        cell_key = tuple(row[field] for field in ("benchmark", "stream", "adapt_stage", "eval_cohort"))
        trials_by_cell[cell_key].append(row)
        trials_by_run[(*cell_key, row["run"])].append(row)
    require(set(runs_by_key) == set(trials_by_run), f"{key}: run inventory differs from trials")
    require(set(matrix_by_key) == set(trials_by_cell), f"{key}: matrix inventory differs from trials")
    for cell_key, trials in trials_by_run.items():
        record = runs_by_key[cell_key]
        label = f"{key}/run/{cell_key}"
        require(int(record["n_tasks"]) == len(trials), f"{label}: denominator")
        require(int(record["passes"]) == sum(r["success"] for r in trials), f"{label}: passes")
        near(record["score_sum"], math.fsum(r["score"] for r in trials), label + "/score_sum", 1e-9)
        summary = summarize(trials)
        near(record["score_pct"], summary["score"], label + "/score_pct")
        near(record["pass_pct"], summary["pass"], label + "/pass_pct")

    control = system["kind"] == "control"
    require(not control or all(r["adapt_stage"] == r["eval_cohort"] for r in rows), f"{key}: control has nondiagonal cells")
    actual_streams = {r["stream"] for r in rows}
    require(set(system["streams"]) == actual_streams, f"{key}: stream inventory")
    final_rows, expected_stages = [], set()
    missing_task_sets = 0
    for stream_name, stream in system["streams"].items():
        stream_rows = [r for r in rows if r["stream"] == stream_name]
        benchmark = stream_rows[0]["benchmark"]
        require(stream["benchmark"] == benchmark, f"{key}/{stream_name}: benchmark")
        ks, js = sorted({r["adapt_stage"] for r in stream_rows}), sorted({r["eval_cohort"] for r in stream_rows})
        require(stream["adaptStages"] == ks and stream["cohorts"] == js, f"{key}/{stream_name}: stages/cohorts")
        data_cells = {(c["stage"], c["cohort"]): c for c in stream["cells"]}
        require(len(data_cells) == len(stream["cells"]), f"{key}/{stream_name}: duplicate JSON matrix cells")
        require(set(data_cells) == {(r["adapt_stage"], r["eval_cohort"]) for r in stream_rows}, f"{key}/{stream_name}: JSON matrix inventory")
        for (k, j), record in data_cells.items():
            label = f"{key}/{stream_name}/matrix/{k}/{j}"
            trials = trials_by_cell[benchmark, stream_name, k, j]
            expected = summarize(trials)
            verify_summary(record, expected, label)
            csv_record = matrix_by_key[benchmark, stream_name, k, j]
            verify_summary(csv_record, expected, label + "/csv", True)
            regime = "cohort_control" if control else "forward" if j > k else "diagonal" if j == k else "retention"
            require(record["regime"] == csv_record["regime"] == regime, label + ": regime")
            run_sets = [{r["task_id"] for r in trials if r["run"] == run} for run in expected["runIds"]]
            missing_task_sets += len({frozenset(s) for s in run_sets}) > 1
        data_stages = {s["stage"]: s for s in stream["stages"]}
        require(len(data_stages) == len(stream["stages"]), f"{key}/{stream_name}: duplicate JSON stages")
        seen_stage_keys = set()
        for k in ks:
            trials = [r for r in stream_rows if r["adapt_stage"] == k and (r["eval_cohort"] == k if control else r["eval_cohort"] <= k)]
            if not trials:
                continue
            stage_key = benchmark, stream_name, k
            expected_stages.add(stage_key)
            seen_stage_keys.add(k)
            require(k in data_stages and stage_key in stage_by_key, f"{key}/{stream_name}/stage/{k}: missing summary")
            expected, cohorts = summarize(trials), sorted({r["eval_cohort"] for r in trials})
            verify_summary(data_stages[k], expected, f"{key}/{stream_name}/stage/{k}")
            verify_summary(stage_by_key[stage_key], expected, f"{key}/{stream_name}/stage/{k}/csv", True)
            require(data_stages[k]["cohorts"] == cohorts, f"{key}/{stream_name}/stage/{k}: cohort inventory")
            require(stage_by_key[stage_key]["evaluated_cohorts"] == ";".join(map(str, cohorts)), f"{key}/{stream_name}/stage/{k}: CSV cohort inventory")
            require(stage_by_key[stage_key]["scope"] == ("cohort_only" if control else "seen_cohorts"), f"{key}/{stream_name}/stage/{k}: scope")
        require(set(data_stages) == seen_stage_keys, f"{key}/{stream_name}: JSON stage inventory")
        final_rows.extend([r for r in stream_rows if r["eval_cohort"] == r["adapt_stage"]] if control else
                          [r for r in stream_rows if r["adapt_stage"] == max(ks) and r["eval_cohort"] <= r["adapt_stage"]])
    require(set(stage_by_key) == expected_stages, f"{key}: CSV stage inventory")
    require(set(system["aggregates"]) == {r["benchmark"] for r in final_rows}, f"{key}: headline benchmark inventory")
    for benchmark, record in system["aggregates"].items():
        verify_summary(record, summarize([r for r in final_rows if r["benchmark"] == benchmark]), f"{key}/{benchmark}/headline")
    require(system["evaluationTrials"] == len(rows), f"{key}: evaluationTrials")
    require(system["evaluationCells"] == len(matrices), f"{key}: evaluationCells")
    return dict(trials=len(rows), cell_runs=len(runs), matrix_cells=len(matrices), stage_scores=len(stages),
                aggregates=len(system["aggregates"]), cells_with_different_run_task_sets=missing_task_sets)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    root = args.directory.resolve()
    hashed = verify_hashes(root)
    data = read_json(root / "data.json")
    require(set(data["systems"]) == EXPECTED_KEYS, "Archive must contain all 25 registered snapshot experiments")
    historical = read_json(root / "historical_ale_exclusions.json")
    excluded = set(historical["excluded"])
    counts = Counter()
    for key, system in data["systems"].items():
        counts.update(verify_system(root, key, system, excluded))
    provenance = read_json(root / "provenance.json")
    for field in ("cell_runs", "matrix_cells", "stage_scores"):
        require(provenance["counts"][field] == counts[field], f"provenance counts/{field}")
    require(provenance["counts"]["cached_trials"] == counts["trials"], "provenance cached_trials")
    require(provenance["counts"]["systems"] == 25, "provenance systems")
    print(f"PASS: {hashed} SHA-256 hashes; 25 experiments; {counts['trials']:,} included trials; "
          f"{counts['cell_runs']:,} cell/runs; {counts['matrix_cells']:,} cells; "
          f"{counts['stage_scores']:,} stages; {counts['aggregates']} benchmark summaries.")
    print(f"Preserved {counts['cells_with_different_run_task_sets']} cells with unequal task sets across runs; "
          "no missing records were filled. Historical ALE exclusions verified.")
    print("This verifies the supplied cached outcomes and aggregation only; it does not rerun models or verify original traces.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (VerificationError, OSError, KeyError, TypeError, ValueError, csv.Error) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
