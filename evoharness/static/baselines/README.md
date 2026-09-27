# Registered baseline experiments

Every entry in `analysis/arms.py`, using the existing August 2026 analysis snapshot. No new benchmark runs were performed.

Click a system name in the leaderboard for its configuration and results. Additional archived variants are linked inside the corresponding system details. Configuration JSONs distinguish saved values, current defaults and unavailable launch settings.

**Reproduce the numbers offline:** download [reproducibility-kit.zip](reproducibility-kit.zip), extract it, and run `python3 verify_results.py` inside `evoharness-baselines/`. Python 3.10+; standard library only; no API key, network, experiment checkout or model calls required. [Full instructions and experiment rerun requirements](REPRODUCE.md).

Rebuild from the experiment checkout: `python tools/build_baseline_details.py /path/to/mas_evovle_enviroment`. The exporter imports the registry, crosschecks trial and cell caches, and preserves their historical task filtering.

## Results and coverage

| Track | Registry arm | System | EOG Score / Pass (%) | ALE Score / Pass (%) |
|---|---|---|---:|---:|
| tools | oracle | [Task-specific ReAct/Codex](tools-oracle-configuration.json) | 56.9 / 25.9 | 34.6 / 11.6 |
| tools | react | [ReAct/Codex](tools-react-configuration.json) | 60.0 / 30.2 | 30.5 / 13.2 |
| tools | meta | [Meta-Harness](tools-meta-harness-configuration.json) | 65.8 / 35.2 | 30.4 / 11.1 |
| tools | gepa | [GEPA](tools-gepa-configuration.json) | 65.9 / 31.9 | 30.9 / 11.1 |
| tools | react-ale-v | [Codex (ALE, V)](tools-react-ale-v-configuration.json) | Not evaluated | 30.0 / 12.2 |
| tools | raw-memory | [Raw memory](tools-raw-memory-configuration.json) | 66.2 / 33.0 | 21.4 / 7.9 |
| tools | reasoning-bank | [Reasoning bank](tools-reasoning-bank-configuration.json) | 68.7 / 36.9 | 28.4 / 11.1 |
| tools | memtoolagent | [MemToolAgent](tools-memtoolagent-configuration.json) | 68.9 / 38.6 | 25.8 / 10.1 |
| skills | oracle | [Task-specific Codex](skills-oracle-configuration.json) | 57.8 / 18.9 | 27.9 / 7.4 |
| skills | oracle-gpt55 | [Task-specific Codex (gpt-5.5)](skills-oracle-gpt55-configuration.json) | 75.1 / 40.5 | Not evaluated |
| skills | oracle-claude | [Task-specific Claude Code](skills-oracle-claude-configuration.json) | 65.5 / 29.3 | 35.0 / 13.2 |
| skills | claude | [Claude Code](skills-claude-configuration.json) | 67.3 / 30.2 | 35.4 / 13.2 |
| skills | codex | [Codex](skills-codex-configuration.json) | 59.1 / 18.9 | 25.5 / 8.3 |
| skills | memory | [Codex Memory](skills-memory-configuration.json) | 58.0 / 17.8 | 25.6 / 9.3 |
| skills | meta | [Meta-Harness](skills-meta-harness-configuration.json) | 59.5 / 19.4 | 26.1 / 7.8 |
| skills | gepa | [GEPA](skills-gepa-configuration.json) | 61.0 / 24.1 | 27.8 / 7.4 |
| skills | gepa-oracle | [Task-specific GEPA (eval on full library)](skills-gepa-oracle-configuration.json) | 63.1 / 23.0 | Not evaluated |
| skills | skillopt | [SkillOpt](skills-skillopt-configuration.json) | 61.8 / 21.2 | Not evaluated |
| agents | oracle | [Task-specific Codex](agents-oracle-configuration.json) | 36.3 / 6.5 | 19.2 / 5.3 |
| agents | oracle-claude | [Task-specific Claude Code](agents-oracle-claude-configuration.json) | 47.2 / 11.0 | 41.3 / 16.9 |
| agents | codex | [Codex](agents-codex-configuration.json) | 42.9 / 8.8 | 16.4 / 4.2 |
| agents | claude | [Claude Code](agents-claude-configuration.json) | 49.5 / 10.6 | 42.3 / 15.3 |
| agents | memory | [Codex Memory](agents-memory-configuration.json) | 42.3 / 10.1 | 16.6 / 3.7 |
| agents | meta | [Meta-Harness](agents-meta-harness-configuration.json) | 57.6 / 18.5 | 18.3 / 3.2 |
| agents | gepa | [GEPA](agents-gepa-configuration.json) | 54.1 / 14.9 | 23.6 / 6.3 |

Score is partial credit; Pass is strict task success. Task-weighted within each run, then averaged over runs 1–3. SD is population SD of run means, not a confidence interval or independent-search variance.

