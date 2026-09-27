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

Reference system given the capabilities selected for each task. It does not learn or retain experience between stages.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5 | Recorded experiment setting |
| Capabilities supplied to each task | The task’s designated tools | Reported experiment setting |
| Optimization between stages | None; no prompt or agent-program search | Experiment design |
| EOG agent loop limit | 50 ReAct iterations per task | Implementation default; original run setting unknown |
| EOG model response token limit | 16,384 tokens per response | Implementation default; original run setting unknown |
| EOG sampling temperature | 0.1 | Implementation default; original run setting unknown |
| ALE task time limit | 7,200 seconds per task | Recorded configuration and implementation setting |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- Each stage result covers that stage’s held-out tasks only. The overall benchmark result combines tasks from all stages. No adaptation takes place between these evaluations.

Sources: `analysis/arms.py`; `analysis/cache/cells_tools.tsv`; `evolve_tools/src/runner.py`; `evolve_tools/src/ale_eval.py`; `reference/EnterpriseOps-Gym/conf/llm/gpt-5.json (model settings only)`

### tools / ReAct/Codex (`react`)

Deployment baseline that receives the capabilities introduced up to the current stage. Its prompt and agent program are not optimized between stages.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5 | Recorded experiment setting |
| Optimization between stages | None | Experiment design |
| Available capabilities | All capabilities introduced through the selected stage | Reported experiment setting |
| EOG agent loop limit | 50 ReAct iterations per task | Implementation default; original run setting unknown |
| EOG model response token limit | 16,384 tokens per response | Implementation default; original run setting unknown |
| EOG sampling temperature | 0.1 | Implementation default; original run setting unknown |
| ALE task time limit | 7,200 seconds per task | Recorded configuration and implementation setting |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- The separately listed Codex (ALE, V) experiment is the ALE deployment baseline used for comparison with the tool-memory methods.

Sources: `analysis/arms.py`; `analysis/cache/cells_tools.tsv`; `evolve_tools/src/runner.py`; `evolve_tools/src/ale_eval.py`; `reference/EnterpriseOps-Gym/conf/llm/gpt-5.json (model settings only)`

### tools / Meta-Harness (`meta`)

Meta-Harness asks GPT-5 to edit the Python program that controls the agent and its learned state. The selected program and state carry forward between stages.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5 | Recorded experiment setting |
| Proposal rounds | 5 requested rounds per optimization stage | Configured experiment budget |
| Candidate programs requested | 3 per proposal round | Proposal instruction; completion not guaranteed |
| EOG candidate-validation repetitions | 3 attempts per validation task for each candidate | Recorded experiment setting |
| ALE candidate-validation repetitions | Per validation task, for each candidate: Stage 1: 3 attempts; Stage 2: 3 attempts; Stage 3: 3 attempts; Stage 4: 3 attempts; Stage 5: 1 attempt | Recorded experiment setting |
| Program-proposal model | GPT-5 | Configured experiment setting |
| Proposal code-editing time limit | 2,400 seconds (40 minutes) per proposal round; candidate learning and validation take additional time | Configured experiment setting |
| Candidate learning method | Update the program’s learned state from training examples, then freeze that state for validation (offline learning) | Configured experiment setting |
| Training passes | 1 pass through the assigned training examples (1 epoch) | Configured experiment setting |
| Training batch size | 1 example per learning step | Configured experiment setting |
| Initial comparison programs | The unmodified agent program and a program given all training examples in its prompt; later stages also compare the previous stage’s winner | Implementation default; original run setting unknown |
| Optimization parallelism | Up to 8 task attempts at once | Implementation default; original run setting unknown |
| EOG agent loop limit | 50 ReAct iterations per task | Implementation default; original run setting unknown |
| EOG model response token limit | 16,384 tokens per response | Recorded experiment setting |
| EOG sampling temperature | 0.1 | Recorded experiment setting |
| ALE task time limit | 7,200 seconds per task | Recorded configuration and implementation setting |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- Each candidate is evaluated on the full validation set, using the repetition count shown for its stage. These validation attempts select the candidate; they are separate from the 3 repetitions used to report held-out results.
- Five proposal rounds requesting 3 candidates each do not guarantee 15 completed candidate evaluations. Some recorded stages stopped before completing the requested work.
- The implementation now defaults to 1 validation attempt per task throughout ALE. The recorded stage schedule above is the relevant setting for these results.
- Candidate learning changes program state, not model weights. It reads training examples without requiring the task-solving agent to attempt each training task, although the candidate’s learning code may make model requests.
- At each stage, validation includes tasks from Stage 1 through the current stage. Learning uses the current stage’s training examples when the previous stage’s learned state is successfully restored; otherwise it uses training examples from all stages seen so far.
- GEPA counts task evaluations, whereas Meta-Harness counts proposal rounds. These budgets do not establish equal model usage, elapsed time, or monetary cost across methods.
- The total optimization token or monetary budget and original parallel-task limit were not reported. The 3 held-out evaluation repetitions do not represent 3 independent optimization runs.

Sources: `analysis/arms.py`; `analysis/cache/cells_tools.tsv`; `evolve_tools/src/scripts/run_meta_harness.sh`; `evolve_tools/meta_harness/config.yaml`; `evolve_tools/meta_harness/skills/meta-harness/SKILL.md`; `evolve_tools/meta_harness/logs/run_*/v*/<stream>/<candidate>/gpt-5/val.json`; `evolve_tools/src/runner.py`; `evolve_tools/src/ale_eval.py`; `reference/EnterpriseOps-Gym/conf/llm/gpt-5.json (model settings only)`

### tools / GEPA (`gepa`)

