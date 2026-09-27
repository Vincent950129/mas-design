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
    recorded = "Recorded experiment setting"
    default = "Implementation default; original run setting unknown"
    reported = "Reported experiment setting"
    unknown = "Not reported"
    design = "Experiment design"
    rows = [["Task-solving model", model, reported if claude or key == "skillopt" else recorded]]
    notes = []
    sources = ["analysis/arms.py", f"analysis/cache/cells_{track}.tsv"]
    kind = "control" if control else "cumulative"
    if control:
        description = "Reference system given the capabilities selected for each task. It does not learn or retain experience between stages."
        rows += [["Capabilities supplied to each task", "The task’s designated tools" if track == "tools" else "The task’s designated skills and tools" if track == "skills" else "The task’s designated specialist agents", reported],
                 ["Optimization between stages", "None; no prompt or agent-program search", design]]
        notes.append("Each stage result covers that stage’s held-out tasks only. The overall benchmark result combines tasks from all stages. No adaptation takes place between these evaluations.")
        if track == "agents" and key == "oracle":
            description = "Reference system given the stage’s specialist library on EOG and the task’s designated specialist groups on ALE. It does not learn between stages."
            rows[1] = ["Specialist agents supplied", "EOG: the reference specialist library for that stage. ALE: the specialist groups designated for each task.", "EOG: recorded experiment setting; ALE: implementation behavior"]
            notes.append("On EOG, tasks from the same stage receive the same specialist library even when their designated tools differ.")
    elif key in ("react", "react-ale-v", "codex", "claude"):
        description = "Deployment baseline that receives the capabilities introduced up to the current stage. Its prompt and agent program are not optimized between stages."
        rows += [["Optimization between stages", "None", design],
                 ["Available capabilities", "All capabilities introduced through the selected stage", reported]]
    elif key == "memory":
        description = "Codex builds persistent memory from its attempts at training tasks. The memory carries forward between stages, and held-out tasks receive a copy of the memory learned so far."
        rows += [["Training data", "Training tasks from Stage 1 through the current stage; learned memory carries forward", "Implementation behavior"],
                 ["EOG training parallelism", "1 training task at a time", "Required by the current implementation; original run setting unknown"],
                 ["ALE training parallelism", "Training tasks can run in parallel in separate environments; the experiment’s parallel-task limit was not reported", unknown],
                 ["Memory extraction time limit", "600 seconds per memory-extraction operation", default],
                 ["Memory consolidation time limit", "900 seconds to combine extracted memories", default],
                 ["Memory extraction parallelism", "Up to 8 extraction operations at once", default],
                 ["Candidate search", "None; compute is spent on training-task attempts and memory processing", "Implementation behavior"]]
        notes.append("The original memory-processing settings and total training token usage or monetary cost were not reported. Held-out task attempts are kept separate from the memory used to train later stages.")
        sources += [f"{prefix}/src/scripts/run_cumulative_{'skill' if track == 'skills' else 'agents'}.py", "evovle_agents/src/config.py:328", f"{prefix}/src/config.py"]
    elif key in ("raw-memory", "reasoning-bank", "memtoolagent"):
        representation = {"raw-memory": "Records of actions and results from training-task attempts", "reasoning-bank": "Reasoning guidance generated from training-task attempts", "memtoolagent": "Written reflections on training-task attempts"}[key]
        description = "The system retains " + representation.lower() + " across stages. The agent receives this memory alongside the tools introduced so far."
        rows += [["What the memory stores", representation, recorded],
                 ["ALE training repetitions", "1 attempt per training task in the available sample of stage records", "Recorded sample; not verified for every stage"],
                 ["Candidate search", "None; compute is spent on training-task attempts and creating memories", "Implementation behavior"]]
        if key in ("raw-memory", "memtoolagent"):
            rows.append(["Memories supplied to an ALE task", "The 10 most recent memories; setting the limit to 0 removes the cap", default])
        else:
            rows.append(["Memory generation and retrieval limits", "The original experiment’s limits were not reported", unknown])
        notes += ["Some EOG experiments contain 8 evaluation repetitions. These results use repetitions 1–3 for consistency with the other systems.",
                  "The separately listed Codex (ALE, V) system is the deployment baseline used for comparison with these memory methods on ALE.",
                  "The total token usage and monetary cost of building memory were not reported. Held-out evaluation usage excludes that work."]
        launcher = {"raw-memory": "gpt5_evolve_ale_cumulative_tool_memory.sh", "reasoning-bank": "gpt5_evolve_ale_cumulative_tool_adapt_fwd_reasoning.sh", "memtoolagent": "gpt5_evolve_ale_cumulative_tool_adapt_fwd_reflection.sh"}[key]
        sources += ["external/evolving-mas-benchmark/evolve_tools/src/memory.py", "external/evolving-mas-benchmark/evolve_tools/src/reasoning_induction.py", "external/evolving-mas-benchmark/evolve_tools/src/scripts/frequent_config/" + launcher]
    elif key in ("gepa", "gepa-oracle"):
        description = "GEPA uses feedback from task attempts to improve prompt text. The selected prompt carries forward to the next stage."
        rows += [["Optimization budget", "50 task evaluations per optimization stage, counted as GEPA metric calls", recorded],
                 ["Tasks per feedback batch", "3 tasks", recorded],
                 ["Optimization repetitions", "1 attempt per task for each candidate being evaluated", recorded],
                 ["Prompt-improvement model", "GPT-5", recorded],
                 ["Prompt-improvement response limit", "32,768 completion tokens per response, including reasoning tokens", default],
                 ["Prompt-improvement request attempts", "Up to 5 attempts per response: the initial request and at most 4 retries", default],
                 ["Optimization parallelism", "Up to 8 task attempts at once", default],
                 ["Random seed for search sampling", "0", default],
                 ["Initial prompt", "The provided task-solving prompt, before GEPA adds or edits guidance", default],
                 ["Improvement rule", "Accept an edit only when its total score on the sampled comparison batch exceeds its parent prompt’s score; reject ties", default],
                 ["Candidate selection", "Pareto selection: choose among prompts that lead on different validation tasks", default],
                 ["Prompt-section selection", "Edit one named section at a time, cycling through sections for each candidate (round-robin)", default],
                 ["Combining candidate prompts", "Disabled; sections from two parent prompts are not merged", default],
                 ["Reusing cached evaluation results", "Disabled; evaluate a repeated prompt and task again instead of reusing its prior score", default]]
        notes += ["One GEPA metric call evaluates one candidate on one task once. A batch of 3 tasks with 1 repetition uses 3 metric calls; it can contain many model requests and tool calls.",
                  "The 50-call budget is a stopping threshold. Initial validation counts toward it, a final batch can exceed it, and request retries add compute.",
                  "At each stage, validation includes tasks from Stage 1 through the current stage. Prompt improvement uses the current stage’s training tasks when continuing an adapted prompt; otherwise it uses training tasks from all stages seen so far.",
                  "An edit that improves the sampled comparison batch can still reduce full-validation or held-out performance. The random seed controls search sampling; it is separate from the starting prompt."]
        sources += [f"{prefix}/src/scripts/run_gepa.sh", f"{prefix}/meta_harness/run_gepa.py", f"{prefix}/meta_harness/gepa_reflection.py", f"{prefix}/meta_harness/splits.py"]
        if key == "gepa-oracle":
            description += " This variant optimizes with the skills designated for each task, then evaluates with the full library available at that stage."
            rows.append(["Skills supplied during optimization", "Only the skills designated for each task", recorded])
            rows.append(["Skills supplied during held-out evaluation", "Full final-stage library: CSM 9 skills, HR 10 skills, ITSM 10 skills", recorded])
            notes.append("Held-out results are available only for the final stage: Stage 3 in CSM and HR, and Stage 4 in ITSM. Earlier optimization stages do not provide earlier held-out results. No ALE results are available for this variant.")
            sources.append("evovle_skills/jobs/oracle_skills_gepa/<stream>/oracle_skills_gepa_*/v*/search.json")
        else:
            sources.append(arm.root + "/<stream>/run_*/v*/search.json")
    elif key == "meta":
        description = "Meta-Harness asks GPT-5 to edit the Python program that controls the agent and its learned state. The selected program and state carry forward between stages."
        rows += [["Proposal rounds", "5 requested rounds per optimization stage", "Configured experiment budget"],
                 ["Candidate programs requested", "3 per proposal round", "Proposal instruction; completion not guaranteed"],
                 ["EOG candidate-validation repetitions", "3 attempts per validation task for each candidate", recorded],
                 ["ALE candidate-validation repetitions", "Per validation task, for each candidate: " + "; ".join(f"Stage {i}: {n.strip()} {'attempt' if n.strip() == '1' else 'attempts'}" for i, n in enumerate(ALE_REPEATS[track].split(","), 1)), recorded],
                 ["Program-proposal model", "GPT-5", "Configured experiment setting"],
                 ["Proposal code-editing time limit", "2,400 seconds (40 minutes) per proposal round; candidate learning and validation take additional time", "Configured experiment setting"],
                 ["Candidate learning method", "Update the program’s learned state from training examples, then freeze that state for validation (offline learning)", "Configured experiment setting"],
                 ["Training passes", "1 pass through the assigned training examples (1 epoch)", "Configured experiment setting"],
                 ["Training batch size", "1 example per learning step", "Configured experiment setting"],
                 ["Initial comparison programs", "The unmodified agent program and a program given all training examples in its prompt; later stages also compare the previous stage’s winner", default],
                 ["Optimization parallelism", "Up to 8 task attempts at once", default]]
        notes += ["Each candidate is evaluated on the full validation set, using the repetition count shown for its stage. These validation attempts select the candidate; they are separate from the 3 repetitions used to report held-out results.",
                  "Five proposal rounds requesting 3 candidates each do not guarantee 15 completed candidate evaluations. Some recorded stages stopped before completing the requested work.",
                  "The implementation now defaults to 1 validation attempt per task throughout ALE. The recorded stage schedule above is the relevant setting for these results.",
                  "Candidate learning changes program state, not model weights. It reads training examples without requiring the task-solving agent to attempt each training task, although the candidate’s learning code may make model requests.",
                  "At each stage, validation includes tasks from Stage 1 through the current stage. Learning uses the current stage’s training examples when the previous stage’s learned state is successfully restored; otherwise it uses training examples from all stages seen so far."]
        sources += [f"{prefix}/src/scripts/run_meta_harness.sh", f"{prefix}/meta_harness/config.yaml", f"{prefix}/meta_harness/skills/meta-harness/SKILL.md", f"{prefix}/meta_harness/logs/run_*/v*/<stream>/<candidate>/gpt-5/val.json"]
    elif key == "skillopt":
        description = "SkillOpt uses GPT-5.5 with the EOG skills introduced through the current stage. Its task-solving model differs from the GPT-5 baselines."
        rows += [["Optimization budget", "Not reported for this experiment", unknown],
                 ["Task time limit", "Not reported", unknown],
                 ["Parallel task limit", "Not reported", unknown]]
        notes += ["Results are available for EOG only. Task durations were not reported; unavailable timing must not be interpreted as zero cost."]
    else:
        raise ValueError(f"Configuration evidence required for {track}/{key}")

    if key in ("gepa", "gepa-oracle", "meta"):
        notes += ["GEPA counts task evaluations, whereas Meta-Harness counts proposal rounds. These budgets do not establish equal model usage, elapsed time, or monetary cost across methods.",
                  "The total optimization token or monetary budget and original parallel-task limit were not reported. The 3 held-out evaluation repetitions do not represent 3 independent optimization runs."]
    if track == "agents" and key in ("oracle", "codex"):
        rows[0] = ["Task-solving model", "EOG: gpt-5-codex; ALE: gpt-5", recorded]
        model = "GPT-5 / GPT-5-Codex"
    if key == "oracle-gpt55":
        notes.append("This EOG-only experiment, run on August 26, changes the task-solving model from GPT-5 to GPT-5.5. It reports the same agent communication protocol, local execution setup, parallel-task limit and task time limit as the GPT-5 reference.")
    if track == "tools":
        if key != "react-ale-v":
            model_basis = recorded if key in ("gepa", "meta") else default
            rows.append(["EOG agent loop limit", "50 ReAct iterations per task", default])
            rows.append(["EOG model response token limit", "16,384 tokens per response", model_basis])
            rows.append(["EOG sampling temperature", "0.1", model_basis])
        rows.append(["ALE task time limit", "7,200 seconds per task", "Recorded configuration and implementation setting"])
        sources += ["evolve_tools/src/runner.py", "evolve_tools/src/ale_eval.py", "reference/EnterpriseOps-Gym/conf/llm/gpt-5.json (model settings only)"]
    elif key != "skillopt":
        if claude:
            rows.append(["EOG task time limit", "900 seconds per task", recorded])
            rows.append(["ALE task time limit", "Not reported", unknown])
            notes.append("Some EOG token-usage measurements come from 1 additional repetition run specifically to measure usage. Accuracy uses the original 3 evaluation repetitions. Missing token counts mean the reported usage may understate total cost.")
            sources.append("yang_li/results_final/README.md")
        else:
            rows.append(["EOG task time limit", "900 seconds in total for each task", default])
            rows.append(["EOG task continuation limit", "Up to 4 episodes in total, including continuations, within the same task time limit; separate from evaluation repetitions", default])
            if key not in ("oracle-gpt55", "gepa-oracle"):
                rows.append(["ALE task time limit", "7,200 seconds per task", "Recorded configuration and implementation setting"])
            sources += [f"{prefix}/src/config.py", f"{prefix}/src/runner.py"]
            if track == "agents":
                rows.append(["Agent thread limit", "12 concurrent agent threads", "Recorded base setting and implementation default"])
                rows.append(["Delegation depth limit", "1 level of specialist delegation below the lead agent", "Recorded base setting and implementation default"])
                notes.append("The delegation limits describe the base Codex configuration. A program produced by optimization may change how agents are coordinated.")
    if track == "tools" and key == "react":
        notes.append("The separately listed Codex (ALE, V) experiment is the ALE deployment baseline used for comparison with the tool-memory methods.")
    if track == "tools" and key == "react-ale-v":
        notes.append("This is the ALE deployment baseline used for comparison with the tool-memory methods. Its results are reported separately from the other ReAct / Codex deployment experiment.")
    rows += [["Held-out evaluation repetitions", "3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run", recorded],
             ["Total experiment compute", "Not reported; held-out evaluation usage excludes training, memory building and optimization", unknown]]
    return dict(name="Meta-Harness" if key == "meta" else arm.name, track=track, arm=key,
                model=model, harness=harness, author=arm.author, kind=kind,
                description=description, settings=rows, notes=notes, sources=sources)