For cumulative experiments, `*-stages.csv` pools recorded cohorts j ≤ k at each stage; `*-matrix.csv` preserves all R[k,j] cells including forward evaluations. Task-specific controls show each cohort separately. Benchmark aggregates pool all control cohorts or each cumulative stream’s final recorded row. Missing cells are never filled or copied.

`*-trials.csv` is the exact counted task/run manifest with score and success flag, including failures. `*-runs.csv` includes exact score sums, success counts, denominators and recorded usage. No prompts or trajectories are needed for the offline reconstruction. Zero usage can mean missing telemetry. SkillOpt duration is unrecorded. Some Claude usage comes from a separate telemetry pass. These are evaluation costs, not training/search budgets.

Known headline differences: tools/oracle cache has 455 EOG tasks versus 454 on the website; tools/react uses the local ALE run while the website matches react-ale-v; agents/memory ALE is 16.6 Score / 3.7 Pass here versus 15.4 / 3.4 on the website. Evaluation exports retain their recorded values; the leaderboard retains the paper’s reported ranking.

Historical ALE counts are 63 for tools/agents and 68 for skills. The current exclusion manifest changed September 16; this export preserves cached denominators. The historical manifest is included for provenance and is not reapplied as a new filter.

Source paths are relative to the experiment repository; `external/evolving-mas-benchmark/` denotes a separate checkout. Each configuration JSON locates all stream roots. No credentials, prompts or private absolute paths are copied.

## Configurations and budgets

### tools / Task-specific ReAct/Codex (`oracle`)

Task-specific reference. Each task receives its selected capability subset; no state accumulates across cohorts.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5 | Recorded |
| Capability selection | Task-specific tools | Registry / runner |
| Stage search budget | No stage-level prompt or harness search in this control | Experiment design |
| EOG solver limits | ReAct: 50 iterations; max_tokens 16,384; temperature 0.1 | Reference defaults; historical overrides unverified |
| ALE solver limit | 7,200 seconds per task | Saved experiment configuration / runner |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- Each stage point evaluates that cohort only. The benchmark aggregate pools all cohorts; this is not a cumulative adaptation curve.

Sources: `analysis/arms.py`; `analysis/cache/cells_tools.tsv`; `evolve_tools/src/runner.py`; `evolve_tools/src/ale_eval.py`; `reference/EnterpriseOps-Gym/conf/llm/gpt-5.json (model settings only)`

### tools / ReAct/Codex (`react`)

Deployment baseline with the benchmark’s accumulating capability pool. No stage-specific prompt or harness optimization.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5 | Recorded |
| Stage search budget | No stage-level optimization | Experiment design |
| Capability pool | Cumulative through the selected stage | Registry / runner |
| EOG solver limits | ReAct: 50 iterations; max_tokens 16,384; temperature 0.1 | Reference defaults; historical overrides unverified |
| ALE solver limit | 7,200 seconds per task | Saved experiment configuration / runner |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- The separate Codex (ALE, V) experiment provides the ALE deployment control for the tool-memory baselines.

Sources: `analysis/arms.py`; `analysis/cache/cells_tools.tsv`; `evolve_tools/src/runner.py`; `evolve_tools/src/ale_eval.py`; `reference/EnterpriseOps-Gym/conf/llm/gpt-5.json (model settings only)`

### tools / Meta-Harness (`meta`)

Code-based adaptation. A GPT-5 proposer edits the Python harness and learned state, carrying the selected program and state between stages.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5 | Recorded |
| Search budget | 5 proposer iterations per stage | Launcher configuration |
| Candidates | 3 requested per iteration | Proposer instruction |
| EOG search repetitions | 3 trials per task | Recorded |
| ALE candidate validation repetitions | v1: 3 trials/task; v2: 3 trials/task; v3: 3 trials/task; v4: 3 trials/task; v5: 1 trials/task | Recorded; repetitions per candidate, separate from held-out evaluation |
| Proposer | GPT-5; 2,400 seconds per iteration | Configuration |
| Inner learning | Offline; 1 epoch; batch size 1 | Configuration |
| Concurrency | 8 concurrent trials | Current default |
| EOG solver limits | ReAct: 50 iterations; max_tokens 16,384; temperature 0.1 | Iteration default / saved model configuration |
| ALE solver limit | 7,200 seconds per task | Saved experiment configuration / runner |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- Each candidate is evaluated on the full validation set. Five iterations do not guarantee 15 evaluated candidates; archived logs include incomplete stages.
- The current ALE launcher defaults to one search trial/task throughout. The recorded schedule above differs.
- Validation pools cohorts 1…k, with winners carried forward. Learning uses the new cohort with cumulative-data fallback from the seed.
- GEPA metric calls and Meta-Harness proposer iterations are different budget units. These searches were not demonstrated to be compute-matched.
- No complete search token/dollar cap or historical concurrency override was established. Three evaluation runs are not three independent searches.