GEPA uses feedback from task attempts to improve prompt text. The selected prompt carries forward to the next stage.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5 | Recorded experiment setting |
| Optimization budget | 50 task evaluations per optimization stage, counted as GEPA metric calls | Recorded experiment setting |
| Tasks per feedback batch | 3 tasks | Recorded experiment setting |
| Optimization repetitions | 1 attempt per task for each candidate being evaluated | Recorded experiment setting |
| Prompt-improvement model | GPT-5 | Recorded experiment setting |
| Prompt-improvement response limit | 32,768 completion tokens per response, including reasoning tokens | Implementation default; original run setting unknown |
| Prompt-improvement request attempts | Up to 5 attempts per response: the initial request and at most 4 retries | Implementation default; original run setting unknown |
| Optimization parallelism | Up to 8 task attempts at once | Implementation default; original run setting unknown |
| Random seed for search sampling | 0 | Implementation default; original run setting unknown |
| Initial prompt | The provided task-solving prompt, before GEPA adds or edits guidance | Implementation default; original run setting unknown |
| Improvement rule | Accept an edit only when its total score on the sampled comparison batch exceeds its parent prompt’s score; reject ties | Implementation default; original run setting unknown |
| Candidate selection | Pareto selection: choose among prompts that lead on different validation tasks | Implementation default; original run setting unknown |
| Prompt-section selection | Edit one named section at a time, cycling through sections for each candidate (round-robin) | Implementation default; original run setting unknown |
| Combining candidate prompts | Disabled; sections from two parent prompts are not merged | Implementation default; original run setting unknown |
| Reusing cached evaluation results | Disabled; evaluate a repeated prompt and task again instead of reusing its prior score | Implementation default; original run setting unknown |
| EOG agent loop limit | 50 ReAct iterations per task | Implementation default; original run setting unknown |
| EOG model response token limit | 16,384 tokens per response | Recorded experiment setting |
| EOG sampling temperature | 0.1 | Recorded experiment setting |
| ALE task time limit | 7,200 seconds per task | Recorded configuration and implementation setting |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- One GEPA metric call evaluates one candidate on one task once. A batch of 3 tasks with 1 repetition uses 3 metric calls; it can contain many model requests and tool calls.
- The 50-call budget is a stopping threshold. Initial validation counts toward it, a final batch can exceed it, and request retries add compute.
- At each stage, validation includes tasks from Stage 1 through the current stage. Prompt improvement uses the current stage’s training tasks when continuing an adapted prompt; otherwise it uses training tasks from all stages seen so far.
- An edit that improves the sampled comparison batch can still reduce full-validation or held-out performance. The random seed controls search sampling; it is separate from the starting prompt.
- GEPA counts task evaluations, whereas Meta-Harness counts proposal rounds. These budgets do not establish equal model usage, elapsed time, or monetary cost across methods.
- The total optimization token or monetary budget and original parallel-task limit were not reported. The 3 held-out evaluation repetitions do not represent 3 independent optimization runs.

Sources: `analysis/arms.py`; `analysis/cache/cells_tools.tsv`; `evolve_tools/src/scripts/run_gepa.sh`; `evolve_tools/meta_harness/run_gepa.py`; `evolve_tools/meta_harness/gepa_reflection.py`; `evolve_tools/meta_harness/splits.py`; `evolve_tools/jobs/cumulative_tools_gepa_cumulative_val/<stream>/run_*/v*/search.json`; `evolve_tools/src/runner.py`; `evolve_tools/src/ale_eval.py`; `reference/EnterpriseOps-Gym/conf/llm/gpt-5.json (model settings only)`

### tools / Codex (ALE, V) (`react-ale-v`)

Deployment baseline that receives the capabilities introduced up to the current stage. Its prompt and agent program are not optimized between stages.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5 | Recorded experiment setting |
| Optimization between stages | None | Experiment design |
| Available capabilities | All capabilities introduced through the selected stage | Reported experiment setting |
| ALE task time limit | 7,200 seconds per task | Recorded configuration and implementation setting |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- This is the ALE deployment baseline used for comparison with the tool-memory methods. Its results are reported separately from the other ReAct / Codex deployment experiment.

Sources: `analysis/arms.py`; `analysis/cache/cells_tools.tsv`; `evolve_tools/src/runner.py`; `evolve_tools/src/ale_eval.py`; `reference/EnterpriseOps-Gym/conf/llm/gpt-5.json (model settings only)`

### tools / Raw memory (`raw-memory`)

The system retains records of actions and results from training-task attempts across stages. The agent receives this memory alongside the tools introduced so far.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5 | Recorded experiment setting |
| What the memory stores | Records of actions and results from training-task attempts | Recorded experiment setting |
| ALE training repetitions | 1 attempt per training task in the available sample of stage records | Recorded sample; not verified for every stage |
| Candidate search | None; compute is spent on training-task attempts and creating memories | Implementation behavior |
| Memories supplied to an ALE task | The 10 most recent memories; setting the limit to 0 removes the cap | Implementation default; original run setting unknown |
| EOG agent loop limit | 50 ReAct iterations per task | Implementation default; original run setting unknown |
| EOG model response token limit | 16,384 tokens per response | Implementation default; original run setting unknown |
| EOG sampling temperature | 0.1 | Implementation default; original run setting unknown |
| ALE task time limit | 7,200 seconds per task | Recorded configuration and implementation setting |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- Some EOG experiments contain 8 evaluation repetitions. These results use repetitions 1–3 for consistency with the other systems.
- The separately listed Codex (ALE, V) system is the deployment baseline used for comparison with these memory methods on ALE.
- The total token usage and monetary cost of building memory were not reported. Held-out evaluation usage excludes that work.

Sources: `analysis/arms.py`; `analysis/cache/cells_tools.tsv`; `external/evolving-mas-benchmark/evolve_tools/src/memory.py`; `external/evolving-mas-benchmark/evolve_tools/src/reasoning_induction.py`; `external/evolving-mas-benchmark/evolve_tools/src/scripts/frequent_config/gpt5_evolve_ale_cumulative_tool_memory.sh`; `evolve_tools/src/runner.py`; `evolve_tools/src/ale_eval.py`; `reference/EnterpriseOps-Gym/conf/llm/gpt-5.json (model settings only)`

