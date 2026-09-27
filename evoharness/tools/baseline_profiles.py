"""Reviewed configuration evidence for the experiments registered in analysis/arms.py.

Keep recorded values separate from launcher defaults: the latter cannot establish
historical overrides. Paths are relative to the experiment repository, unless
prefixed with external/evolving-mas-benchmark/.
"""

PREFIX = {"tools": "evolve_tools", "skills": "evovle_skills", "agents": "evovle_agents"}
ALE_REPEATS = {"tools": "3, 3, 3, 3, 1", "skills": "3, 3, 3, 3, 3, 1", "agents": "3, 3, 3, 3, 1, 1"}


def profile(arm):
    track, key = arm.track, arm.key
    prefix = PREFIX[track]
    control = arm.role == "baseline"
    claude = key in ("claude", "oracle-claude")
    model = "Sonnet-4.6" if claude else "GPT-5.5" if key in ("oracle-gpt55", "skillopt") else "GPT-5"
    harness = "ReAct (EOG) / Codex (ALE)" if track == "tools" else "Claude Code" if claude else "SkillOpt" if key == "skillopt" else "Codex"
    if key == "react-ale-v":
        harness = "Codex (ALE)"
    rows = [["Solver model", model, "Reported" if claude else "Registry" if key == "skillopt" else "Recorded"]]
    notes = []
    sources = ["analysis/arms.py", f"analysis/cache/cells_{track}.tsv"]
    kind = "control" if control else "cumulative"
    if control:
        description = "Task-specific reference. Each task receives its selected capability subset; no state accumulates across cohorts."
        rows += [["Capability selection", "Task-specific tools" if track == "tools" else "Task-specific skills with oracle tools" if track == "skills" else "Task-specific specialist agents", "Registry / runner"],
                 ["Stage search budget", "No stage-level prompt or harness search in this control", "Experiment design"]]
        notes.append("Each stage point evaluates that cohort only. The benchmark aggregate pools all cohorts; this is not a cumulative adaptation curve.")
        if track == "agents" and key == "oracle":
            description = "Reference control with a per-cohort specialist library on EOG and task-specific specialist families on ALE. No cross-stage adaptation."
            rows[1] = ["Capability selection", "EOG: per-cohort reference specialist library; ALE: task-specific specialist families", "Saved EOG manifests / ALE runner"]
            notes.append("On EOG, tasks with different selected tool sets use the same specialist roster within each cohort.")
    elif key in ("react", "react-ale-v", "codex", "claude"):
        description = "Deployment baseline with the benchmark’s accumulating capability pool. No stage-specific prompt or harness optimization."
        rows += [["Stage search budget", "No stage-level optimization", "Experiment design"],
                 ["Capability pool", "Cumulative through the selected stage", "Registry / runner"]]
    elif key == "memory":
        description = "Codex with native persistent memory. Training rollouts populate a shared memory home that is carried between stages and copied for evaluation."
        rows += [["Adaptation", "Training tasks from versions 1…k; memory carried between stages", "Current runner"],
                 ["Memory training concurrency", "EOG: 1 (forced); ALE: requested concurrency, with parallel sandbox rollouts", "Current runner; historical override unknown"],
                 ["Extraction / consolidation limits", "600 / 900 seconds", "Current defaults"],
                 ["Extraction concurrency", "8", "Current default"],
                 ["Stage search budget", "No GEPA/Meta-Harness search; training and memory processing add work", "Runner"]]
        notes.append("Historical memory-processing overrides and total adaptation tokens/cost are not recoverable from the evaluation snapshot. Held-out evaluation uses a copy of trained memory.")
        sources += [f"{prefix}/src/scripts/run_cumulative_{'skill' if track == 'skills' else 'agents'}.py", "evovle_agents/src/config.py:328", f"{prefix}/src/config.py"]
    elif key in ("raw-memory", "reasoning-bank", "memtoolagent"):
        representation = {"raw-memory": "Raw adaptation trajectories", "reasoning-bank": "Induced reasoning memories", "memtoolagent": "Reflections on adaptation trajectories"}[key]
        description = representation + " are retained across stages and supplied to the solver alongside the accumulating tool pool."
        rows += [["Memory representation", representation, "Registry / saved artifacts"],
                 ["ALE adaptation repetitions", "1 rollout per training task in inspected stage logs", "Recorded sample"],
                 ["Search budget", "No candidate-search loop; adaptation rollouts and memory induction add work", "Runner"]]
        if key in ("raw-memory", "memtoolagent"):
            rows.append(["ALE retrieval limit", "10 most recent memories; 0 means unlimited", "Current launcher default; historical override unknown"])
        else:
            rows.append(["Historical retrieval / induction budget", "Not recorded in the exported evaluation configuration", "Unavailable"])
        notes += ["EOG exports can contain eight evaluation runs. These results use runs 1–3 to match the other systems.",
                  "Codex (ALE, V) is the ALE deployment control for these memory experiments.",
                  "No complete adaptation token/dollar budget is recorded. Evaluation usage is not a measure of memory-building cost."]
        launcher = {"raw-memory": "gpt5_evolve_ale_cumulative_tool_memory.sh", "reasoning-bank": "gpt5_evolve_ale_cumulative_tool_adapt_fwd_reasoning.sh", "memtoolagent": "gpt5_evolve_ale_cumulative_tool_adapt_fwd_reflection.sh"}[key]
        sources += ["external/evolving-mas-benchmark/evolve_tools/src/memory.py", "external/evolving-mas-benchmark/evolve_tools/src/reasoning_induction.py", "external/evolving-mas-benchmark/evolve_tools/src/scripts/frequent_config/" + launcher]
    elif key in ("gepa", "gepa-oracle"):
        description = "Reflective prompt optimization. GEPA edits prompt text and carries the selected prompt forward between stages."
        rows += [["Search budget", "50 metric calls per searched stage", "Recorded search.json"],
                 ["Reflection minibatch", "3 tasks", "Recorded"],
                 ["Search repetitions", "1 trial per task", "Recorded"],
                 ["Reflection model", "GPT-5", "Recorded"],
                 ["Reflection response limit", "32,768 tokens; up to 5 API attempts", "Current configuration"],
                 ["Concurrency / RNG seed", "8 concurrent trials / seed 0", "Current defaults"]]
        notes += ["50 calls is a stopping threshold: initial validation consumes calls, batches can overshoot, and retries add work.",
                  "Library defaults: strict improvement, Pareto selection, round-robin module selection, no merge and no evaluation cache.",
                  "Validation pools cohorts 1…k. Winners carry forward; learning uses the new cohort with a cumulative-data fallback from the seed."]
        sources += [f"{prefix}/src/scripts/run_gepa.sh", f"{prefix}/meta_harness/run_gepa.py", f"{prefix}/meta_harness/gepa_reflection.py", f"{prefix}/meta_harness/splits.py"]
        if key == "gepa-oracle":
            description += " This variant searches with each task’s oracle skills, then evaluates with the full stage library."
            rows.append(["Search / evaluation library", "Per-task oracle / full stage library (CSM 9, HR 10, ITSM 10 skills)", "Recorded / registry"])
            notes.append("Only final-stage held-out evaluations are archived: CSM/HR v3, ITSM v4. Earlier search stages exist, but are not earlier held-out results. No ALE evaluation is registered.")
            sources.append("evovle_skills/jobs/oracle_skills_gepa/<stream>/oracle_skills_gepa_*/v*/search.json")
        else:
            sources.append(arm.root + "/<stream>/run_*/v*/search.json")
    elif key == "meta":
        description = "Code-based adaptation. A GPT-5 proposer edits the Python harness and learned state, carrying the selected program and state between stages."
        rows += [["Search budget", "5 proposer iterations per stage", "Launcher configuration"],
                 ["Candidates", "3 requested per iteration", "Proposer instruction"],
                 ["EOG search repetitions", "3 trials per task", "Recorded"],
                 ["ALE candidate validation repetitions", "; ".join(f"v{i}: {n.strip()} trials/task" for i, n in enumerate(ALE_REPEATS[track].split(","), 1)), "Recorded; repetitions per candidate, separate from held-out evaluation"],
                 ["Proposer", "GPT-5; 2,400 seconds per iteration", "Configuration"],
                 ["Inner learning", "Offline; 1 epoch; batch size 1", "Configuration"],
                 ["Concurrency", "8 concurrent trials", "Current default"]]
        notes += ["Each candidate is evaluated on the full validation set. Five iterations do not guarantee 15 evaluated candidates; archived logs include incomplete stages.",
                  "The current ALE launcher defaults to one search trial/task throughout. The recorded schedule above differs.",
                  "Validation pools cohorts 1…k, with winners carried forward. Learning uses the new cohort with cumulative-data fallback from the seed."]
        sources += [f"{prefix}/src/scripts/run_meta_harness.sh", f"{prefix}/meta_harness/config.yaml", f"{prefix}/meta_harness/skills/meta-harness/SKILL.md", f"{prefix}/meta_harness/logs/run_*/v*/<stream>/<candidate>/gpt-5/val.json"]
    elif key == "skillopt":
        description = "SkillOpt with GPT-5.5, evaluated against the cumulative EOG skill library. This is a different backbone from the GPT-5 systems."
        rows += [["Optimization budget", "Not recorded with this archived evaluation export", "Unavailable"],
                 ["Solver limits / concurrency", "Not established by these artifacts", "Unavailable"]]
        notes += ["EOG only. Recorded trial durations are unavailable; missing time must not be interpreted as zero cost."]
    else:
        raise ValueError(f"Configuration evidence required for {track}/{key}")

    if key in ("gepa", "gepa-oracle", "meta"):
        notes += ["GEPA metric calls and Meta-Harness proposer iterations are different budget units. These searches were not demonstrated to be compute-matched.",
                  "No complete search token/dollar cap or historical concurrency override was established. Three evaluation runs are not three independent searches."]
    if track == "agents" and key in ("oracle", "codex"):
        rows[0] = ["Solver model", "EOG: gpt-5-codex in inspected saved config.toml; ALE: GPT-5", "Recorded"]
        model = "GPT-5 / GPT-5-Codex"
    if key == "oracle-gpt55":
        notes.append("Model-only swap of the GPT-5 task-specific skills control, run August 26. The registry records the same ACP transport, local backend, concurrency and timeout. EOG only.")
    if track == "tools":
        if key != "react-ale-v":
            basis = "Iteration default / saved model configuration" if key in ("gepa", "meta") else "Reference defaults; historical overrides unverified"
            rows.append(["EOG solver limits", "ReAct: 50 iterations; max_tokens 16,384; temperature 0.1", basis])
        rows.append(["ALE solver limit", "7,200 seconds per task", "Saved experiment configuration / runner"])
        sources += ["evolve_tools/src/runner.py", "evolve_tools/src/ale_eval.py", "reference/EnterpriseOps-Gym/conf/llm/gpt-5.json (model settings only)"]
    elif key != "skillopt":
        if claude:
            rows.append(["EOG solver limit", "900 seconds per task", "Export notes / timeout records"])
            rows.append(["ALE solver limit / launch overrides", "Not specified in the exported run configuration", "Unavailable"])
            notes.append("Some EOG usage comes from a dedicated one-run telemetry pass; accuracy still uses the original three runs. Missing usage means cost totals may be lower bounds.")
            sources.append("yang_li/results_final/README.md")
        else:
            rows.append(["EOG solver limit", "900 seconds per task shared across up to 4 episodes", "Current default; historical overrides not fully established"])
            if key not in ("oracle-gpt55", "gepa-oracle"):
                rows.append(["ALE solver limit", "7,200 seconds per task", "Saved experiment configuration / runner"])
            sources += [f"{prefix}/src/config.py", f"{prefix}/src/runner.py"]
            if track == "agents":
                rows.append(["Base delegation limits", "12 threads; maximum depth 1", "Saved base configuration / current default"])
                notes.append("These are base Codex delegation limits; an evolved harness may change orchestration behavior.")
    if track == "tools" and key == "react":
        notes.append("The separate Codex (ALE, V) experiment provides the ALE deployment control for the tool-memory baselines.")
    if track == "tools" and key == "react-ale-v":
        notes.append("ALE deployment control for the tool-memory baselines. Results are reported separately from the other ReAct / Codex deployment run.")
    rows += [["Held-out evaluation", "Runs 1, 2 and 3 per recorded cell", "Archived snapshot"],
             ["Complete total compute budget", "Not established; evaluation metrics exclude adaptation/search work", "Unavailable"]]
    return dict(name="Meta-Harness" if key == "meta" else arm.name, track=track, arm=key,
                model=model, harness=harness, author=arm.author, kind=kind,
                description=description, settings=rows, notes=notes, sources=sources)