Sources: `analysis/arms.py`; `analysis/cache/cells_tools.tsv`; `evolve_tools/src/scripts/run_meta_harness.sh`; `evolve_tools/meta_harness/config.yaml`; `evolve_tools/meta_harness/skills/meta-harness/SKILL.md`; `evolve_tools/meta_harness/logs/run_*/v*/<stream>/<candidate>/gpt-5/val.json`; `evolve_tools/src/runner.py`; `evolve_tools/src/ale_eval.py`; `reference/EnterpriseOps-Gym/conf/llm/gpt-5.json (model settings only)`

### tools / GEPA (`gepa`)

Reflective prompt optimization. GEPA edits prompt text and carries the selected prompt forward between stages.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5 | Recorded |
| Search budget | 50 metric calls per searched stage | Recorded search.json |
| Reflection minibatch | 3 tasks | Recorded |
| Search repetitions | 1 trial per task | Recorded |
| Reflection model | GPT-5 | Recorded |
| Reflection response limit | 32,768 tokens; up to 5 API attempts | Current configuration |
| Concurrency / RNG seed | 8 concurrent trials / seed 0 | Current defaults |
| EOG solver limits | ReAct: 50 iterations; max_tokens 16,384; temperature 0.1 | Iteration default / saved model configuration |
| ALE solver limit | 7,200 seconds per task | Saved experiment configuration / runner |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- 50 calls is a stopping threshold: initial validation consumes calls, batches can overshoot, and retries add work.
- Library defaults: strict improvement, Pareto selection, round-robin module selection, no merge and no evaluation cache.
- Validation pools cohorts 1…k. Winners carry forward; learning uses the new cohort with a cumulative-data fallback from the seed.
- GEPA metric calls and Meta-Harness proposer iterations are different budget units. These searches were not demonstrated to be compute-matched.
- No complete search token/dollar cap or historical concurrency override was established. Three evaluation runs are not three independent searches.

Sources: `analysis/arms.py`; `analysis/cache/cells_tools.tsv`; `evolve_tools/src/scripts/run_gepa.sh`; `evolve_tools/meta_harness/run_gepa.py`; `evolve_tools/meta_harness/gepa_reflection.py`; `evolve_tools/meta_harness/splits.py`; `evolve_tools/jobs/cumulative_tools_gepa_cumulative_val/<stream>/run_*/v*/search.json`; `evolve_tools/src/runner.py`; `evolve_tools/src/ale_eval.py`; `reference/EnterpriseOps-Gym/conf/llm/gpt-5.json (model settings only)`

### tools / Codex (ALE, V) (`react-ale-v`)

Deployment baseline with the benchmark’s accumulating capability pool. No stage-specific prompt or harness optimization.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5 | Recorded |
| Stage search budget | No stage-level optimization | Experiment design |
| Capability pool | Cumulative through the selected stage | Registry / runner |
| ALE solver limit | 7,200 seconds per task | Saved experiment configuration / runner |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- ALE deployment control for the tool-memory baselines. Results are reported separately from the other ReAct / Codex deployment run.

Sources: `analysis/arms.py`; `analysis/cache/cells_tools.tsv`; `evolve_tools/src/runner.py`; `evolve_tools/src/ale_eval.py`; `reference/EnterpriseOps-Gym/conf/llm/gpt-5.json (model settings only)`

### tools / Raw memory (`raw-memory`)

Raw adaptation trajectories are retained across stages and supplied to the solver alongside the accumulating tool pool.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5 | Recorded |
| Memory representation | Raw adaptation trajectories | Registry / saved artifacts |
| ALE adaptation repetitions | 1 rollout per training task in inspected stage logs | Recorded sample |
| Search budget | No candidate-search loop; adaptation rollouts and memory induction add work | Runner |
| ALE retrieval limit | 10 most recent memories; 0 means unlimited | Current launcher default; historical override unknown |
| EOG solver limits | ReAct: 50 iterations; max_tokens 16,384; temperature 0.1 | Reference defaults; historical overrides unverified |
| ALE solver limit | 7,200 seconds per task | Saved experiment configuration / runner |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- EOG exports can contain eight evaluation runs. These results use runs 1–3 to match the other systems.
- Codex (ALE, V) is the ALE deployment control for these memory experiments.
- No complete adaptation token/dollar budget is recorded. Evaluation usage is not a measure of memory-building cost.

Sources: `analysis/arms.py`; `analysis/cache/cells_tools.tsv`; `external/evolving-mas-benchmark/evolve_tools/src/memory.py`; `external/evolving-mas-benchmark/evolve_tools/src/reasoning_induction.py`; `external/evolving-mas-benchmark/evolve_tools/src/scripts/frequent_config/gpt5_evolve_ale_cumulative_tool_memory.sh`; `evolve_tools/src/runner.py`; `evolve_tools/src/ale_eval.py`; `reference/EnterpriseOps-Gym/conf/llm/gpt-5.json (model settings only)`