### tools / Reasoning bank (`reasoning-bank`)

The system retains reasoning guidance generated from training-task attempts across stages. The agent receives this memory alongside the tools introduced so far.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5 | Recorded experiment setting |
| What the memory stores | Reasoning guidance generated from training-task attempts | Recorded experiment setting |
| ALE training repetitions | 1 attempt per training task in the available sample of stage records | Recorded sample; not verified for every stage |
| Candidate search | None; compute is spent on training-task attempts and creating memories | Implementation behavior |
| Memory generation and retrieval limits | The original experiment’s limits were not reported | Not reported |
| EOG agent loop limit | 50 ReAct iterations per task | Implementation default; original run setting unknown |
| EOG model response token limit | 16,384 tokens per response | Implementation default; original run setting unknown |
| EOG sampling temperature | 0.1 | Implementation default; original run setting unknown |
| ALE task time limit | 7,200 seconds per task | Recorded configuration and implementation setting |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- Some EOG experiments contain 8 evaluation repetitions. These results use repetitions 1–3 for consistency with the other systems.
- The separately listed Codex (ALE, V) system is the deployment baseline used for comparison with these memory methods on ALE.
- The total token usage and monetary cost of building memory were not reported. Held-out evaluation usage excludes that work.

Sources: `analysis/arms.py`; `analysis/cache/cells_tools.tsv`; `external/evolving-mas-benchmark/evolve_tools/src/memory.py`; `external/evolving-mas-benchmark/evolve_tools/src/reasoning_induction.py`; `external/evolving-mas-benchmark/evolve_tools/src/scripts/frequent_config/gpt5_evolve_ale_cumulative_tool_adapt_fwd_reasoning.sh`; `evolve_tools/src/runner.py`; `evolve_tools/src/ale_eval.py`; `reference/EnterpriseOps-Gym/conf/llm/gpt-5.json (model settings only)`

### tools / MemToolAgent (`memtoolagent`)

The system retains written reflections on training-task attempts across stages. The agent receives this memory alongside the tools introduced so far.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5 | Recorded experiment setting |
| What the memory stores | Written reflections on training-task attempts | Recorded experiment setting |
| ALE training repetitions | 1 attempt per training task in the available sample of stage records | Recorded sample; not verified for every stage |
| Candidate search | None; compute is spent on training-task attempts and creating memories | Implementation behavior |
| Memories supplied to an ALE task | The 10 most recent memories; setting the limit to 0 removes the cap | Implementation default; original run setting unknown |
| EOG agent loop limit | 50 ReAct iterations per task | Implementation default; original run setting unknown |
| EOG model response token limit | 16,384 tokens per response | Implementation default; original run setting unknown |
| EOG sampling temperature | 0.1 | Implementation default; original run setting unknown |
| ALE task time limit | 7,200 seconds per task | Recorded configuration and implementation setting |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- Some EOG experiments contain 8 evaluation repetitions. These results use repetitions 1–3 for consistency with the other systems.
- The separately listed Codex (ALE, V) system is the deployment baseline used for comparison with these memory methods on ALE.
- The total token usage and monetary cost of building memory were not reported. Held-out evaluation usage excludes that work.

Sources: `analysis/arms.py`; `analysis/cache/cells_tools.tsv`; `external/evolving-mas-benchmark/evolve_tools/src/memory.py`; `external/evolving-mas-benchmark/evolve_tools/src/reasoning_induction.py`; `external/evolving-mas-benchmark/evolve_tools/src/scripts/frequent_config/gpt5_evolve_ale_cumulative_tool_adapt_fwd_reflection.sh`; `evolve_tools/src/runner.py`; `evolve_tools/src/ale_eval.py`; `reference/EnterpriseOps-Gym/conf/llm/gpt-5.json (model settings only)`

### skills / Task-specific Codex (`oracle`)

Reference system given the capabilities selected for each task. It does not learn or retain experience between stages.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5 | Recorded experiment setting |
| Capabilities supplied to each task | The task’s designated skills and tools | Reported experiment setting |
| Optimization between stages | None; no prompt or agent-program search | Experiment design |
| EOG task time limit | 900 seconds in total for each task | Implementation default; original run setting unknown |
| EOG task continuation limit | Up to 4 episodes in total, including continuations, within the same task time limit; separate from evaluation repetitions | Implementation default; original run setting unknown |
| ALE task time limit | 7,200 seconds per task | Recorded configuration and implementation setting |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- Each stage result covers that stage’s held-out tasks only. The overall benchmark result combines tasks from all stages. No adaptation takes place between these evaluations.

Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`; `evovle_skills/src/config.py`; `evovle_skills/src/runner.py`

### skills / Task-specific Codex (gpt-5.5) (`oracle-gpt55`)

Reference system given the capabilities selected for each task. It does not learn or retain experience between stages.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5.5 | Recorded experiment setting |
| Capabilities supplied to each task | The task’s designated skills and tools | Reported experiment setting |
| Optimization between stages | None; no prompt or agent-program search | Experiment design |
| EOG task time limit | 900 seconds in total for each task | Implementation default; original run setting unknown |
| EOG task continuation limit | Up to 4 episodes in total, including continuations, within the same task time limit; separate from evaluation repetitions | Implementation default; original run setting unknown |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- Each stage result covers that stage’s held-out tasks only. The overall benchmark result combines tasks from all stages. No adaptation takes place between these evaluations.
- This EOG-only experiment, run on August 26, changes the task-solving model from GPT-5 to GPT-5.5. It reports the same agent communication protocol, local execution setup, parallel-task limit and task time limit as the GPT-5 reference.

Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`; `evovle_skills/src/config.py`; `evovle_skills/src/runner.py`