### tools / Reasoning bank (`reasoning-bank`)

Induced reasoning memories are retained across stages and supplied to the solver alongside the accumulating tool pool.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5 | Recorded |
| Memory representation | Induced reasoning memories | Registry / saved artifacts |
| ALE adaptation repetitions | 1 rollout per training task in inspected stage logs | Recorded sample |
| Search budget | No candidate-search loop; adaptation rollouts and memory induction add work | Runner |
| Historical retrieval / induction budget | Not recorded in the exported evaluation configuration | Unavailable |
| EOG solver limits | ReAct: 50 iterations; max_tokens 16,384; temperature 0.1 | Reference defaults; historical overrides unverified |
| ALE solver limit | 7,200 seconds per task | Saved experiment configuration / runner |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- EOG exports can contain eight evaluation runs. These results use runs 1–3 to match the other systems.
- Codex (ALE, V) is the ALE deployment control for these memory experiments.
- No complete adaptation token/dollar budget is recorded. Evaluation usage is not a measure of memory-building cost.

Sources: `analysis/arms.py`; `analysis/cache/cells_tools.tsv`; `external/evolving-mas-benchmark/evolve_tools/src/memory.py`; `external/evolving-mas-benchmark/evolve_tools/src/reasoning_induction.py`; `external/evolving-mas-benchmark/evolve_tools/src/scripts/frequent_config/gpt5_evolve_ale_cumulative_tool_adapt_fwd_reasoning.sh`; `evolve_tools/src/runner.py`; `evolve_tools/src/ale_eval.py`; `reference/EnterpriseOps-Gym/conf/llm/gpt-5.json (model settings only)`

### tools / MemToolAgent (`memtoolagent`)

Reflections on adaptation trajectories are retained across stages and supplied to the solver alongside the accumulating tool pool.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5 | Recorded |
| Memory representation | Reflections on adaptation trajectories | Registry / saved artifacts |
| ALE adaptation repetitions | 1 rollout per training task in inspected stage logs | Recorded sample |
| Search budget | No candidate-search loop; adaptation rollouts and memory induction add work | Runner |
| ALE retrieval limit | 10 most recent memories; 0 means unlimited | Current launcher default; historical override unknown |
| EOG solver limits | ReAct: 50 iterations; max_tokens 16,384; temperature 0.1 | Reference defaults; historical overrides unverified |
| ALE solver limit | 7,200 seconds per task | Saved experiment configuration / runner |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- EOG exports can contain eight evaluation runs. These results use runs 1–3 to match the other systems.
- Codex (ALE, V) is the ALE deployment control for these memory experiments.
- No complete adaptation token/dollar budget is recorded. Evaluation usage is not a measure of memory-building cost.

Sources: `analysis/arms.py`; `analysis/cache/cells_tools.tsv`; `external/evolving-mas-benchmark/evolve_tools/src/memory.py`; `external/evolving-mas-benchmark/evolve_tools/src/reasoning_induction.py`; `external/evolving-mas-benchmark/evolve_tools/src/scripts/frequent_config/gpt5_evolve_ale_cumulative_tool_adapt_fwd_reflection.sh`; `evolve_tools/src/runner.py`; `evolve_tools/src/ale_eval.py`; `reference/EnterpriseOps-Gym/conf/llm/gpt-5.json (model settings only)`

### skills / Task-specific Codex (`oracle`)

Task-specific reference. Each task receives its selected capability subset; no state accumulates across cohorts.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5 | Recorded |
| Capability selection | Task-specific skills with oracle tools | Registry / runner |
| Stage search budget | No stage-level prompt or harness search in this control | Experiment design |
| EOG solver limit | 900 seconds per task shared across up to 4 episodes | Current default; historical overrides not fully established |
| ALE solver limit | 7,200 seconds per task | Saved experiment configuration / runner |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- Each stage point evaluates that cohort only. The benchmark aggregate pools all cohorts; this is not a cumulative adaptation curve.

Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`; `evovle_skills/src/config.py`; `evovle_skills/src/runner.py`

### skills / Task-specific Codex (gpt-5.5) (`oracle-gpt55`)

Task-specific reference. Each task receives its selected capability subset; no state accumulates across cohorts.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5.5 | Recorded |
| Capability selection | Task-specific skills with oracle tools | Registry / runner |
| Stage search budget | No stage-level prompt or harness search in this control | Experiment design |
| EOG solver limit | 900 seconds per task shared across up to 4 episodes | Current default; historical overrides not fully established |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- Each stage point evaluates that cohort only. The benchmark aggregate pools all cohorts; this is not a cumulative adaptation curve.
- Model-only swap of the GPT-5 task-specific skills control, run August 26. The registry records the same ACP transport, local backend, concurrency and timeout. EOG only.

Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`; `evovle_skills/src/config.py`; `evovle_skills/src/runner.py`

### skills / Task-specific Claude Code (`oracle-claude`)

Task-specific reference. Each task receives its selected capability subset; no state accumulates across cohorts.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | Sonnet-4.6 | Reported |
| Capability selection | Task-specific skills with oracle tools | Registry / runner |
| Stage search budget | No stage-level prompt or harness search in this control | Experiment design |
| EOG solver limit | 900 seconds per task | Export notes / timeout records |
| ALE solver limit / launch overrides | Not specified in the exported run configuration | Unavailable |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- Each stage point evaluates that cohort only. The benchmark aggregate pools all cohorts; this is not a cumulative adaptation curve.
- Some EOG usage comes from a dedicated one-run telemetry pass; accuracy still uses the original three runs. Missing usage means cost totals may be lower bounds.

Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`; `yang_li/results_final/README.md`

### skills / Claude Code (`claude`)

Deployment baseline with the benchmark’s accumulating capability pool. No stage-specific prompt or harness optimization.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | Sonnet-4.6 | Reported |
| Stage search budget | No stage-level optimization | Experiment design |
| Capability pool | Cumulative through the selected stage | Registry / runner |
| EOG solver limit | 900 seconds per task | Export notes / timeout records |
| ALE solver limit / launch overrides | Not specified in the exported run configuration | Unavailable |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- Some EOG usage comes from a dedicated one-run telemetry pass; accuracy still uses the original three runs. Missing usage means cost totals may be lower bounds.

Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`; `yang_li/results_final/README.md`

### skills / Codex (`codex`)

Deployment baseline with the benchmark’s accumulating capability pool. No stage-specific prompt or harness optimization.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5 | Recorded |
| Stage search budget | No stage-level optimization | Experiment design |
| Capability pool | Cumulative through the selected stage | Registry / runner |
| EOG solver limit | 900 seconds per task shared across up to 4 episodes | Current default; historical overrides not fully established |
| ALE solver limit | 7,200 seconds per task | Saved experiment configuration / runner |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |


Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`; `evovle_skills/src/config.py`; `evovle_skills/src/runner.py`

### skills / Codex Memory (`memory`)

Codex with native persistent memory. Training rollouts populate a shared memory home that is carried between stages and copied for evaluation.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5 | Recorded |
| Adaptation | Training tasks from versions 1…k; memory carried between stages | Current runner |
| Memory training concurrency | EOG: 1 (forced); ALE: requested concurrency, with parallel sandbox rollouts | Current runner; historical override unknown |
| Extraction / consolidation limits | 600 / 900 seconds | Current defaults |
| Extraction concurrency | 8 | Current default |
| Stage search budget | No GEPA/Meta-Harness search; training and memory processing add work | Runner |
| EOG solver limit | 900 seconds per task shared across up to 4 episodes | Current default; historical overrides not fully established |
| ALE solver limit | 7,200 seconds per task | Saved experiment configuration / runner |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- Historical memory-processing overrides and total adaptation tokens/cost are not recoverable from the evaluation snapshot. Held-out evaluation uses a copy of trained memory.

Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`; `evovle_skills/src/scripts/run_cumulative_skill.py`; `evovle_agents/src/config.py:328`; `evovle_skills/src/config.py`; `evovle_skills/src/config.py`; `evovle_skills/src/runner.py`

### skills / Meta-Harness (`meta`)