### skills / Task-specific Claude Code (`oracle-claude`)

Reference system given the capabilities selected for each task. It does not learn or retain experience between stages.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | Sonnet-4.6 | Reported experiment setting |
| Capabilities supplied to each task | The task’s designated skills and tools | Reported experiment setting |
| Optimization between stages | None; no prompt or agent-program search | Experiment design |
| EOG task time limit | 900 seconds per task | Recorded experiment setting |
| ALE task time limit | Not reported | Not reported |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- Each stage result covers that stage’s held-out tasks only. The overall benchmark result combines tasks from all stages. No adaptation takes place between these evaluations.
- Some EOG token-usage measurements come from 1 additional repetition run specifically to measure usage. Accuracy uses the original 3 evaluation repetitions. Missing token counts mean the reported usage may understate total cost.

Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`; `yang_li/results_final/README.md`

### skills / Claude Code (`claude`)

Deployment baseline that receives the capabilities introduced up to the current stage. Its prompt and agent program are not optimized between stages.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | Sonnet-4.6 | Reported experiment setting |
| Optimization between stages | None | Experiment design |
| Available capabilities | All capabilities introduced through the selected stage | Reported experiment setting |
| EOG task time limit | 900 seconds per task | Recorded experiment setting |
| ALE task time limit | Not reported | Not reported |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- Some EOG token-usage measurements come from 1 additional repetition run specifically to measure usage. Accuracy uses the original 3 evaluation repetitions. Missing token counts mean the reported usage may understate total cost.

Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`; `yang_li/results_final/README.md`

### skills / Codex (`codex`)

Deployment baseline that receives the capabilities introduced up to the current stage. Its prompt and agent program are not optimized between stages.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5 | Recorded experiment setting |
| Optimization between stages | None | Experiment design |
| Available capabilities | All capabilities introduced through the selected stage | Reported experiment setting |
| EOG task time limit | 900 seconds in total for each task | Implementation default; original run setting unknown |
| EOG task continuation limit | Up to 4 episodes in total, including continuations, within the same task time limit; separate from evaluation repetitions | Implementation default; original run setting unknown |
| ALE task time limit | 7,200 seconds per task | Recorded configuration and implementation setting |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |


Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`; `evovle_skills/src/config.py`; `evovle_skills/src/runner.py`

### skills / Codex Memory (`memory`)

Codex builds persistent memory from its attempts at training tasks. The memory carries forward between stages, and held-out tasks receive a copy of the memory learned so far.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5 | Recorded experiment setting |
| Training data | Training tasks from Stage 1 through the current stage; learned memory carries forward | Implementation behavior |
| EOG training parallelism | 1 training task at a time | Required by the current implementation; original run setting unknown |
| ALE training parallelism | Training tasks can run in parallel in separate environments; the experiment’s parallel-task limit was not reported | Not reported |
| Memory extraction time limit | 600 seconds per memory-extraction operation | Implementation default; original run setting unknown |
| Memory consolidation time limit | 900 seconds to combine extracted memories | Implementation default; original run setting unknown |
| Memory extraction parallelism | Up to 8 extraction operations at once | Implementation default; original run setting unknown |
| Candidate search | None; compute is spent on training-task attempts and memory processing | Implementation behavior |
| EOG task time limit | 900 seconds in total for each task | Implementation default; original run setting unknown |
| EOG task continuation limit | Up to 4 episodes in total, including continuations, within the same task time limit; separate from evaluation repetitions | Implementation default; original run setting unknown |
| ALE task time limit | 7,200 seconds per task | Recorded configuration and implementation setting |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- The original memory-processing settings and total training token usage or monetary cost were not reported. Held-out task attempts are kept separate from the memory used to train later stages.

Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`; `evovle_skills/src/scripts/run_cumulative_skill.py`; `evovle_agents/src/config.py:328`; `evovle_skills/src/config.py`; `evovle_skills/src/config.py`; `evovle_skills/src/runner.py`

### skills / Meta-Harness (`meta`)