Code-based adaptation. A GPT-5 proposer edits the Python harness and learned state, carrying the selected program and state between stages.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5 | Recorded |
| Search budget | 5 proposer iterations per stage | Launcher configuration |
| Candidates | 3 requested per iteration | Proposer instruction |
| EOG search repetitions | 3 trials per task | Recorded |
| ALE candidate validation repetitions | v1: 3 trials/task; v2: 3 trials/task; v3: 3 trials/task; v4: 3 trials/task; v5: 3 trials/task; v6: 1 trials/task | Recorded; repetitions per candidate, separate from held-out evaluation |
| Proposer | GPT-5; 2,400 seconds per iteration | Configuration |
| Inner learning | Offline; 1 epoch; batch size 1 | Configuration |
| Concurrency | 8 concurrent trials | Current default |
| EOG solver limit | 900 seconds per task shared across up to 4 episodes | Current default; historical overrides not fully established |
| ALE solver limit | 7,200 seconds per task | Saved experiment configuration / runner |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- Each candidate is evaluated on the full validation set. Five iterations do not guarantee 15 evaluated candidates; archived logs include incomplete stages.
- The current ALE launcher defaults to one search trial/task throughout. The recorded schedule above differs.
- Validation pools cohorts 1…k, with winners carried forward. Learning uses the new cohort with cumulative-data fallback from the seed.
- GEPA metric calls and Meta-Harness proposer iterations are different budget units. These searches were not demonstrated to be compute-matched.
- No complete search token/dollar cap or historical concurrency override was established. Three evaluation runs are not three independent searches.

Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`; `evovle_skills/src/scripts/run_meta_harness.sh`; `evovle_skills/meta_harness/config.yaml`; `evovle_skills/meta_harness/skills/meta-harness/SKILL.md`; `evovle_skills/meta_harness/logs/run_*/v*/<stream>/<candidate>/gpt-5/val.json`; `evovle_skills/src/config.py`; `evovle_skills/src/runner.py`

### skills / GEPA (`gepa`)

Reflective prompt optimization. GEPA edits prompt text and carries the selected prompt forward between stages.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5 | Recorded |
| Search budget | 50 metric calls per searched stage | Recorded search.json |
| Reflection minibatch | 3 tasks | Recorded |
| Search repetitions | 1 trial per task | Recorded |
| Reflection model | GPT-5 | Recorded |
| Reflection response limit | 32,768 tokens; up to 5 API attempts | Current configuration |
| Concurrency / RNG seed | 8 concurrent trials / seed 0 | Current defaults |
| EOG solver limit | 900 seconds per task shared across up to 4 episodes | Current default; historical overrides not fully established |
| ALE solver limit | 7,200 seconds per task | Saved experiment configuration / runner |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- 50 calls is a stopping threshold: initial validation consumes calls, batches can overshoot, and retries add work.
- Library defaults: strict improvement, Pareto selection, round-robin module selection, no merge and no evaluation cache.
- Validation pools cohorts 1…k. Winners carry forward; learning uses the new cohort with a cumulative-data fallback from the seed.
- GEPA metric calls and Meta-Harness proposer iterations are different budget units. These searches were not demonstrated to be compute-matched.
- No complete search token/dollar cap or historical concurrency override was established. Three evaluation runs are not three independent searches.

Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`; `evovle_skills/src/scripts/run_gepa.sh`; `evovle_skills/meta_harness/run_gepa.py`; `evovle_skills/meta_harness/gepa_reflection.py`; `evovle_skills/meta_harness/splits.py`; `evovle_skills/jobs/cumulative_skill_gepa/<stream>/run_*/v*/search.json`; `evovle_skills/src/config.py`; `evovle_skills/src/runner.py`

### skills / Task-specific GEPA (eval on full library) (`gepa-oracle`)

Reflective prompt optimization. GEPA edits prompt text and carries the selected prompt forward between stages. This variant searches with each task’s oracle skills, then evaluates with the full stage library.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5 | Recorded |
| Search budget | 50 metric calls per searched stage | Recorded search.json |
| Reflection minibatch | 3 tasks | Recorded |
| Search repetitions | 1 trial per task | Recorded |
| Reflection model | GPT-5 | Recorded |
| Reflection response limit | 32,768 tokens; up to 5 API attempts | Current configuration |
| Concurrency / RNG seed | 8 concurrent trials / seed 0 | Current defaults |
| Search / evaluation library | Per-task oracle / full stage library (CSM 9, HR 10, ITSM 10 skills) | Recorded / registry |
| EOG solver limit | 900 seconds per task shared across up to 4 episodes | Current default; historical overrides not fully established |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- 50 calls is a stopping threshold: initial validation consumes calls, batches can overshoot, and retries add work.
- Library defaults: strict improvement, Pareto selection, round-robin module selection, no merge and no evaluation cache.
- Validation pools cohorts 1…k. Winners carry forward; learning uses the new cohort with a cumulative-data fallback from the seed.
- Only final-stage held-out evaluations are archived: CSM/HR v3, ITSM v4. Earlier search stages exist, but are not earlier held-out results. No ALE evaluation is registered.
- GEPA metric calls and Meta-Harness proposer iterations are different budget units. These searches were not demonstrated to be compute-matched.
- No complete search token/dollar cap or historical concurrency override was established. Three evaluation runs are not three independent searches.

Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`; `evovle_skills/src/scripts/run_gepa.sh`; `evovle_skills/meta_harness/run_gepa.py`; `evovle_skills/meta_harness/gepa_reflection.py`; `evovle_skills/meta_harness/splits.py`; `evovle_skills/jobs/oracle_skills_gepa/<stream>/oracle_skills_gepa_*/v*/search.json`; `evovle_skills/src/config.py`; `evovle_skills/src/runner.py`

### skills / SkillOpt (`skillopt`)

SkillOpt with GPT-5.5, evaluated against the cumulative EOG skill library. This is a different backbone from the GPT-5 systems.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5.5 | Registry |
| Optimization budget | Not recorded with this archived evaluation export | Unavailable |
| Solver limits / concurrency | Not established by these artifacts | Unavailable |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- EOG only. Recorded trial durations are unavailable; missing time must not be interpreted as zero cost.

Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`