Meta-Harness asks GPT-5 to edit the Python program that controls the agent and its learned state. The selected program and state carry forward between stages.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5 | Recorded experiment setting |
| Proposal rounds | 5 requested rounds per optimization stage | Configured experiment budget |
| Candidate programs requested | 3 per proposal round | Proposal instruction; completion not guaranteed |
| EOG candidate-validation repetitions | 3 attempts per validation task for each candidate | Recorded experiment setting |
| ALE candidate-validation repetitions | Per validation task, for each candidate: Stage 1: 3 attempts; Stage 2: 3 attempts; Stage 3: 3 attempts; Stage 4: 3 attempts; Stage 5: 3 attempts; Stage 6: 1 attempt | Recorded experiment setting |
| Program-proposal model | GPT-5 | Configured experiment setting |
| Proposal code-editing time limit | 2,400 seconds (40 minutes) per proposal round; candidate learning and validation take additional time | Configured experiment setting |
| Candidate learning method | Update the program’s learned state from training examples, then freeze that state for validation (offline learning) | Configured experiment setting |
| Training passes | 1 pass through the assigned training examples (1 epoch) | Configured experiment setting |
| Training batch size | 1 example per learning step | Configured experiment setting |
| Initial comparison programs | The unmodified agent program and a program given all training examples in its prompt; later stages also compare the previous stage’s winner | Implementation default; original run setting unknown |
| Optimization parallelism | Up to 8 task attempts at once | Implementation default; original run setting unknown |
| EOG task time limit | 900 seconds in total for each task | Implementation default; original run setting unknown |
| EOG task continuation limit | Up to 4 episodes in total, including continuations, within the same task time limit; separate from evaluation repetitions | Implementation default; original run setting unknown |
| ALE task time limit | 7,200 seconds per task | Recorded configuration and implementation setting |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- Each candidate is evaluated on the full validation set, using the repetition count shown for its stage. These validation attempts select the candidate; they are separate from the 3 repetitions used to report held-out results.
- Five proposal rounds requesting 3 candidates each do not guarantee 15 completed candidate evaluations. Some recorded stages stopped before completing the requested work.
- The implementation now defaults to 1 validation attempt per task throughout ALE. The recorded stage schedule above is the relevant setting for these results.
- Candidate learning changes program state, not model weights. It reads training examples without requiring the task-solving agent to attempt each training task, although the candidate’s learning code may make model requests.
- At each stage, validation includes tasks from Stage 1 through the current stage. Learning uses the current stage’s training examples when the previous stage’s learned state is successfully restored; otherwise it uses training examples from all stages seen so far.
- GEPA counts task evaluations, whereas Meta-Harness counts proposal rounds. These budgets do not establish equal model usage, elapsed time, or monetary cost across methods.
- The total optimization token or monetary budget and original parallel-task limit were not reported. The 3 held-out evaluation repetitions do not represent 3 independent optimization runs.

Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`; `evovle_skills/src/scripts/run_meta_harness.sh`; `evovle_skills/meta_harness/config.yaml`; `evovle_skills/meta_harness/skills/meta-harness/SKILL.md`; `evovle_skills/meta_harness/logs/run_*/v*/<stream>/<candidate>/gpt-5/val.json`; `evovle_skills/src/config.py`; `evovle_skills/src/runner.py`

### skills / GEPA (`gepa`)

GEPA uses feedback from task attempts to improve prompt text. The selected prompt carries forward to the next stage.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5 | Recorded experiment setting |
| Optimization budget | 50 task evaluations per optimization stage, counted as GEPA metric calls | Recorded experiment setting |
| Tasks per feedback batch | 3 tasks | Recorded experiment setting |
| Optimization repetitions | 1 attempt per task for each candidate being evaluated | Recorded experiment setting |
| Prompt-improvement model | GPT-5 | Recorded experiment setting |
| Prompt-improvement response limit | 32,768 completion tokens per response, including reasoning tokens | Implementation default; original run setting unknown |
| Prompt-improvement request attempts | Up to 5 attempts per response: the initial request and at most 4 retries | Implementation default; original run setting unknown |
| Optimization parallelism | Up to 8 task attempts at once | Implementation default; original run setting unknown |
| Random seed for search sampling | 0 | Implementation default; original run setting unknown |
| Initial prompt | The provided task-solving prompt, before GEPA adds or edits guidance | Implementation default; original run setting unknown |
| Improvement rule | Accept an edit only when its total score on the sampled comparison batch exceeds its parent prompt’s score; reject ties | Implementation default; original run setting unknown |
| Candidate selection | Pareto selection: choose among prompts that lead on different validation tasks | Implementation default; original run setting unknown |
| Prompt-section selection | Edit one named section at a time, cycling through sections for each candidate (round-robin) | Implementation default; original run setting unknown |
| Combining candidate prompts | Disabled; sections from two parent prompts are not merged | Implementation default; original run setting unknown |
| Reusing cached evaluation results | Disabled; evaluate a repeated prompt and task again instead of reusing its prior score | Implementation default; original run setting unknown |
| EOG task time limit | 900 seconds in total for each task | Implementation default; original run setting unknown |
| EOG task continuation limit | Up to 4 episodes in total, including continuations, within the same task time limit; separate from evaluation repetitions | Implementation default; original run setting unknown |
| ALE task time limit | 7,200 seconds per task | Recorded configuration and implementation setting |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- One GEPA metric call evaluates one candidate on one task once. A batch of 3 tasks with 1 repetition uses 3 metric calls; it can contain many model requests and tool calls.
- The 50-call budget is a stopping threshold. Initial validation counts toward it, a final batch can exceed it, and request retries add compute.
- At each stage, validation includes tasks from Stage 1 through the current stage. Prompt improvement uses the current stage’s training tasks when continuing an adapted prompt; otherwise it uses training tasks from all stages seen so far.
- An edit that improves the sampled comparison batch can still reduce full-validation or held-out performance. The random seed controls search sampling; it is separate from the starting prompt.
- GEPA counts task evaluations, whereas Meta-Harness counts proposal rounds. These budgets do not establish equal model usage, elapsed time, or monetary cost across methods.
- The total optimization token or monetary budget and original parallel-task limit were not reported. The 3 held-out evaluation repetitions do not represent 3 independent optimization runs.

Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`; `evovle_skills/src/scripts/run_gepa.sh`; `evovle_skills/meta_harness/run_gepa.py`; `evovle_skills/meta_harness/gepa_reflection.py`; `evovle_skills/meta_harness/splits.py`; `evovle_skills/jobs/cumulative_skill_gepa/<stream>/run_*/v*/search.json`; `evovle_skills/src/config.py`; `evovle_skills/src/runner.py`

### skills / Task-specific GEPA (eval on full library) (`gepa-oracle`)