### agents / Task-specific Codex (`oracle`)

Reference control with a per-cohort specialist library on EOG and task-specific specialist families on ALE. No cross-stage adaptation.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | EOG: gpt-5-codex in inspected saved config.toml; ALE: GPT-5 | Recorded |
| Capability selection | EOG: per-cohort reference specialist library; ALE: task-specific specialist families | Saved EOG manifests / ALE runner |
| Stage search budget | No stage-level prompt or harness search in this control | Experiment design |
| EOG solver limit | 900 seconds per task shared across up to 4 episodes | Current default; historical overrides not fully established |
| ALE solver limit | 7,200 seconds per task | Saved experiment configuration / runner |
| Base delegation limits | 12 threads; maximum depth 1 | Saved base configuration / current default |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- Each stage point evaluates that cohort only. The benchmark aggregate pools all cohorts; this is not a cumulative adaptation curve.
- On EOG, tasks with different selected tool sets use the same specialist roster within each cohort.
- These are base Codex delegation limits; an evolved harness may change orchestration behavior.

Sources: `analysis/arms.py`; `analysis/cache/cells_agents.tsv`; `evovle_agents/src/config.py`; `evovle_agents/src/runner.py`

### agents / Task-specific Claude Code (`oracle-claude`)

Task-specific reference. Each task receives its selected capability subset; no state accumulates across cohorts.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | Sonnet-4.6 | Reported |
| Capability selection | Task-specific specialist agents | Registry / runner |
| Stage search budget | No stage-level prompt or harness search in this control | Experiment design |
| EOG solver limit | 900 seconds per task | Export notes / timeout records |
| ALE solver limit / launch overrides | Not specified in the exported run configuration | Unavailable |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- Each stage point evaluates that cohort only. The benchmark aggregate pools all cohorts; this is not a cumulative adaptation curve.
- Some EOG usage comes from a dedicated one-run telemetry pass; accuracy still uses the original three runs. Missing usage means cost totals may be lower bounds.

Sources: `analysis/arms.py`; `analysis/cache/cells_agents.tsv`; `yang_li/results_final/README.md`

### agents / Codex (`codex`)

Deployment baseline with the benchmark’s accumulating capability pool. No stage-specific prompt or harness optimization.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | EOG: gpt-5-codex in inspected saved config.toml; ALE: GPT-5 | Recorded |
| Stage search budget | No stage-level optimization | Experiment design |
| Capability pool | Cumulative through the selected stage | Registry / runner |
| EOG solver limit | 900 seconds per task shared across up to 4 episodes | Current default; historical overrides not fully established |
| ALE solver limit | 7,200 seconds per task | Saved experiment configuration / runner |
| Base delegation limits | 12 threads; maximum depth 1 | Saved base configuration / current default |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- These are base Codex delegation limits; an evolved harness may change orchestration behavior.

Sources: `analysis/arms.py`; `analysis/cache/cells_agents.tsv`; `evovle_agents/src/config.py`; `evovle_agents/src/runner.py`

### agents / Claude Code (`claude`)

Deployment baseline with the benchmark’s accumulating capability pool. No stage-specific prompt or harness optimization.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | Sonnet-4.6 | Reported |
| Stage search budget | No stage-level optimization | Experiment design |
| Capability pool | Cumulative through the selected stage | Registry / runner |
| EOG solver limit | 900 seconds per task | Export notes / timeout records |
| ALE solver limit / launch overrides | Not specified in the exported run configuration | Unavailable |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- Some EOG usage comes from a dedicated one-run telemetry pass; accuracy still uses the original three runs. Missing usage means cost totals may be lower bounds.

Sources: `analysis/arms.py`; `analysis/cache/cells_agents.tsv`; `yang_li/results_final/README.md`

### agents / Codex Memory (`memory`)

Codex with native persistent memory. Training rollouts populate a shared memory home that is carried between stages and copied for evaluation.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5 | Recorded |
| Adaptation | Training tasks from versions 1…k; memory carried between stages | Current runner |
| Memory training concurrency | EOG: 1 (forced); ALE: requested concurrency, with parallel sandbox rollouts | Current runner; historical override unknown |
| Extraction / consolidation limits | 600 / 900 seconds | Current defaults |
| Extraction concurrency | 8 | Current default |
| Stage search budget | No GEPA/Meta-Harness search; training and memory processing add work | Runner |
| EOG solver limit | 900 seconds per task shared across up to 4 episodes | Current default; historical overrides not fully established |
| ALE solver limit | 7,200 seconds per task | Saved experiment configuration / runner |
| Base delegation limits | 12 threads; maximum depth 1 | Saved base configuration / current default |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- Historical memory-processing overrides and total adaptation tokens/cost are not recoverable from the evaluation snapshot. Held-out evaluation uses a copy of trained memory.
- These are base Codex delegation limits; an evolved harness may change orchestration behavior.