GEPA uses feedback from task attempts to improve prompt text. The selected prompt carries forward to the next stage. This variant optimizes with the skills designated for each task, then evaluates with the full library available at that stage.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5 | Recorded experiment setting |
| Optimization budget | 50 task evaluations per optimization stage, counted as GEPA metric calls | Recorded experiment setting |
| Tasks per feedback batch | 3 tasks | Recorded experiment setting |
| Optimization repetitions | 1 attempt per task for each candidate being evaluated | Recorded experiment setting |
| Prompt-improvement model | GPT-5 | Recorded experiment setting |
| Prompt-improvement response limit | 32,768 completion tokens per response, including reasoning tokens | Implementation default; original run setting unknown |
| Prompt-improvement request attempts | Up to 5 attempts per response: the initial request and at most 4 retries | Implementation default; original run setting unknown |
| Optimization parallelism | Up to 8 task attempts at once | Implementation default; original run setting unknown |
| Random seed for search sampling | 0 | Implementation default; original run setting unknown |
| Initial prompt | The provided task-solving prompt, before GEPA adds or edits guidance | Implementation default; original run setting unknown |
| Improvement rule | Accept an edit only when its total score on the sampled comparison batch exceeds its parent prompt’s score; reject ties | Implementation default; original run setting unknown |
| Candidate selection | Pareto selection: choose among prompts that lead on different validation tasks | Implementation default; original run setting unknown |
| Prompt-section selection | Edit one named section at a time, cycling through sections for each candidate (round-robin) | Implementation default; original run setting unknown |
| Combining candidate prompts | Disabled; sections from two parent prompts are not merged | Implementation default; original run setting unknown |
| Reusing cached evaluation results | Disabled; evaluate a repeated prompt and task again instead of reusing its prior score | Implementation default; original run setting unknown |
| Skills supplied during optimization | Only the skills designated for each task | Recorded experiment setting |
| Skills supplied during held-out evaluation | Full final-stage library: CSM 9 skills, HR 10 skills, ITSM 10 skills | Recorded experiment setting |
| EOG task time limit | 900 seconds in total for each task | Implementation default; original run setting unknown |
| EOG task continuation limit | Up to 4 episodes in total, including continuations, within the same task time limit; separate from evaluation repetitions | Implementation default; original run setting unknown |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- One GEPA metric call evaluates one candidate on one task once. A batch of 3 tasks with 1 repetition uses 3 metric calls; it can contain many model requests and tool calls.
- The 50-call budget is a stopping threshold. Initial validation counts toward it, a final batch can exceed it, and request retries add compute.
- At each stage, validation includes tasks from Stage 1 through the current stage. Prompt improvement uses the current stage’s training tasks when continuing an adapted prompt; otherwise it uses training tasks from all stages seen so far.
- An edit that improves the sampled comparison batch can still reduce full-validation or held-out performance. The random seed controls search sampling; it is separate from the starting prompt.
- Held-out results are available only for the final stage: Stage 3 in CSM and HR, and Stage 4 in ITSM. Earlier optimization stages do not provide earlier held-out results. No ALE results are available for this variant.
- GEPA counts task evaluations, whereas Meta-Harness counts proposal rounds. These budgets do not establish equal model usage, elapsed time, or monetary cost across methods.
- The total optimization token or monetary budget and original parallel-task limit were not reported. The 3 held-out evaluation repetitions do not represent 3 independent optimization runs.

Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`; `evovle_skills/src/scripts/run_gepa.sh`; `evovle_skills/meta_harness/run_gepa.py`; `evovle_skills/meta_harness/gepa_reflection.py`; `evovle_skills/meta_harness/splits.py`; `evovle_skills/jobs/oracle_skills_gepa/<stream>/oracle_skills_gepa_*/v*/search.json`; `evovle_skills/src/config.py`; `evovle_skills/src/runner.py`

### skills / SkillOpt (`skillopt`)

SkillOpt uses GPT-5.5 with the EOG skills introduced through the current stage. Its task-solving model differs from the GPT-5 baselines.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5.5 | Reported experiment setting |
| Optimization budget | Not reported for this experiment | Not reported |
| Task time limit | Not reported | Not reported |
| Parallel task limit | Not reported | Not reported |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- Results are available for EOG only. Task durations were not reported; unavailable timing must not be interpreted as zero cost.

Sources: `analysis/arms.py`; `analysis/cache/cells_skills.tsv`

### agents / Task-specific Codex (`oracle`)

Reference system given the stage’s specialist library on EOG and the task’s designated specialist groups on ALE. It does not learn between stages.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | EOG: gpt-5-codex; ALE: gpt-5 | Recorded experiment setting |
| Specialist agents supplied | EOG: the reference specialist library for that stage. ALE: the specialist groups designated for each task. | EOG: recorded experiment setting; ALE: implementation behavior |
| Optimization between stages | None; no prompt or agent-program search | Experiment design |
| EOG task time limit | 900 seconds in total for each task | Implementation default; original run setting unknown |
| EOG task continuation limit | Up to 4 episodes in total, including continuations, within the same task time limit; separate from evaluation repetitions | Implementation default; original run setting unknown |
| ALE task time limit | 7,200 seconds per task | Recorded configuration and implementation setting |
| Agent thread limit | 12 concurrent agent threads | Recorded base setting and implementation default |
| Delegation depth limit | 1 level of specialist delegation below the lead agent | Recorded base setting and implementation default |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- Each stage result covers that stage’s held-out tasks only. The overall benchmark result combines tasks from all stages. No adaptation takes place between these evaluations.
- On EOG, tasks from the same stage receive the same specialist library even when their designated tools differ.
- The delegation limits describe the base Codex configuration. A program produced by optimization may change how agents are coordinated.

Sources: `analysis/arms.py`; `analysis/cache/cells_agents.tsv`; `evovle_agents/src/config.py`; `evovle_agents/src/runner.py`

### agents / Task-specific Claude Code (`oracle-claude`)

Reference system given the capabilities selected for each task. It does not learn or retain experience between stages.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | Sonnet-4.6 | Reported experiment setting |
| Capabilities supplied to each task | The task’s designated specialist agents | Reported experiment setting |
| Optimization between stages | None; no prompt or agent-program search | Experiment design |
| EOG task time limit | 900 seconds per task | Recorded experiment setting |
| ALE task time limit | Not reported | Not reported |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- Each stage result covers that stage’s held-out tasks only. The overall benchmark result combines tasks from all stages. No adaptation takes place between these evaluations.
- Some EOG token-usage measurements come from 1 additional repetition run specifically to measure usage. Accuracy uses the original 3 evaluation repetitions. Missing token counts mean the reported usage may understate total cost.

Sources: `analysis/arms.py`; `analysis/cache/cells_agents.tsv`; `yang_li/results_final/README.md`

### agents / Codex (`codex`)

Deployment baseline that receives the capabilities introduced up to the current stage. Its prompt and agent program are not optimized between stages.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | EOG: gpt-5-codex; ALE: gpt-5 | Recorded experiment setting |
| Optimization between stages | None | Experiment design |
| Available capabilities | All capabilities introduced through the selected stage | Reported experiment setting |
| EOG task time limit | 900 seconds in total for each task | Implementation default; original run setting unknown |
| EOG task continuation limit | Up to 4 episodes in total, including continuations, within the same task time limit; separate from evaluation repetitions | Implementation default; original run setting unknown |
| ALE task time limit | 7,200 seconds per task | Recorded configuration and implementation setting |
| Agent thread limit | 12 concurrent agent threads | Recorded base setting and implementation default |
| Delegation depth limit | 1 level of specialist delegation below the lead agent | Recorded base setting and implementation default |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- The delegation limits describe the base Codex configuration. A program produced by optimization may change how agents are coordinated.

Sources: `analysis/arms.py`; `analysis/cache/cells_agents.tsv`; `evovle_agents/src/config.py`; `evovle_agents/src/runner.py`

### agents / Claude Code (`claude`)

Deployment baseline that receives the capabilities introduced up to the current stage. Its prompt and agent program are not optimized between stages.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | Sonnet-4.6 | Reported experiment setting |
| Optimization between stages | None | Experiment design |
| Available capabilities | All capabilities introduced through the selected stage | Reported experiment setting |
| EOG task time limit | 900 seconds per task | Recorded experiment setting |
| ALE task time limit | Not reported | Not reported |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- Some EOG token-usage measurements come from 1 additional repetition run specifically to measure usage. Accuracy uses the original 3 evaluation repetitions. Missing token counts mean the reported usage may understate total cost.

Sources: `analysis/arms.py`; `analysis/cache/cells_agents.tsv`; `yang_li/results_final/README.md`

### agents / Codex Memory (`memory`)

Codex builds persistent memory from its attempts at training tasks. The memory carries forward between stages, and held-out tasks receive a copy of the memory learned so far.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5 | Recorded experiment setting |
| Training data | Training tasks from Stage 1 through the current stage; learned memory carries forward | Implementation behavior |
| EOG training parallelism | 1 training task at a time | Required by the current implementation; original run setting unknown |
| ALE training parallelism | Training tasks can run in parallel in separate environments; the experiment’s parallel-task limit was not reported | Not reported |
| Memory extraction time limit | 600 seconds per memory-extraction operation | Implementation default; original run setting unknown |
| Memory consolidation time limit | 900 seconds to combine extracted memories | Implementation default; original run setting unknown |
| Memory extraction parallelism | Up to 8 extraction operations at once | Implementation default; original run setting unknown |
| Candidate search | None; compute is spent on training-task attempts and memory processing | Implementation behavior |
| EOG task time limit | 900 seconds in total for each task | Implementation default; original run setting unknown |
| EOG task continuation limit | Up to 4 episodes in total, including continuations, within the same task time limit; separate from evaluation repetitions | Implementation default; original run setting unknown |
| ALE task time limit | 7,200 seconds per task | Recorded configuration and implementation setting |
| Agent thread limit | 12 concurrent agent threads | Recorded base setting and implementation default |
| Delegation depth limit | 1 level of specialist delegation below the lead agent | Recorded base setting and implementation default |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- The original memory-processing settings and total training token usage or monetary cost were not reported. Held-out task attempts are kept separate from the memory used to train later stages.
- The delegation limits describe the base Codex configuration. A program produced by optimization may change how agents are coordinated.

Sources: `analysis/arms.py`; `analysis/cache/cells_agents.tsv`; `evovle_agents/src/scripts/run_cumulative_agents.py`; `evovle_agents/src/config.py:328`; `evovle_agents/src/config.py`; `evovle_agents/src/config.py`; `evovle_agents/src/runner.py`

### agents / Meta-Harness (`meta`)

Meta-Harness asks GPT-5 to edit the Python program that controls the agent and its learned state. The selected program and state carry forward between stages.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5 | Recorded experiment setting |
| Proposal rounds | 5 requested rounds per optimization stage | Configured experiment budget |
| Candidate programs requested | 3 per proposal round | Proposal instruction; completion not guaranteed |
| EOG candidate-validation repetitions | 3 attempts per validation task for each candidate | Recorded experiment setting |
| ALE candidate-validation repetitions | Per validation task, for each candidate: Stage 1: 3 attempts; Stage 2: 3 attempts; Stage 3: 3 attempts; Stage 4: 3 attempts; Stage 5: 1 attempt; Stage 6: 1 attempt | Recorded experiment setting |
| Program-proposal model | GPT-5 | Configured experiment setting |
| Proposal code-editing time limit | 2,400 seconds (40 minutes) per proposal round; candidate learning and validation take additional time | Configured experiment setting |
| Candidate learning method | Update the program’s learned state from training examples, then freeze that state for validation (offline learning) | Configured experiment setting |
| Training passes | 1 pass through the assigned training examples (1 epoch) | Configured experiment setting |
| Training batch size | 1 example per learning step | Configured experiment setting |
| Initial comparison programs | The unmodified agent program and a program given all training examples in its prompt; later stages also compare the previous stage’s winner | Implementation default; original run setting unknown |
| Optimization parallelism | Up to 8 task attempts at once | Implementation default; original run setting unknown |
| EOG task time limit | 900 seconds in total for each task | Implementation default; original run setting unknown |
| EOG task continuation limit | Up to 4 episodes in total, including continuations, within the same task time limit; separate from evaluation repetitions | Implementation default; original run setting unknown |
| ALE task time limit | 7,200 seconds per task | Recorded configuration and implementation setting |
| Agent thread limit | 12 concurrent agent threads | Recorded base setting and implementation default |
| Delegation depth limit | 1 level of specialist delegation below the lead agent | Recorded base setting and implementation default |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- Each candidate is evaluated on the full validation set, using the repetition count shown for its stage. These validation attempts select the candidate; they are separate from the 3 repetitions used to report held-out results.
- Five proposal rounds requesting 3 candidates each do not guarantee 15 completed candidate evaluations. Some recorded stages stopped before completing the requested work.
- The implementation now defaults to 1 validation attempt per task throughout ALE. The recorded stage schedule above is the relevant setting for these results.
- Candidate learning changes program state, not model weights. It reads training examples without requiring the task-solving agent to attempt each training task, although the candidate’s learning code may make model requests.
- At each stage, validation includes tasks from Stage 1 through the current stage. Learning uses the current stage’s training examples when the previous stage’s learned state is successfully restored; otherwise it uses training examples from all stages seen so far.
- GEPA counts task evaluations, whereas Meta-Harness counts proposal rounds. These budgets do not establish equal model usage, elapsed time, or monetary cost across methods.
- The total optimization token or monetary budget and original parallel-task limit were not reported. The 3 held-out evaluation repetitions do not represent 3 independent optimization runs.
- The delegation limits describe the base Codex configuration. A program produced by optimization may change how agents are coordinated.

Sources: `analysis/arms.py`; `analysis/cache/cells_agents.tsv`; `evovle_agents/src/scripts/run_meta_harness.sh`; `evovle_agents/meta_harness/config.yaml`; `evovle_agents/meta_harness/skills/meta-harness/SKILL.md`; `evovle_agents/meta_harness/logs/run_*/v*/<stream>/<candidate>/gpt-5/val.json`; `evovle_agents/src/config.py`; `evovle_agents/src/runner.py`

### agents / GEPA (`gepa`)

GEPA uses feedback from task attempts to improve prompt text. The selected prompt carries forward to the next stage.

| Setting | Value | Evidence |
|---|---|---|
| Task-solving model | GPT-5 | Recorded experiment setting |
| Optimization budget | 50 task evaluations per optimization stage, counted as GEPA metric calls | Recorded experiment setting |
| Tasks per feedback batch | 3 tasks | Recorded experiment setting |
| Optimization repetitions | 1 attempt per task for each candidate being evaluated | Recorded experiment setting |
| Prompt-improvement model | GPT-5 | Recorded experiment setting |
| Prompt-improvement response limit | 32,768 completion tokens per response, including reasoning tokens | Implementation default; original run setting unknown |
| Prompt-improvement request attempts | Up to 5 attempts per response: the initial request and at most 4 retries | Implementation default; original run setting unknown |
| Optimization parallelism | Up to 8 task attempts at once | Implementation default; original run setting unknown |
| Random seed for search sampling | 0 | Implementation default; original run setting unknown |
| Initial prompt | The provided task-solving prompt, before GEPA adds or edits guidance | Implementation default; original run setting unknown |
| Improvement rule | Accept an edit only when its total score on the sampled comparison batch exceeds its parent prompt’s score; reject ties | Implementation default; original run setting unknown |
| Candidate selection | Pareto selection: choose among prompts that lead on different validation tasks | Implementation default; original run setting unknown |
| Prompt-section selection | Edit one named section at a time, cycling through sections for each candidate (round-robin) | Implementation default; original run setting unknown |
| Combining candidate prompts | Disabled; sections from two parent prompts are not merged | Implementation default; original run setting unknown |
| Reusing cached evaluation results | Disabled; evaluate a repeated prompt and task again instead of reusing its prior score | Implementation default; original run setting unknown |
| EOG task time limit | 900 seconds in total for each task | Implementation default; original run setting unknown |
| EOG task continuation limit | Up to 4 episodes in total, including continuations, within the same task time limit; separate from evaluation repetitions | Implementation default; original run setting unknown |
| ALE task time limit | 7,200 seconds per task | Recorded configuration and implementation setting |
| Agent thread limit | 12 concurrent agent threads | Recorded base setting and implementation default |
| Delegation depth limit | 1 level of specialist delegation below the lead agent | Recorded base setting and implementation default |
| Held-out evaluation repetitions | 3 runs for each evaluated combination of stream, system stage, and task group; each task is attempted once per run | Recorded experiment setting |
| Total experiment compute | Not reported; held-out evaluation usage excludes training, memory building and optimization | Not reported |

- One GEPA metric call evaluates one candidate on one task once. A batch of 3 tasks with 1 repetition uses 3 metric calls; it can contain many model requests and tool calls.
- The 50-call budget is a stopping threshold. Initial validation counts toward it, a final batch can exceed it, and request retries add compute.
- At each stage, validation includes tasks from Stage 1 through the current stage. Prompt improvement uses the current stage’s training tasks when continuing an adapted prompt; otherwise it uses training tasks from all stages seen so far.
- An edit that improves the sampled comparison batch can still reduce full-validation or held-out performance. The random seed controls search sampling; it is separate from the starting prompt.
- GEPA counts task evaluations, whereas Meta-Harness counts proposal rounds. These budgets do not establish equal model usage, elapsed time, or monetary cost across methods.
- The total optimization token or monetary budget and original parallel-task limit were not reported. The 3 held-out evaluation repetitions do not represent 3 independent optimization runs.
- The delegation limits describe the base Codex configuration. A program produced by optimization may change how agents are coordinated.

Sources: `analysis/arms.py`; `analysis/cache/cells_agents.tsv`; `evovle_agents/src/scripts/run_gepa.sh`; `evovle_agents/meta_harness/run_gepa.py`; `evovle_agents/meta_harness/gepa_reflection.py`; `evovle_agents/meta_harness/splits.py`; `evovle_agents/jobs/cumulative_agents_gepa/<stream>/run_*/v*/search.json`; `evovle_agents/src/config.py`; `evovle_agents/src/runner.py`