Sources: `analysis/arms.py`; `analysis/cache/cells_agents.tsv`; `evovle_agents/src/scripts/run_cumulative_agents.py`; `evovle_agents/src/config.py:328`; `evovle_agents/src/config.py`; `evovle_agents/src/config.py`; `evovle_agents/src/runner.py`

### agents / Meta-Harness (`meta`)

Code-based adaptation. A GPT-5 proposer edits the Python harness and learned state, carrying the selected program and state between stages.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5 | Recorded |
| Search budget | 5 proposer iterations per stage | Launcher configuration |
| Candidates | 3 requested per iteration | Proposer instruction |
| EOG search repetitions | 3 trials per task | Recorded |
| ALE candidate validation repetitions | v1: 3 trials/task; v2: 3 trials/task; v3: 3 trials/task; v4: 3 trials/task; v5: 1 trials/task; v6: 1 trials/task | Recorded; repetitions per candidate, separate from held-out evaluation |
| Proposer | GPT-5; 2,400 seconds per iteration | Configuration |
| Inner learning | Offline; 1 epoch; batch size 1 | Configuration |
| Concurrency | 8 concurrent trials | Current default |
| EOG solver limit | 900 seconds per task shared across up to 4 episodes | Current default; historical overrides not fully established |
| ALE solver limit | 7,200 seconds per task | Saved experiment configuration / runner |
| Base delegation limits | 12 threads; maximum depth 1 | Saved base configuration / current default |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- Each candidate is evaluated on the full validation set. Five iterations do not guarantee 15 evaluated candidates; archived logs include incomplete stages.
- The current ALE launcher defaults to one search trial/task throughout. The recorded schedule above differs.
- Validation pools cohorts 1…k, with winners carried forward. Learning uses the new cohort with cumulative-data fallback from the seed.
- GEPA metric calls and Meta-Harness proposer iterations are different budget units. These searches were not demonstrated to be compute-matched.
- No complete search token/dollar cap or historical concurrency override was established. Three evaluation runs are not three independent searches.
- These are base Codex delegation limits; an evolved harness may change orchestration behavior.

Sources: `analysis/arms.py`; `analysis/cache/cells_agents.tsv`; `evovle_agents/src/scripts/run_meta_harness.sh`; `evovle_agents/meta_harness/config.yaml`; `evovle_agents/meta_harness/skills/meta-harness/SKILL.md`; `evovle_agents/meta_harness/logs/run_*/v*/<stream>/<candidate>/gpt-5/val.json`; `evovle_agents/src/config.py`; `evovle_agents/src/runner.py`

### agents / GEPA (`gepa`)

Reflective prompt optimization. GEPA edits prompt text and carries the selected prompt forward between stages.

| Setting | Value | Evidence |
|---|---|---|
| Solver model | GPT-5 | Recorded |
| Search budget | 50 metric calls per searched stage | Recorded search.json |
| Reflection minibatch | 3 tasks | Recorded |
| Search repetitions | 1 trial per task | Recorded |
| Reflection model | GPT-5 | Recorded |
| Reflection response limit | 32,768 tokens; up to 5 API attempts | Current configuration |
| Concurrency / RNG seed | 8 concurrent trials / seed 0 | Current defaults |
| EOG solver limit | 900 seconds per task shared across up to 4 episodes | Current default; historical overrides not fully established |
| ALE solver limit | 7,200 seconds per task | Saved experiment configuration / runner |
| Base delegation limits | 12 threads; maximum depth 1 | Saved base configuration / current default |
| Held-out evaluation | Runs 1, 2 and 3 per recorded cell | Archived snapshot |
| Complete total compute budget | Not established; evaluation metrics exclude adaptation/search work | Unavailable |

- 50 calls is a stopping threshold: initial validation consumes calls, batches can overshoot, and retries add work.
- Library defaults: strict improvement, Pareto selection, round-robin module selection, no merge and no evaluation cache.
- Validation pools cohorts 1…k. Winners carry forward; learning uses the new cohort with a cumulative-data fallback from the seed.
- GEPA metric calls and Meta-Harness proposer iterations are different budget units. These searches were not demonstrated to be compute-matched.
- No complete search token/dollar cap or historical concurrency override was established. Three evaluation runs are not three independent searches.
- These are base Codex delegation limits; an evolved harness may change orchestration behavior.

Sources: `analysis/arms.py`; `analysis/cache/cells_agents.tsv`; `evovle_agents/src/scripts/run_gepa.sh`; `evovle_agents/meta_harness/run_gepa.py`; `evovle_agents/meta_harness/gepa_reflection.py`; `evovle_agents/meta_harness/splits.py`; `evovle_agents/jobs/cumulative_agents_gepa/<stream>/run_*/v*/search.json`; `evovle_agents/src/config.py`; `evovle_agents/src/runner.py`
