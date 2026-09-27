# Reproducing the baseline results

## 1. Reconstruct the archived numbers (complete, offline)

Download `reproducibility-kit.zip` from the leaderboard, extract it, and run:

```sh
cd evoharness-baselines
python3 verify_results.py
```

Requires Python 3.10 or newer and its standard library. This operation uses no API, network, benchmark runtime, credentials, or source checkout. It verifies SHA-256 checksums, task/run identities, filtering, exact run numerators, all 1,346 matrix cells, 518 stage summaries and 46 benchmark aggregates for all 25 registered experiments. A nonzero exit means a missing artifact or inconsistency.

The ZIP contains a lossless export of each cached task’s score/success flag, the exact task IDs retained in each cell/run, configuration and rerun notes, all result CSVs, data.json, provenance, historical exclusions and the checker. Individual scores in the source cache have six-decimal precision; exact sums here mean sums of those cached values, not full-precision original outcomes. Original prompts, environments, trajectories and trained harness checkpoints are not in the kit.

`search-stage-evidence.json` provides 150 search-stage records for GEPA/Meta-Harness and oracle-skills GEPA: recorded train/validation counts, repetition schedules, requested budgets, retained work, available validation task IDs, checkpoint locations and hashes. The exporter verifies every supplied artifact hash against the source checkout. Multiple task counts can reflect different retained candidates or fallback training sets; they are not independent run counts. All 37 tools Meta-Harness lineage entries require the explicit recorded_path → path remapping documented there, in a copied lineage tree before archived reevaluation.

### Metric definitions and denominators

For each run r, Score = 100 × sum(task score)/number of recorded tasks and Pass = 100 × sum(recorded binary success)/number of recorded tasks. The displayed value is the equally weighted mean of runs 1, 2, 3; SD = sqrt(mean((run value − mean)²)), with population denominator 3. Pass uses the recorded success flag, not an invented threshold on rounded Score.

For R[k,j], k is the available harness stage and j the evaluated cohort. A cumulative stage summary pools recorded tasks from j ≤ k within each run. Forward cells j > k are shown separately. A task-specific control evaluates only cohort j with its selected capabilities; its stage points do not accumulate cohorts. Benchmark headlines pool each cumulative stream’s final recorded stage, or all cohort-only control cells. No averaging across EOG and ALE is performed here.

Failures with recorded zero scores remain in the denominator. Missing records are not invented or zero-filled; unequal counts are retained. No September filters are applied to these August caches. The per-task CSVs, rather than a union of task names or the exclusion file alone, define the exact cohort/run membership. A fresh ALE run also needs the historical Linux-supported task selection (`reference/agents-last-exam/selected_tasks/docker_support.txt`) as well as the environment-failure exclusions and cohort/split manifests. Some EOG source sweeps have eight runs; only runs 1–3 are included here.

Known coverage differences: tools/meta-harness Hybrid R[1,1] has 15/24/24 tasks; agents/meta-harness ALE R[5,6] has 7/8/7 tasks (a forward cell). Tools/oracle counts the additional EOG task `task_20251205_154853_044_d4a463c3_fce76046`, yielding 455 rather than 454 tasks. Skills/gepa-oracle has final-stage results only: CSM/HR v3, ITSM v4. Earlier search stages are not earlier held-out measurements.

Three published-row differences remain explicit: tools/oracle EOG; tools/react ALE (the website headline matches react-ale-v); agents/memory ALE. The archive does not silently alter the paper’s ranking.

### What the checker establishes

It establishes that the downloadable task outcomes reproduce the published archive and their checksums. The exporter also checked those outcomes against the repository’s cached cell tables. It does not independently replay the original trajectories, confirm the task verifiers by execution, or prove that source/runtime versions match August.

## 2. Rerun the experiments (additional artifacts required)

A full historical rerun cannot currently be guaranteed for every arm. The recipe for each arm below records source-supported entrypoints and explicit settings, and lists missing artifacts. Commands are templates from the inspected current source; they are not recovered historical shell histories and have not been executed as new benchmark runs. An LLM rerun can vary even with the same setup.

Obtain the experiment source/data checkout and the separate external checkout where named. Source locations in configuration JSONs are repository-relative; they are not public download URLs. This website kit does not bundle the benchmark runtimes, EOG databases, ALE task environments or trained harness checkpoints. Configure your own model/service credentials privately. Use fresh output roots or isolated checkouts, never the archived result directories.

Before comparing methods, freeze task IDs and train/validation/test split, per-stage capability pools, solver and proposer model snapshots, candidate-search budget, validation repeats, evaluation repeats, timeout/retry/concurrency policy, initial and inherited state, and source/dependency/container versions. Unknown historical values must remain unknown; a current default is not evidence that the August run used it. Current source hashes are in provenance.json, labeled as current inspection evidence.

GEPA’s metric-call limit and Meta-Harness’s proposer iterations are different units. Neither establishes equal compute. Report adaptation/search episodes, proposer/reflection tokens, retries and evaluation spend separately. CSV usage is evaluation telemetry only and can be incomplete; it is not a complete training/search budget.

## Per-experiment rerun recipes

### tools-oracle — Task-specific ReAct/Codex

Historical rerun status: **partial**.

Prerequisites:

- Use a complete experiment-source checkout, not the static website. Set REPRO_SOURCE to its root.
- Set REPRO_RUN_ID to a fresh directory-safe run identifier and REPRO_CONCURRENCY to an explicit positive integer. The template concurrency is a new-run choice; historical overrides are unknown.
- For EOG: run the EnterpriseOps-Gym MCP/SQL services from reference/EnterpriseOps-Gym and preserve their dataset/database seeds; install/authenticate Codex CLI with access to the requested model.
- Make eval_service/sdk importable (the launch scripts set PYTHONPATH); install its declared dependencies. The inspected runner documentation requires httpx, with datasets when reloading Hugging Face data.
- For ALE: obtain reference/agents-last-exam, use its Python >=3.12 environment and dependency lock (uv sync), and provision the Docker/cloud environment with the same task image and guard assets. Configure credentials privately through ALE_SECRET_FILE; never copy archived credentials.
- Set REPRO_DATA_ROOT to the archived evovling_tools data and REPRO_OUTPUT_ROOT to a new empty directory. For the current EOG SDK path, install/use the matching eval_service and supply your own credentials.

**Local ALE oracle template**

```sh
cd "${REPRO_SOURCE:?}"
ALE_MODEL=gpt-5 ALE_WALL_TIME_S=7200 PYTHONPATH="${REPRO_SOURCE:?}/eval_service/sdk:${REPRO_SOURCE:?}${PYTHONPATH:+:$PYTHONPATH}" \
  python -m evolve_tools.src.run_oracle_evolving \
  --dataset ale --backend local --data_root "${REPRO_DATA_ROOT:?}" \
  --domain ale --model gpt-5 --ale_mode oracle --num_runs 3 \
  --concurrency "${REPRO_CONCURRENCY:?}" --output_root "${REPRO_OUTPUT_ROOT:?}"
```

Current local ALE template. Restricts each task to its oracle tool/software set and evaluates the diagonal only. Full source/data/environment setup is required.

Missing information / conditions:

- The archived launcher command, full environment overrides, exact dependency lock and historical source revision were not preserved in the exported evaluation snapshot.
- A fresh live-model run is stochastic. Matching its protocol does not guarantee the same scores; use the downloadable trial/cell data to reproduce the archived arithmetic.
- Obtain the versioned task splits, capability libraries, original verifier/environment assets and archived task-exclusion manifest before running; current datasets/manifests may differ.
- The local experiment worktree has no Git HEAD commit; no immutable historical code revision could be established. A source-file checksum identifies the inspected current file only.
- The current tools oracle entry point routes EOG through the hosted SDK and rejects --backend local for EOG. Its source comment refers to a local --mode oracle flag that does not exist in current runner.py; no misleading local EOG command is supplied. Recover the archived oracle EOG runner/launcher or validate a pinned hosted equivalent.
- Current hosted EOG preset limits must be verified against the archived ReAct model/config before treating it as equivalent.

Evidence: `analysis/arms.py`; `evolve_tools/src/run_oracle_evolving.py`; `evolve_tools/src/scripts/gpt5_oracle_evoving_tools.sh`; `evolve_tools/src/runner.py`

### tools-react — ReAct/Codex

Historical rerun status: **partial**.

Prerequisites:

- Use the exact source tree named in the evidence. The external/evolving-mas-benchmark prefix denotes Vaidehi’s separate checkout; it is not interchangeable with the main experiment source.
- Set REPRO_SOURCE to that checkout, REPRO_DATA_ROOT to the frozen evovling_tools dataset, REPRO_OUTPUT_ROOT to a new empty output directory, REPRO_DOMAIN to the desired stream, and REPRO_CONCURRENCY explicitly.
- Create REPRO_LLM_CONFIG as a private provider configuration with openai/gpt-5, max_tokens 16384 and temperature 0.1; use your own credentials. The original file must not be copied because it can contain secrets.
- EOG requires the matching EnterpriseOps-Gym source/dependencies and running MCP/SQL services. ALE requires the matching agents-last-exam checkout, locked Python >=3.12 environment, Docker/task images, software guard and your own secret file.
- This registry arm combines external EOG runs and the main-source local ALE run. Its ALE results differ from the separate tools-react-ale-v control; do not combine their raw trials.

**Local ALE cumulative deployment template**

```sh
cd "${REPRO_SOURCE:?}"
ALE_MODEL=gpt-5 ALE_WALL_TIME_S=7200 python -m evolve_tools.src.runner_evolving_tools \
  --data_root "${REPRO_DATA_ROOT:?}" --domain ale --dataset ale \
  --llm_config "${REPRO_LLM_CONFIG:?}" --output_dir "${REPRO_OUTPUT_ROOT:?}" \
  --memory_mode none --runs_per_stage 3 --concurrency "${REPRO_CONCURRENCY:?}"
```

Use the main experiment source for this ALE template. The model override is supported here. It fills the lower-triangular cumulative matrix.

**External EOG deployment template**

```sh
cd "${REPRO_EXTERNAL_SOURCE:?}"
python -m evolve_tools.src.runner_evolving_tools \
  --data_root "${REPRO_DATA_ROOT:?}" --domain "${REPRO_DOMAIN:?}" --dataset eog \
  --llm_config "${REPRO_LLM_CONFIG:?}" --output_dir "${REPRO_OUTPUT_ROOT:?}" \
  --memory_mode none --runs_per_stage 3 --concurrency "${REPRO_CONCURRENCY:?}"
```

Current external source template for one EOG stream. Historical overrides and the exact revision that generated all archived cells were not preserved.

Missing information / conditions:

- The archived launcher command, full environment overrides, exact dependency lock and historical source revision were not preserved in the exported evaluation snapshot.
- A fresh live-model run is stochastic. Matching its protocol does not guarantee the same scores; use the downloadable trial/cell data to reproduce the archived arithmetic.
- Obtain the versioned task splits, capability libraries, original verifier/environment assets and archived task-exclusion manifest before running; current datasets/manifests may differ.
- The local experiment worktree has no Git HEAD commit; no immutable historical code revision could be established. A source-file checksum identifies the inspected current file only.
- The external checkout currently has HEAD aef27e4802f7c64dcd591844e6858bcdcdb7da44 plus uncommitted modifications to runner_evolving_tools.py, runner.py, memory.py, reasoning_induction.py, ale_eval.py and metrics.py. This is not an archived run commit or a reproducible source pin.
- Two source trees are required for this registry entry. Archived EOG and ALE run configurations must both be recovered before claiming an exact rerun.

Evidence: `analysis/arms.py`; `evolve_tools/src/runner_evolving_tools.py`; `evolve_tools/src/ale_eval.py`; `external/evolving-mas-benchmark/evolve_tools/src/runner_evolving_tools.py`

### tools-meta-harness — Meta-Harness

Historical rerun status: **partial**.

Prerequisites:

- Obtain the experiment source, benchmark task data and frozen capability libraries. Website CSVs can recompute reported aggregates but cannot execute an agent.
- Follow install.md for local EOG gyms, Docker connectivity, Codex CLI authentication and Python environments. Authenticate with your own credentials; never reuse or publish saved authentication files.
- Run namespace packages from the repository root. scripts/env.sh adds the root, eval_service/sdk (simple_agentic_evals), and reference/gepa/src to PYTHONPATH. Install the reference project dependencies instead of substituting another GEPA version.
- EOG requires the reference EnterpriseOps-Gym runtime and its domain gym containers. Tools also require its ReAct/LangChain stack. Verify gym endpoints before spending the search budget.
- ALE requires the reference/agents-last-exam Python 3.12 environment, gated task-data including grading references, a Linux sandbox image and the historical task eligibility/exclusion snapshot. A current manifest can change the denominator.
- Freeze source, dependency locks, Python/Codex/Node versions, container digests, model identifiers, task/split manifests and library hashes. Current source fingerprints do not identify the historical runtime.

**Prepare an isolated run**

```sh
# Run from a prepared writable experiment checkout, not the website.
set -euo pipefail
test -f scripts/env.sh
source scripts/env.sh
# Retain this tag for resume; use a new tag for each independent search.
export REPRO_TAG="$(date -u +%Y%m%d_%H%M%S)_$$"
export REPRO_RESULTS="$PWD/reproduction/$REPRO_TAG"
mkdir -p "$REPRO_RESULTS"
export EVOVLE_CODEX_MODEL=gpt-5
export EVOVLE_CODEX_TRANSPORT=stdio
export EVOVLE_CODEX_TIMEOUT_SEC=900
export EVOVLE_CODEX_MAX_EPISODES=4
export ALE_WALL_TIME_S=7200
export META_HARNESS_BACKEND=local
export META_HARNESS_CONCURRENCY=8
unset EVOVLE_SKILLS_JOBS_ARM_DIR EVOVLE_AGENTS_JOBS_ARM_DIR
```

New run using inspected current source. EOG timeout 900 seconds, four episodes, stdio transport and concurrency eight are explicit current settings, not established historical overrides. Append --dry-run to a search command to inspect its plan once prerequisites exist; preparation files may still be written. Recipes were source-checked and bash syntax-checked; no benchmark was launched.

**Search and evaluate EOG streams**

```sh
for spec in calendar:1,2,3 csm:1,2,3,4 drive:1,2,3 email:1,2,3,4,5,6 hr:1,2,3,4,5 hybrid:1,2,3,4 itsm:1,2,3 teams:1,2,3,4; do
  stream=${spec%%:*}
  versions=${spec#*:}
  bash evolve_tools/src/scripts/run_meta_harness.sh "$stream" \
    --versions "$versions" --model gpt-5 --backend local \
    --concurrency 8 --num-runs 3 --fwt-all \
    --run-name "repro_tools_meta_harness_${REPRO_TAG}_${stream}" \
    --iterations 5 --trials-per-task 3 --resume --results-root "$REPRO_RESULTS/tools-meta-harness"
done
```

One stage chain per stream, pooled validation, three held-out repetitions and full forward/retention matrix. --fwt-all adds the forward cells; stagewise headline summaries pool j<=k. Fresh output roots/suffixes protect archived results.

**Run ALE with the recorded search repetition schedule**

```sh
versions=""
stage=0
for repetitions in 3 3 3 3 1; do
  stage=$((stage + 1))
  versions="${versions:+$versions,}$stage"
  bash evolve_tools/src/scripts/run_meta_harness.sh ale \
    --versions "$versions" --model gpt-5 --backend local \
    --concurrency 8 --iterations 5 --trials-per-task "$repetitions" \
    --run-name "repro_tools_meta_harness_${REPRO_TAG}_ale" \
    --resume --no-eval --results-root "$REPRO_RESULTS/tools-meta-harness"
done
# Resume completed stages and evaluate each winner three times.
bash evolve_tools/src/scripts/run_meta_harness.sh ale \
  --versions "$versions" --model gpt-5 --backend local \
  --concurrency 8 --iterations 5 --trials-per-task 1 \
  --run-name "repro_tools_meta_harness_${REPRO_TAG}_ale" \
  --resume --num-runs 3 --fwt-all --results-root "$REPRO_RESULTS/tools-meta-harness"
```

Requires the historical ALE eligibility snapshot and corresponding task/library files; current manifests can change split counts and denominators. Use a full version prefix, same run name and --resume at each stage so the preceding winner is restored. Passing only the newest stage starts carry state empty. Check prior stages completed before continuing.

**Evaluate an existing checkpoint without another search**

```sh
export REPRO_STREAM=hr
# Reuse the sanitized model config created by the search launcher.
export META_HARNESS_LLM_CONFIG="$PWD/evolve_tools/meta_harness/logs/repro_tools_meta_harness_${REPRO_TAG}_${REPRO_STREAM}/solver_gpt-5.json"
test -f "$META_HARNESS_LLM_CONFIG"
python -m evolve_tools.meta_harness.cl_eval \
  --domain "$REPRO_STREAM" \
  --run-name "repro_tools_meta_harness_${REPRO_TAG}_${REPRO_STREAM}" \
  --model gpt-5 --backend local --concurrency 8 --num-runs 3 --fwt-all \
  --results-root "$REPRO_RESULTS/tools-meta_harness-reeval" --phase cumulative_tool_meta_harness --mode cumulative_tool_meta_harness --llm-config "$META_HARNESS_LLM_CONFIG"
```

HR example reads the newly generated lineage and evaluates into a separate output tree. To evaluate an archived chain, replace --run-name with protocol.search_stages run_name and restore all lineage-linked code/state/library files. Tools also needs your own sanitized model config. This launches fresh stochastic evaluation, not recomputation of archived metrics.

Missing information / conditions:

- No complete historical runtime lock: per-run Python/Codex/Node versions, dependency install state, container digests and immutable model snapshot are not recovered.
- Historical concurrency, timeout, environment overrides and GEPA RNG seeds are not preserved in the inspected search summaries. Recipe values select current documented settings, not proof of the historical launch command.
- No complete optimization token or dollar budget. Retained adapter statistics and reflection usage omit some failed attempts and are not total billed cost.
- The downloadable result bundle does not include executable task environments, gated ALE data, trained checkpoints, full adapted code/state or frozen capability libraries. These assets are required for fresh evaluation.
- A fresh search is stochastic and can select a different winner. Three evaluation repetitions are not three independently optimized harnesses.
- Archived tools Meta-Harness lineage paths still reference the removed cumulative_tools_meta_harness tree. Restore or remap a copied lineage to the registered cumulative_tools_meta_harness_cumulative_val tree before evaluation; verify state/code hashes. The experiment archives are not modified by these recipes.
- Five iterations and three requested candidates are configured plans, not completed work. Archived stages can be incomplete and retained results overwritten; a complete rerun can spend more than the archived run.

Evidence: `analysis/arms.py`; `evolve_tools/src/scripts/run_meta_harness.sh`; `evolve_tools/meta_harness/splits.py`; `evolve_tools/meta_harness/cl_eval.py`; `evolve_tools/meta_harness/run_stages.py`; `install.md`; `scripts/env.sh`; `reference/gepa/pyproject.toml`; `reference/gepa/uv.lock`; `reference/EnterpriseOps-Gym/pyproject.toml`; `reference/EnterpriseOps-Gym/uv.lock`; `reference/agents-last-exam/pyproject.toml`; `reference/agents-last-exam/uv.lock`; `evolve_tools/meta_harness/config.yaml`; `evolve_tools/meta_harness/skills/meta-harness/SKILL.md`

### tools-gepa — GEPA

Historical rerun status: **partial**.

Prerequisites:

- Obtain the experiment source, benchmark task data and frozen capability libraries. Website CSVs can recompute reported aggregates but cannot execute an agent.
- Follow install.md for local EOG gyms, Docker connectivity, Codex CLI authentication and Python environments. Authenticate with your own credentials; never reuse or publish saved authentication files.
- Run namespace packages from the repository root. scripts/env.sh adds the root, eval_service/sdk (simple_agentic_evals), and reference/gepa/src to PYTHONPATH. Install the reference project dependencies instead of substituting another GEPA version.
- EOG requires the reference EnterpriseOps-Gym runtime and its domain gym containers. Tools also require its ReAct/LangChain stack. Verify gym endpoints before spending the search budget.
- ALE requires the reference/agents-last-exam Python 3.12 environment, gated task-data including grading references, a Linux sandbox image and the historical task eligibility/exclusion snapshot. A current manifest can change the denominator.
- Freeze source, dependency locks, Python/Codex/Node versions, container digests, model identifiers, task/split manifests and library hashes. Current source fingerprints do not identify the historical runtime.

**Prepare an isolated run**

```sh
# Run from a prepared writable experiment checkout, not the website.
set -euo pipefail
test -f scripts/env.sh
source scripts/env.sh
# Retain this tag for resume; use a new tag for each independent search.
export REPRO_TAG="$(date -u +%Y%m%d_%H%M%S)_$$"
export REPRO_RESULTS="$PWD/reproduction/$REPRO_TAG"
mkdir -p "$REPRO_RESULTS"
export EVOVLE_CODEX_MODEL=gpt-5
export EVOVLE_CODEX_TRANSPORT=stdio
export EVOVLE_CODEX_TIMEOUT_SEC=900
export EVOVLE_CODEX_MAX_EPISODES=4
export ALE_WALL_TIME_S=7200
export META_HARNESS_BACKEND=local
export META_HARNESS_CONCURRENCY=8
unset EVOVLE_SKILLS_JOBS_ARM_DIR EVOVLE_AGENTS_JOBS_ARM_DIR
```

New run using inspected current source. EOG timeout 900 seconds, four episodes, stdio transport and concurrency eight are explicit current settings, not established historical overrides. Append --dry-run to a search command to inspect its plan once prerequisites exist; preparation files may still be written. Recipes were source-checked and bash syntax-checked; no benchmark was launched.

**Search and evaluate EOG streams**

```sh
for spec in calendar:1,2,3 csm:1,2,3,4 drive:1,2,3 email:1,2,3,4,5,6 hr:1,2,3,4,5 hybrid:1,2,3,4 itsm:1,2,3 teams:1,2,3,4; do
  stream=${spec%%:*}
  versions=${spec#*:}
  bash evolve_tools/src/scripts/run_gepa.sh "$stream" \
    --versions "$versions" --model gpt-5 --backend local \
    --concurrency 8 --num-runs 3 --fwt-all \
    --run-name "repro_tools_gepa_${REPRO_TAG}_${stream}" \
    --max-metric-calls 50 --reflection-minibatch-size 3 --trials-per-task 1 --results-root "$REPRO_RESULTS/tools-gepa"
done
```

One stage chain per stream, pooled validation, three held-out repetitions and full forward/retention matrix. --fwt-all adds the forward cells; stagewise headline summaries pool j<=k. Fresh output roots/suffixes protect archived results.

**Run ALE with the recorded search repetition schedule**

```sh
bash evolve_tools/src/scripts/run_gepa.sh ale \
  --versions 1,2,3,4,5 --model gpt-5 --backend local \
  --concurrency 8 --num-runs 3 --fwt-all \
  --run-name "repro_tools_gepa_${REPRO_TAG}_ale" \
  --max-metric-calls 50 --reflection-minibatch-size 3 --trials-per-task 1 \
  --results-root "$REPRO_RESULTS/tools-gepa"
```

Requires the historical ALE eligibility snapshot and corresponding task/library files; current manifests can change split counts and denominators. One search trial/task throughout; --num-runs 3 is held-out evaluation.

**Evaluate an existing checkpoint without another search**

```sh
export REPRO_STREAM=hr
# Reuse the sanitized model config created by the search launcher.
export META_HARNESS_LLM_CONFIG="$PWD/evolve_tools/meta_harness/logs/repro_tools_gepa_${REPRO_TAG}_${REPRO_STREAM}/solver_gpt-5.json"
test -f "$META_HARNESS_LLM_CONFIG"
python -m evolve_tools.meta_harness.cl_eval \
  --domain "$REPRO_STREAM" \
  --run-name "repro_tools_gepa_${REPRO_TAG}_${REPRO_STREAM}" \
  --model gpt-5 --backend local --concurrency 8 --num-runs 3 --fwt-all \
  --results-root "$REPRO_RESULTS/tools-gepa-reeval" --phase cumulative_tool_gepa --mode cumulative_tool_gepa --llm-config "$META_HARNESS_LLM_CONFIG"
```

HR example reads the newly generated lineage and evaluates into a separate output tree. To evaluate an archived chain, replace --run-name with protocol.search_stages run_name and restore all lineage-linked code/state/library files. Tools also needs your own sanitized model config. This launches fresh stochastic evaluation, not recomputation of archived metrics.

Missing information / conditions:

- No complete historical runtime lock: per-run Python/Codex/Node versions, dependency install state, container digests and immutable model snapshot are not recovered.
- Historical concurrency, timeout, environment overrides and GEPA RNG seeds are not preserved in the inspected search summaries. Recipe values select current documented settings, not proof of the historical launch command.
- No complete optimization token or dollar budget. Retained adapter statistics and reflection usage omit some failed attempts and are not total billed cost.
- The downloadable result bundle does not include executable task environments, gated ALE data, trained checkpoints, full adapted code/state or frozen capability libraries. These assets are required for fresh evaluation.
- A fresh search is stochastic and can select a different winner. Three evaluation repetitions are not three independently optimized harnesses.
- Email v1 is unsearched because it lacks a disjoint learn/validation split. Tools shell does not expose --seed/--max-retries; inspected Python defaults are 0/1.

Evidence: `analysis/arms.py`; `evolve_tools/src/scripts/run_gepa.sh`; `evolve_tools/meta_harness/splits.py`; `evolve_tools/meta_harness/cl_eval.py`; `evolve_tools/meta_harness/run_gepa.py`; `install.md`; `scripts/env.sh`; `reference/gepa/pyproject.toml`; `reference/gepa/uv.lock`; `reference/EnterpriseOps-Gym/pyproject.toml`; `reference/EnterpriseOps-Gym/uv.lock`; `reference/agents-last-exam/pyproject.toml`; `reference/agents-last-exam/uv.lock`; `evolve_tools/meta_harness/gepa_reflection.py`; `evolve_tools/meta_harness/gepa_adapter.py`

### tools-react-ale-v — Codex (ALE, V)

Historical rerun status: **partial**.

Prerequisites:

- Use the exact source tree named in the evidence. The external/evolving-mas-benchmark prefix denotes Vaidehi’s separate checkout; it is not interchangeable with the main experiment source.
- Set REPRO_SOURCE to that checkout, REPRO_DATA_ROOT to the frozen evovling_tools dataset, REPRO_OUTPUT_ROOT to a new empty output directory, REPRO_DOMAIN to the desired stream, and REPRO_CONCURRENCY explicitly.
- Create REPRO_LLM_CONFIG as a private provider configuration with openai/gpt-5, max_tokens 16384 and temperature 0.1; use your own credentials. The original file must not be copied because it can contain secrets.
- EOG requires the matching EnterpriseOps-Gym source/dependencies and running MCP/SQL services. ALE requires the matching agents-last-exam checkout, locked Python >=3.12 environment, Docker/task images, software guard and your own secret file.
- Before ALE runs in the external checkout, point ALE_AGENT_CONFIG at a user-created Codex preset with model gpt-5. This runner has no ALE_MODEL override; its default preset can select gpt-5.4. Validate the generated experiment YAML without printing credentials.

**External tool-runner template**

```sh
cd "${REPRO_SOURCE:?}"
ALE_WALL_TIME_S=7200 python -m evolve_tools.src.runner_evolving_tools \
  --data_root "${REPRO_DATA_ROOT:?}" --domain "${REPRO_DOMAIN:?}" \
  --llm_config "${REPRO_LLM_CONFIG:?}" --output_dir "${REPRO_OUTPUT_ROOT:?}" \
  --memory_mode none --runs_per_stage 3 --concurrency "${REPRO_CONCURRENCY:?}"
```

Current external source template. Use REPRO_DOMAIN=ale for ALE; this arm is ALE-only. Current no-memory ALE code evaluates the final cumulative row only. It cannot recreate every earlier archived matrix cell without recovering the earlier runner/version.

Missing information / conditions:

- The archived launcher command, full environment overrides, exact dependency lock and historical source revision were not preserved in the exported evaluation snapshot.
- A fresh live-model run is stochastic. Matching its protocol does not guarantee the same scores; use the downloadable trial/cell data to reproduce the archived arithmetic.
- Obtain the versioned task splits, capability libraries, original verifier/environment assets and archived task-exclusion manifest before running; current datasets/manifests may differ.
- The external checkout currently has HEAD aef27e4802f7c64dcd591844e6858bcdcdb7da44 plus uncommitted modifications to runner_evolving_tools.py, runner.py, memory.py, reasoning_induction.py, ale_eval.py and metrics.py. This is not an archived run commit or a reproducible source pin.
- Historical solver/induction overrides, retrieval policy, complete adaptation compute usage and matching stage memory artifacts are not fully recorded.

Evidence: `analysis/arms.py`; `external/evolving-mas-benchmark/evolve_tools/src/runner_evolving_tools.py`; `external/evolving-mas-benchmark/evolve_tools/src/ale_eval.py`; `external/evolving-mas-benchmark/evolve_tools/src/scripts/frequent_config/gpt5_evolve_ale_cumulative_tool_no_memory.sh`

### tools-raw-memory — Raw memory

Historical rerun status: **partial**.

Prerequisites:

- Use the exact source tree named in the evidence. The external/evolving-mas-benchmark prefix denotes Vaidehi’s separate checkout; it is not interchangeable with the main experiment source.
- Set REPRO_SOURCE to that checkout, REPRO_DATA_ROOT to the frozen evovling_tools dataset, REPRO_OUTPUT_ROOT to a new empty output directory, REPRO_DOMAIN to the desired stream, and REPRO_CONCURRENCY explicitly.
- Create REPRO_LLM_CONFIG as a private provider configuration with openai/gpt-5, max_tokens 16384 and temperature 0.1; use your own credentials. The original file must not be copied because it can contain secrets.
- EOG requires the matching EnterpriseOps-Gym source/dependencies and running MCP/SQL services. ALE requires the matching agents-last-exam checkout, locked Python >=3.12 environment, Docker/task images, software guard and your own secret file.
- Before ALE runs in the external checkout, point ALE_AGENT_CONFIG at a user-created Codex preset with model gpt-5. This runner has no ALE_MODEL override; its default preset can select gpt-5.4. Validate the generated experiment YAML without printing credentials.

**External tool-runner template**

```sh
cd "${REPRO_SOURCE:?}"
ALE_WALL_TIME_S=7200 python -m evolve_tools.src.runner_evolving_tools \
  --data_root "${REPRO_DATA_ROOT:?}" --domain "${REPRO_DOMAIN:?}" \
  --llm_config "${REPRO_LLM_CONFIG:?}" --output_dir "${REPRO_OUTPUT_ROOT:?}" \
  --memory_mode adapt_fwd --runs_per_stage 3 --concurrency "${REPRO_CONCURRENCY:?}" \
  --memory_repr raw --memory_topk 10 --memory_topk_strategy recent
```

Current external source template. Run independently for each registered EOG stream and ALE, preserving the same frozen splits. Raw/reflection top-k 10 is the current ALE launcher default, not a proven historical setting; EOG historical retrieval overrides are unknown.

Missing information / conditions:

- The archived launcher command, full environment overrides, exact dependency lock and historical source revision were not preserved in the exported evaluation snapshot.
- A fresh live-model run is stochastic. Matching its protocol does not guarantee the same scores; use the downloadable trial/cell data to reproduce the archived arithmetic.
- Obtain the versioned task splits, capability libraries, original verifier/environment assets and archived task-exclusion manifest before running; current datasets/manifests may differ.
- The external checkout currently has HEAD aef27e4802f7c64dcd591844e6858bcdcdb7da44 plus uncommitted modifications to runner_evolving_tools.py, runner.py, memory.py, reasoning_induction.py, ale_eval.py and metrics.py. This is not an archived run commit or a reproducible source pin.
- Historical solver/induction overrides, retrieval policy, complete adaptation compute usage and matching stage memory artifacts are not fully recorded.

Evidence: `analysis/arms.py`; `external/evolving-mas-benchmark/evolve_tools/src/runner_evolving_tools.py`; `external/evolving-mas-benchmark/evolve_tools/src/ale_eval.py`; `external/evolving-mas-benchmark/evolve_tools/src/scripts/frequent_config/gpt5_evolve_ale_cumulative_tool_memory.sh`

### tools-reasoning-bank — Reasoning bank

Historical rerun status: **partial**.

Prerequisites:

- Use the exact source tree named in the evidence. The external/evolving-mas-benchmark prefix denotes Vaidehi’s separate checkout; it is not interchangeable with the main experiment source.
- Set REPRO_SOURCE to that checkout, REPRO_DATA_ROOT to the frozen evovling_tools dataset, REPRO_OUTPUT_ROOT to a new empty output directory, REPRO_DOMAIN to the desired stream, and REPRO_CONCURRENCY explicitly.
- Create REPRO_LLM_CONFIG as a private provider configuration with openai/gpt-5, max_tokens 16384 and temperature 0.1; use your own credentials. The original file must not be copied because it can contain secrets.
- EOG requires the matching EnterpriseOps-Gym source/dependencies and running MCP/SQL services. ALE requires the matching agents-last-exam checkout, locked Python >=3.12 environment, Docker/task images, software guard and your own secret file.
- Before ALE runs in the external checkout, point ALE_AGENT_CONFIG at a user-created Codex preset with model gpt-5. This runner has no ALE_MODEL override; its default preset can select gpt-5.4. Validate the generated experiment YAML without printing credentials.

**External tool-runner template**

```sh
cd "${REPRO_SOURCE:?}"
ALE_WALL_TIME_S=7200 python -m evolve_tools.src.runner_evolving_tools \
  --data_root "${REPRO_DATA_ROOT:?}" --domain "${REPRO_DOMAIN:?}" \
  --llm_config "${REPRO_LLM_CONFIG:?}" --output_dir "${REPRO_OUTPUT_ROOT:?}" \
  --memory_mode adapt_fwd --runs_per_stage 3 --concurrency "${REPRO_CONCURRENCY:?}" \
  --memory_repr reasoning
```

Current external source template. Run independently for each registered EOG stream and ALE, preserving the same frozen splits. Raw/reflection top-k 10 is the current ALE launcher default, not a proven historical setting; EOG historical retrieval overrides are unknown.

Missing information / conditions:

- The archived launcher command, full environment overrides, exact dependency lock and historical source revision were not preserved in the exported evaluation snapshot.
- A fresh live-model run is stochastic. Matching its protocol does not guarantee the same scores; use the downloadable trial/cell data to reproduce the archived arithmetic.
- Obtain the versioned task splits, capability libraries, original verifier/environment assets and archived task-exclusion manifest before running; current datasets/manifests may differ.
- The external checkout currently has HEAD aef27e4802f7c64dcd591844e6858bcdcdb7da44 plus uncommitted modifications to runner_evolving_tools.py, runner.py, memory.py, reasoning_induction.py, ale_eval.py and metrics.py. This is not an archived run commit or a reproducible source pin.
- Historical solver/induction overrides, retrieval policy, complete adaptation compute usage and matching stage memory artifacts are not fully recorded.

Evidence: `analysis/arms.py`; `external/evolving-mas-benchmark/evolve_tools/src/runner_evolving_tools.py`; `external/evolving-mas-benchmark/evolve_tools/src/ale_eval.py`; `external/evolving-mas-benchmark/evolve_tools/src/scripts/frequent_config/gpt5_evolve_ale_cumulative_tool_adapt_fwd_reasoning.sh`

### tools-memtoolagent — MemToolAgent

Historical rerun status: **partial**.

Prerequisites:

- Use the exact source tree named in the evidence. The external/evolving-mas-benchmark prefix denotes Vaidehi’s separate checkout; it is not interchangeable with the main experiment source.
- Set REPRO_SOURCE to that checkout, REPRO_DATA_ROOT to the frozen evovling_tools dataset, REPRO_OUTPUT_ROOT to a new empty output directory, REPRO_DOMAIN to the desired stream, and REPRO_CONCURRENCY explicitly.
- Create REPRO_LLM_CONFIG as a private provider configuration with openai/gpt-5, max_tokens 16384 and temperature 0.1; use your own credentials. The original file must not be copied because it can contain secrets.
- EOG requires the matching EnterpriseOps-Gym source/dependencies and running MCP/SQL services. ALE requires the matching agents-last-exam checkout, locked Python >=3.12 environment, Docker/task images, software guard and your own secret file.
- Before ALE runs in the external checkout, point ALE_AGENT_CONFIG at a user-created Codex preset with model gpt-5. This runner has no ALE_MODEL override; its default preset can select gpt-5.4. Validate the generated experiment YAML without printing credentials.

**External tool-runner template**

```sh
cd "${REPRO_SOURCE:?}"
ALE_WALL_TIME_S=7200 python -m evolve_tools.src.runner_evolving_tools \
  --data_root "${REPRO_DATA_ROOT:?}" --domain "${REPRO_DOMAIN:?}" \
  --llm_config "${REPRO_LLM_CONFIG:?}" --output_dir "${REPRO_OUTPUT_ROOT:?}" \
  --memory_mode adapt_fwd --runs_per_stage 3 --concurrency "${REPRO_CONCURRENCY:?}" \
  --memory_repr reflection --memory_topk 10 --memory_topk_strategy recent
```

Current external source template. Run independently for each registered EOG stream and ALE, preserving the same frozen splits. Raw/reflection top-k 10 is the current ALE launcher default, not a proven historical setting; EOG historical retrieval overrides are unknown.

Missing information / conditions:

- The archived launcher command, full environment overrides, exact dependency lock and historical source revision were not preserved in the exported evaluation snapshot.
- A fresh live-model run is stochastic. Matching its protocol does not guarantee the same scores; use the downloadable trial/cell data to reproduce the archived arithmetic.
- Obtain the versioned task splits, capability libraries, original verifier/environment assets and archived task-exclusion manifest before running; current datasets/manifests may differ.
- The external checkout currently has HEAD aef27e4802f7c64dcd591844e6858bcdcdb7da44 plus uncommitted modifications to runner_evolving_tools.py, runner.py, memory.py, reasoning_induction.py, ale_eval.py and metrics.py. This is not an archived run commit or a reproducible source pin.
- Historical solver/induction overrides, retrieval policy, complete adaptation compute usage and matching stage memory artifacts are not fully recorded.

Evidence: `analysis/arms.py`; `external/evolving-mas-benchmark/evolve_tools/src/runner_evolving_tools.py`; `external/evolving-mas-benchmark/evolve_tools/src/ale_eval.py`; `external/evolving-mas-benchmark/evolve_tools/src/scripts/frequent_config/gpt5_evolve_ale_cumulative_tool_adapt_fwd_reflection.sh`

### skills-oracle — Task-specific Codex

Historical rerun status: **partial**.

Prerequisites:

- Use a complete experiment-source checkout, not the static website. Set REPRO_SOURCE to its root.
- Set REPRO_RUN_ID to a fresh directory-safe run identifier and REPRO_CONCURRENCY to an explicit positive integer. The template concurrency is a new-run choice; historical overrides are unknown.
- For EOG: run the EnterpriseOps-Gym MCP/SQL services from reference/EnterpriseOps-Gym and preserve their dataset/database seeds; install/authenticate Codex CLI with access to the requested model.
- Make eval_service/sdk importable (the launch scripts set PYTHONPATH); install its declared dependencies. The inspected runner documentation requires httpx, with datasets when reloading Hugging Face data.
- For ALE: obtain reference/agents-last-exam, use its Python >=3.12 environment and dependency lock (uv sync), and provision the Docker/cloud environment with the same task image and guard assets. Configure credentials privately through ALE_SECRET_FILE; never copy archived credentials.

**EOG rerun template**

```sh
cd "${REPRO_SOURCE:?}"
EVOVLE_SKILLS_JOBS_ARM_DIR="repro_oracle_${REPRO_RUN_ID:?}" EVOVLE_AGENT_RUNTIME=acp EVOVLE_CODEX_MAX_EPISODES=4 \
  bash evovle_skills/src/scripts/run_oracle_skill.sh --domains "csm hr itsm" --dataset eog \
  --backend local --model gpt-5 --num-runs 3 \
  --concurrency "${REPRO_CONCURRENCY:?}" --timeout-s 900 --transport stdio \
  --run-id "${REPRO_RUN_ID:?}"
```

Current source template; not a recovered historical launch. EOG model matches inspected saved config.toml. Timeout/episodes/transport and explicit concurrency remain new-run settings where historical overrides are absent. This evaluates each cohort once per run under its reference pool.

**ALE rerun template**

```sh
cd "${REPRO_SOURCE:?}"
EVOVLE_SKILLS_JOBS_ARM_DIR="repro_oracle_${REPRO_RUN_ID:?}" EVOVLE_AGENT_RUNTIME=acp EVOVLE_CODEX_MAX_EPISODES=4 ALE_WALL_TIME_S=7200 ALE_MODEL=gpt-5 \
  bash evovle_skills/src/scripts/run_oracle_skill.sh --dataset ale --backend local --model gpt-5 \
  --num-runs 3 --concurrency "${REPRO_CONCURRENCY:?}" \
  --run-id "${REPRO_RUN_ID:?}"
```

Current local-backend template with model explicitly pinned to gpt-5 and task wall clock to 7,200 seconds. Keep the original ALE image, task inventory, hard capability guard and exclusion manifest; the hosted backend can select a different preset.

Missing information / conditions:

- The archived launcher command, full environment overrides, exact dependency lock and historical source revision were not preserved in the exported evaluation snapshot.
- A fresh live-model run is stochastic. Matching its protocol does not guarantee the same scores; use the downloadable trial/cell data to reproduce the archived arithmetic.
- Obtain the versioned task splits, capability libraries, original verifier/environment assets and archived task-exclusion manifest before running; current datasets/manifests may differ.
- The local experiment worktree has no Git HEAD commit; no immutable historical code revision could be established. A source-file checksum identifies the inspected current file only.
- Historical Codex binary version, provider snapshot and per-trial reasoning settings are not completely recorded.

Evidence: `evovle_skills/src/scripts/run_oracle_skill.sh`; `evovle_skills/src/config.py`; `evovle_skills/src/runner.py`; `evolve_tools/src/ale_eval.py`; `analysis/arms.py`

### skills-oracle-gpt55 — Task-specific Codex (gpt-5.5)

Historical rerun status: **partial**.

Prerequisites:

- Use a complete experiment-source checkout, not the static website. Set REPRO_SOURCE to its root.
- Set REPRO_RUN_ID to a fresh directory-safe run identifier and REPRO_CONCURRENCY to an explicit positive integer. The template concurrency is a new-run choice; historical overrides are unknown.
- For EOG: run the EnterpriseOps-Gym MCP/SQL services from reference/EnterpriseOps-Gym and preserve their dataset/database seeds; install/authenticate Codex CLI with access to the requested model.
- Make eval_service/sdk importable (the launch scripts set PYTHONPATH); install its declared dependencies. The inspected runner documentation requires httpx, with datasets when reloading Hugging Face data.
- For ALE: obtain reference/agents-last-exam, use its Python >=3.12 environment and dependency lock (uv sync), and provision the Docker/cloud environment with the same task image and guard assets. Configure credentials privately through ALE_SECRET_FILE; never copy archived credentials.

**EOG rerun template**

```sh
cd "${REPRO_SOURCE:?}"
EVOVLE_SKILLS_JOBS_ARM_DIR="repro_oracle_gpt55_${REPRO_RUN_ID:?}" EVOVLE_AGENT_RUNTIME=acp EVOVLE_CODEX_MAX_EPISODES=4 \
  bash evovle_skills/src/scripts/run_oracle_skill.sh --domains "csm hr itsm" --dataset eog \
  --backend local --model gpt-5.5 --num-runs 3 \
  --concurrency "${REPRO_CONCURRENCY:?}" --timeout-s 900 --transport stdio \
  --run-id "${REPRO_RUN_ID:?}"
```

Current source template; not a recovered historical launch. EOG model matches inspected saved config.toml. Timeout/episodes/transport and explicit concurrency remain new-run settings where historical overrides are absent. This evaluates each cohort once per run under its reference pool.

Missing information / conditions:

- The archived launcher command, full environment overrides, exact dependency lock and historical source revision were not preserved in the exported evaluation snapshot.
- A fresh live-model run is stochastic. Matching its protocol does not guarantee the same scores; use the downloadable trial/cell data to reproduce the archived arithmetic.
- Obtain the versioned task splits, capability libraries, original verifier/environment assets and archived task-exclusion manifest before running; current datasets/manifests may differ.
- The local experiment worktree has no Git HEAD commit; no immutable historical code revision could be established. A source-file checksum identifies the inspected current file only.
- Historical Codex binary version, provider snapshot and per-trial reasoning settings are not completely recorded.

Evidence: `evovle_skills/src/scripts/run_oracle_skill.sh`; `evovle_skills/src/config.py`; `evovle_skills/src/runner.py`; `evolve_tools/src/ale_eval.py`; `analysis/arms.py`

### skills-oracle-claude — Task-specific Claude Code

Historical rerun status: **unavailable**.

Prerequisites:

- Obtain the original Claude Code runner and its locked dependencies/container image from the experiment authors. The registered folder contains exported results, not executable runner source.
- Obtain the original Vertex provider/model endpoint configuration and use your own credentials. Sonnet-4.6 is the reported display label; an immutable historical model identifier was not recovered.
- Obtain the versioned dataset, stage capability bundles, verifier assets and archived task exclusions.

Missing information / conditions:

- No source-supported launch command exists in the supplied result-only export. Do not substitute the Codex launcher or invent Claude CLI flags.
- Historical Claude Code version, exact model/Vertex region, prompts and launch overrides, ALE solver budget and concurrency are absent from the export.
- EOG timeout records establish a 900-second cap; ALE limits are not established. Three accuracy repeats exist, but some usage measurements come from a separate one-run token sweep.

Evidence: `analysis/arms.py`; `yang_li/results_final/README.md`; `yang_li/results_final/per_run/skills/oracle_skill/`

### skills-claude — Claude Code

Historical rerun status: **unavailable**.

Prerequisites:

- Obtain the original Claude Code runner and its locked dependencies/container image from the experiment authors. The registered folder contains exported results, not executable runner source.
- Obtain the original Vertex provider/model endpoint configuration and use your own credentials. Sonnet-4.6 is the reported display label; an immutable historical model identifier was not recovered.
- Obtain the versioned dataset, stage capability bundles, verifier assets and archived task exclusions.

Missing information / conditions:

- No source-supported launch command exists in the supplied result-only export. Do not substitute the Codex launcher or invent Claude CLI flags.
- Historical Claude Code version, exact model/Vertex region, prompts and launch overrides, ALE solver budget and concurrency are absent from the export.
- EOG timeout records establish a 900-second cap; ALE limits are not established. Three accuracy repeats exist, but some usage measurements come from a separate one-run token sweep.

Evidence: `analysis/arms.py`; `yang_li/results_final/README.md`; `yang_li/results_final/per_run/skills/cumulative_skill/`

### skills-codex — Codex

Historical rerun status: **partial**.

Prerequisites:

- Use a complete experiment-source checkout, not the static website. Set REPRO_SOURCE to its root.
- Set REPRO_RUN_ID to a fresh directory-safe run identifier and REPRO_CONCURRENCY to an explicit positive integer. The template concurrency is a new-run choice; historical overrides are unknown.
- For EOG: run the EnterpriseOps-Gym MCP/SQL services from reference/EnterpriseOps-Gym and preserve their dataset/database seeds; install/authenticate Codex CLI with access to the requested model.
- Make eval_service/sdk importable (the launch scripts set PYTHONPATH); install its declared dependencies. The inspected runner documentation requires httpx, with datasets when reloading Hugging Face data.
- For ALE: obtain reference/agents-last-exam, use its Python >=3.12 environment and dependency lock (uv sync), and provision the Docker/cloud environment with the same task image and guard assets. Configure credentials privately through ALE_SECRET_FILE; never copy archived credentials.

**EOG rerun template**

```sh
cd "${REPRO_SOURCE:?}"
EVOVLE_SKILLS_JOBS_ARM_DIR="repro_codex_${REPRO_RUN_ID:?}" EVOVLE_AGENT_RUNTIME=acp EVOVLE_CODEX_MAX_EPISODES=4 \
  bash evovle_skills/src/scripts/run_cumulative_skill.sh --domains "csm hr itsm" --dataset eog \
  --backend local --model gpt-5 --num-runs 3 \
  --concurrency "${REPRO_CONCURRENCY:?}" --timeout-s 900 --transport stdio \
  --run-id "${REPRO_RUN_ID:?}"
```

Current source template; not a recovered historical launch. EOG model matches inspected saved config.toml. Timeout/episodes/transport and explicit concurrency remain new-run settings where historical overrides are absent. Default launcher evaluates the cumulative lower-triangular matrix, not only the diagonal; no --diagonal flag is used.

**ALE rerun template**

```sh
cd "${REPRO_SOURCE:?}"
EVOVLE_SKILLS_JOBS_ARM_DIR="repro_codex_${REPRO_RUN_ID:?}" EVOVLE_AGENT_RUNTIME=acp EVOVLE_CODEX_MAX_EPISODES=4 ALE_WALL_TIME_S=7200 ALE_MODEL=gpt-5 \
  bash evovle_skills/src/scripts/run_cumulative_skill.sh --dataset ale --backend local --model gpt-5 \
  --num-runs 3 --concurrency "${REPRO_CONCURRENCY:?}" \
  --run-id "${REPRO_RUN_ID:?}"
```

Current local-backend template with model explicitly pinned to gpt-5 and task wall clock to 7,200 seconds. Keep the original ALE image, task inventory, hard capability guard and exclusion manifest; the hosted backend can select a different preset.

Missing information / conditions:

- The archived launcher command, full environment overrides, exact dependency lock and historical source revision were not preserved in the exported evaluation snapshot.
- A fresh live-model run is stochastic. Matching its protocol does not guarantee the same scores; use the downloadable trial/cell data to reproduce the archived arithmetic.
- Obtain the versioned task splits, capability libraries, original verifier/environment assets and archived task-exclusion manifest before running; current datasets/manifests may differ.
- The local experiment worktree has no Git HEAD commit; no immutable historical code revision could be established. A source-file checksum identifies the inspected current file only.
- Historical Codex binary version, provider snapshot and per-trial reasoning settings are not completely recorded.

Evidence: `evovle_skills/src/scripts/run_cumulative_skill.sh`; `evovle_skills/src/config.py`; `evovle_skills/src/runner.py`; `evolve_tools/src/ale_eval.py`; `analysis/arms.py`

### skills-memory — Codex Memory

Historical rerun status: **partial**.

Prerequisites:

- Use a complete experiment-source checkout, not the static website. Set REPRO_SOURCE to its root.
- Set REPRO_RUN_ID to a fresh directory-safe run identifier and REPRO_CONCURRENCY to an explicit positive integer. The template concurrency is a new-run choice; historical overrides are unknown.
- For EOG: run the EnterpriseOps-Gym MCP/SQL services from reference/EnterpriseOps-Gym and preserve their dataset/database seeds; install/authenticate Codex CLI with access to the requested model.
- Make eval_service/sdk importable (the launch scripts set PYTHONPATH); install its declared dependencies. The inspected runner documentation requires httpx, with datasets when reloading Hugging Face data.
- For ALE: obtain reference/agents-last-exam, use its Python >=3.12 environment and dependency lock (uv sync), and provision the Docker/cloud environment with the same task image and guard assets. Configure credentials privately through ALE_SECRET_FILE; never copy archived credentials.
- Native memory requires Codex >=0.145.0 in the current runner. This is a minimum, not the historical version. Use a fresh jobs arm directory so old memory cannot enter the rerun.

**EOG rerun template**

```sh
cd "${REPRO_SOURCE:?}"
EVOVLE_SKILLS_JOBS_ARM_DIR="repro_memory_${REPRO_RUN_ID:?}" EVOVLE_AGENT_RUNTIME=acp EVOVLE_CODEX_MAX_EPISODES=4 EVOVLE_MEMORY_EXTRACT_TIMEOUT=600 EVOVLE_MEMORY_CONSOLIDATE_TIMEOUT=900 EVOVLE_MEMORY_EXTRACT_CONCURRENCY=8 EVOVLE_MEMORY_MIN_IDLE_HOURS=1 \
  bash evovle_skills/src/scripts/run_cumulative_skill.sh --domains "csm hr itsm" --dataset eog \
  --backend local --model gpt-5 --num-runs 3 \
  --concurrency "${REPRO_CONCURRENCY:?}" --timeout-s 900 --transport stdio \
  --run-id "${REPRO_RUN_ID:?}" --memory
```

Current source template; not a recovered historical launch. EOG model matches inspected saved config.toml. Timeout/episodes/transport and explicit concurrency remain new-run settings where historical overrides are absent. Default launcher evaluates the cumulative lower-triangular matrix, not only the diagonal; no --diagonal flag is used.

**ALE rerun template**

```sh
cd "${REPRO_SOURCE:?}"
EVOVLE_SKILLS_JOBS_ARM_DIR="repro_memory_${REPRO_RUN_ID:?}" EVOVLE_AGENT_RUNTIME=acp EVOVLE_CODEX_MAX_EPISODES=4 EVOVLE_MEMORY_EXTRACT_TIMEOUT=600 EVOVLE_MEMORY_CONSOLIDATE_TIMEOUT=900 EVOVLE_MEMORY_EXTRACT_CONCURRENCY=8 EVOVLE_MEMORY_MIN_IDLE_HOURS=1 ALE_WALL_TIME_S=7200 ALE_MODEL=gpt-5 \
  bash evovle_skills/src/scripts/run_cumulative_skill.sh --dataset ale --backend local --model gpt-5 \
  --num-runs 3 --concurrency "${REPRO_CONCURRENCY:?}" \
  --run-id "${REPRO_RUN_ID:?}" --memory
```

Current local-backend template with model explicitly pinned to gpt-5 and task wall clock to 7,200 seconds. Keep the original ALE image, task inventory, hard capability guard and exclusion manifest; the hosted backend can select a different preset.

Missing information / conditions:

- The archived launcher command, full environment overrides, exact dependency lock and historical source revision were not preserved in the exported evaluation snapshot.
- A fresh live-model run is stochastic. Matching its protocol does not guarantee the same scores; use the downloadable trial/cell data to reproduce the archived arithmetic.
- Obtain the versioned task splits, capability libraries, original verifier/environment assets and archived task-exclusion manifest before running; current datasets/manifests may differ.
- The local experiment worktree has no Git HEAD commit; no immutable historical code revision could be established. A source-file checksum identifies the inspected current file only.
- Historical Codex binary version, provider snapshot and per-trial reasoning settings are not completely recorded.
- Exact archived memory extraction/consolidation settings, stage memory snapshots and complete adaptation tokens/cost must be obtained to recreate the original treatment.

Evidence: `evovle_skills/src/scripts/run_cumulative_skill.sh`; `evovle_skills/src/config.py`; `evovle_skills/src/runner.py`; `evolve_tools/src/ale_eval.py`; `analysis/arms.py`; `evovle_agents/src/config.py:278`; `evovle_skills/src/scripts/run_cumulative_skill.py`

### skills-meta-harness — Meta-Harness

Historical rerun status: **partial**.

Prerequisites:

- Obtain the experiment source, benchmark task data and frozen capability libraries. Website CSVs can recompute reported aggregates but cannot execute an agent.
- Follow install.md for local EOG gyms, Docker connectivity, Codex CLI authentication and Python environments. Authenticate with your own credentials; never reuse or publish saved authentication files.
- Run namespace packages from the repository root. scripts/env.sh adds the root, eval_service/sdk (simple_agentic_evals), and reference/gepa/src to PYTHONPATH. Install the reference project dependencies instead of substituting another GEPA version.
- EOG requires the reference EnterpriseOps-Gym runtime and its domain gym containers. Tools also require its ReAct/LangChain stack. Verify gym endpoints before spending the search budget.
- ALE requires the reference/agents-last-exam Python 3.12 environment, gated task-data including grading references, a Linux sandbox image and the historical task eligibility/exclusion snapshot. A current manifest can change the denominator.
- Freeze source, dependency locks, Python/Codex/Node versions, container digests, model identifiers, task/split manifests and library hashes. Current source fingerprints do not identify the historical runtime.

**Prepare an isolated run**

```sh
# Run from a prepared writable experiment checkout, not the website.
set -euo pipefail
test -f scripts/env.sh
source scripts/env.sh
# Retain this tag for resume; use a new tag for each independent search.
export REPRO_TAG="$(date -u +%Y%m%d_%H%M%S)_$$"
export REPRO_RESULTS="$PWD/reproduction/$REPRO_TAG"
mkdir -p "$REPRO_RESULTS"
export EVOVLE_CODEX_MODEL=gpt-5
export EVOVLE_CODEX_TRANSPORT=stdio
export EVOVLE_CODEX_TIMEOUT_SEC=900
export EVOVLE_CODEX_MAX_EPISODES=4
export ALE_WALL_TIME_S=7200
export META_HARNESS_BACKEND=local
export META_HARNESS_CONCURRENCY=8
unset EVOVLE_SKILLS_JOBS_ARM_DIR EVOVLE_AGENTS_JOBS_ARM_DIR
```

New run using inspected current source. EOG timeout 900 seconds, four episodes, stdio transport and concurrency eight are explicit current settings, not established historical overrides. Append --dry-run to a search command to inspect its plan once prerequisites exist; preparation files may still be written. Recipes were source-checked and bash syntax-checked; no benchmark was launched.

**Search and evaluate EOG streams**

```sh
export EVOVLE_SKILLS_JOBS_MODE_SUFFIX="_meta_harness_repro_${REPRO_TAG}"
for spec in csm:1,2,3 hr:1,2,3 itsm:1,2,3,4; do
  stream=${spec%%:*}
  versions=${spec#*:}
  bash evovle_skills/src/scripts/run_meta_harness.sh "$stream" \
    --versions "$versions" --model gpt-5 --backend local \
    --concurrency 8 --num-runs 3 --fwt-all \
    --run-name "repro_skills_meta_harness_${REPRO_TAG}_${stream}" \
    --iterations 5 --trials-per-task 3 --resume
done
```

One stage chain per stream, pooled validation, three held-out repetitions and full forward/retention matrix. --fwt-all adds the forward cells; stagewise headline summaries pool j<=k. Fresh output roots/suffixes protect archived results.

**Run ALE with the recorded search repetition schedule**

```sh
export EVOVLE_SKILLS_JOBS_MODE_SUFFIX="_meta_harness_repro_${REPRO_TAG}"
versions=""
stage=0
for repetitions in 3 3 3 3 3 1; do
  stage=$((stage + 1))
  versions="${versions:+$versions,}$stage"
  bash evovle_skills/src/scripts/run_meta_harness.sh ale \
    --versions "$versions" --model gpt-5 --backend local \
    --concurrency 8 --iterations 5 --trials-per-task "$repetitions" \
    --run-name "repro_skills_meta_harness_${REPRO_TAG}_ale" \
    --resume --no-eval
done
# Resume completed stages and evaluate each winner three times.
bash evovle_skills/src/scripts/run_meta_harness.sh ale \
  --versions "$versions" --model gpt-5 --backend local \
  --concurrency 8 --iterations 5 --trials-per-task 1 \
  --run-name "repro_skills_meta_harness_${REPRO_TAG}_ale" \
  --resume --num-runs 3 --fwt-all
```

Requires the historical ALE eligibility snapshot and corresponding task/library files; current manifests can change split counts and denominators. Use a full version prefix, same run name and --resume at each stage so the preceding winner is restored. Passing only the newest stage starts carry state empty. Check prior stages completed before continuing.

**Evaluate an existing checkpoint without another search**

```sh
export REPRO_STREAM=hr
export EVOVLE_SKILLS_JOBS_MODE_SUFFIX="_meta_harness_eval_repro_${REPRO_TAG}"
python -m evovle_skills.meta_harness.cl_eval \
  --domain "$REPRO_STREAM" \
  --run-name "repro_skills_meta_harness_${REPRO_TAG}_${REPRO_STREAM}" \
  --model gpt-5 --backend local --concurrency 8 --num-runs 3 --fwt-all \
  --mode cumulative_skill_oracle_tool
```

HR example reads the newly generated lineage and evaluates into a separate output tree. To evaluate an archived chain, replace --run-name with protocol.search_stages run_name and restore all lineage-linked code/state/library files. Tools also needs your own sanitized model config. This launches fresh stochastic evaluation, not recomputation of archived metrics.

Missing information / conditions:

- No complete historical runtime lock: per-run Python/Codex/Node versions, dependency install state, container digests and immutable model snapshot are not recovered.
- Historical concurrency, timeout, environment overrides and GEPA RNG seeds are not preserved in the inspected search summaries. Recipe values select current documented settings, not proof of the historical launch command.
- No complete optimization token or dollar budget. Retained adapter statistics and reflection usage omit some failed attempts and are not total billed cost.
- The downloadable result bundle does not include executable task environments, gated ALE data, trained checkpoints, full adapted code/state or frozen capability libraries. These assets are required for fresh evaluation.
- A fresh search is stochastic and can select a different winner. Three evaluation repetitions are not three independently optimized harnesses.
- Five iterations and three requested candidates are configured plans, not completed work. Archived stages can be incomplete and retained results overwritten; a complete rerun can spend more than the archived run.

Evidence: `analysis/arms.py`; `evovle_skills/src/scripts/run_meta_harness.sh`; `evovle_skills/meta_harness/splits.py`; `evovle_skills/meta_harness/cl_eval.py`; `evovle_skills/meta_harness/run_stages.py`; `install.md`; `scripts/env.sh`; `reference/gepa/pyproject.toml`; `reference/gepa/uv.lock`; `reference/EnterpriseOps-Gym/pyproject.toml`; `reference/EnterpriseOps-Gym/uv.lock`; `reference/agents-last-exam/pyproject.toml`; `reference/agents-last-exam/uv.lock`; `evovle_skills/meta_harness/config.yaml`; `evovle_skills/meta_harness/skills/meta-harness/SKILL.md`

### skills-gepa — GEPA

Historical rerun status: **partial**.

Prerequisites:

- Obtain the experiment source, benchmark task data and frozen capability libraries. Website CSVs can recompute reported aggregates but cannot execute an agent.
- Follow install.md for local EOG gyms, Docker connectivity, Codex CLI authentication and Python environments. Authenticate with your own credentials; never reuse or publish saved authentication files.
- Run namespace packages from the repository root. scripts/env.sh adds the root, eval_service/sdk (simple_agentic_evals), and reference/gepa/src to PYTHONPATH. Install the reference project dependencies instead of substituting another GEPA version.
- EOG requires the reference EnterpriseOps-Gym runtime and its domain gym containers. Tools also require its ReAct/LangChain stack. Verify gym endpoints before spending the search budget.
- ALE requires the reference/agents-last-exam Python 3.12 environment, gated task-data including grading references, a Linux sandbox image and the historical task eligibility/exclusion snapshot. A current manifest can change the denominator.
- Freeze source, dependency locks, Python/Codex/Node versions, container digests, model identifiers, task/split manifests and library hashes. Current source fingerprints do not identify the historical runtime.

**Prepare an isolated run**

```sh
# Run from a prepared writable experiment checkout, not the website.
set -euo pipefail
test -f scripts/env.sh
source scripts/env.sh
# Retain this tag for resume; use a new tag for each independent search.
export REPRO_TAG="$(date -u +%Y%m%d_%H%M%S)_$$"
export REPRO_RESULTS="$PWD/reproduction/$REPRO_TAG"
mkdir -p "$REPRO_RESULTS"
export EVOVLE_CODEX_MODEL=gpt-5
export EVOVLE_CODEX_TRANSPORT=stdio
export EVOVLE_CODEX_TIMEOUT_SEC=900
export EVOVLE_CODEX_MAX_EPISODES=4
export ALE_WALL_TIME_S=7200
export META_HARNESS_BACKEND=local
export META_HARNESS_CONCURRENCY=8
unset EVOVLE_SKILLS_JOBS_ARM_DIR EVOVLE_AGENTS_JOBS_ARM_DIR
```

New run using inspected current source. EOG timeout 900 seconds, four episodes, stdio transport and concurrency eight are explicit current settings, not established historical overrides. Append --dry-run to a search command to inspect its plan once prerequisites exist; preparation files may still be written. Recipes were source-checked and bash syntax-checked; no benchmark was launched.

**Search and evaluate EOG streams**

```sh
for spec in csm:1,2,3 hr:1,2,3 itsm:1,2,3,4; do
  stream=${spec%%:*}
  versions=${spec#*:}
  bash evovle_skills/src/scripts/run_gepa.sh "$stream" \
    --versions "$versions" --model gpt-5 --backend local \
    --concurrency 8 --num-runs 3 --fwt-all \
    --run-name "repro_skills_gepa_${REPRO_TAG}_${stream}" \
    --max-metric-calls 50 --reflection-minibatch-size 3 --trials-per-task 1 --jobs-suffix "_gepa_repro_${REPRO_TAG}" --seed 0 --max-retries 1
done
```

One stage chain per stream, pooled validation, three held-out repetitions and full forward/retention matrix. --fwt-all adds the forward cells; stagewise headline summaries pool j<=k. Fresh output roots/suffixes protect archived results.

**Run ALE with the recorded search repetition schedule**

```sh
bash evovle_skills/src/scripts/run_gepa.sh ale \
  --versions 1,2,3,4,5,6 --model gpt-5 --backend local \
  --concurrency 8 --num-runs 3 --fwt-all \
  --run-name "repro_skills_gepa_${REPRO_TAG}_ale" \
  --max-metric-calls 50 --reflection-minibatch-size 3 --trials-per-task 1 \
  --jobs-suffix "_gepa_repro_${REPRO_TAG}" --seed 0 --max-retries 1
```

Requires the historical ALE eligibility snapshot and corresponding task/library files; current manifests can change split counts and denominators. One search trial/task throughout; --num-runs 3 is held-out evaluation.

**Evaluate an existing checkpoint without another search**

```sh
export REPRO_STREAM=hr
export EVOVLE_SKILLS_JOBS_MODE_SUFFIX="_gepa_eval_repro_${REPRO_TAG}"
python -m evovle_skills.meta_harness.cl_eval \
  --domain "$REPRO_STREAM" \
  --run-name "repro_skills_gepa_${REPRO_TAG}_${REPRO_STREAM}" \
  --model gpt-5 --backend local --concurrency 8 --num-runs 3 --fwt-all \
  --mode cumulative_skill_oracle_tool
```

HR example reads the newly generated lineage and evaluates into a separate output tree. To evaluate an archived chain, replace --run-name with protocol.search_stages run_name and restore all lineage-linked code/state/library files. Tools also needs your own sanitized model config. This launches fresh stochastic evaluation, not recomputation of archived metrics.

Missing information / conditions:

- No complete historical runtime lock: per-run Python/Codex/Node versions, dependency install state, container digests and immutable model snapshot are not recovered.
- Historical concurrency, timeout, environment overrides and GEPA RNG seeds are not preserved in the inspected search summaries. Recipe values select current documented settings, not proof of the historical launch command.
- No complete optimization token or dollar budget. Retained adapter statistics and reflection usage omit some failed attempts and are not total billed cost.
- The downloadable result bundle does not include executable task environments, gated ALE data, trained checkpoints, full adapted code/state or frozen capability libraries. These assets are required for fresh evaluation.
- A fresh search is stochastic and can select a different winner. Three evaluation repetitions are not three independently optimized harnesses.

Evidence: `analysis/arms.py`; `evovle_skills/src/scripts/run_gepa.sh`; `evovle_skills/meta_harness/splits.py`; `evovle_skills/meta_harness/cl_eval.py`; `evovle_skills/meta_harness/run_gepa.py`; `install.md`; `scripts/env.sh`; `reference/gepa/pyproject.toml`; `reference/gepa/uv.lock`; `reference/EnterpriseOps-Gym/pyproject.toml`; `reference/EnterpriseOps-Gym/uv.lock`; `reference/agents-last-exam/pyproject.toml`; `reference/agents-last-exam/uv.lock`; `evovle_skills/meta_harness/gepa_reflection.py`; `evovle_skills/meta_harness/gepa_adapter.py`

### skills-gepa-oracle — Task-specific GEPA (eval on full library)

Historical rerun status: **partial**.

Prerequisites:

- Obtain the experiment source, benchmark task data and frozen capability libraries. Website CSVs can recompute reported aggregates but cannot execute an agent.
- Follow install.md for local EOG gyms, Docker connectivity, Codex CLI authentication and Python environments. Authenticate with your own credentials; never reuse or publish saved authentication files.
- Run namespace packages from the repository root. scripts/env.sh adds the root, eval_service/sdk (simple_agentic_evals), and reference/gepa/src to PYTHONPATH. Install the reference project dependencies instead of substituting another GEPA version.
- EOG requires the reference EnterpriseOps-Gym runtime and its domain gym containers. Tools also require its ReAct/LangChain stack. Verify gym endpoints before spending the search budget.
- ALE requires the reference/agents-last-exam Python 3.12 environment, gated task-data including grading references, a Linux sandbox image and the historical task eligibility/exclusion snapshot. A current manifest can change the denominator.
- Freeze source, dependency locks, Python/Codex/Node versions, container digests, model identifiers, task/split manifests and library hashes. Current source fingerprints do not identify the historical runtime.

**Prepare an isolated run**

```sh
# Run from a prepared writable experiment checkout, not the website.
set -euo pipefail
test -f scripts/env.sh
source scripts/env.sh
# Retain this tag for resume; use a new tag for each independent search.
export REPRO_TAG="$(date -u +%Y%m%d_%H%M%S)_$$"
export REPRO_RESULTS="$PWD/reproduction/$REPRO_TAG"
mkdir -p "$REPRO_RESULTS"
export EVOVLE_CODEX_MODEL=gpt-5
export EVOVLE_CODEX_TRANSPORT=stdio
export EVOVLE_CODEX_TIMEOUT_SEC=900
export EVOVLE_CODEX_MAX_EPISODES=4
export ALE_WALL_TIME_S=7200
export META_HARNESS_BACKEND=local
export META_HARNESS_CONCURRENCY=8
unset EVOVLE_SKILLS_JOBS_ARM_DIR EVOVLE_AGENTS_JOBS_ARM_DIR
```

New run using inspected current source. EOG timeout 900 seconds, four episodes, stdio transport and concurrency eight are explicit current settings, not established historical overrides. Append --dry-run to a search command to inspect its plan once prerequisites exist; preparation files may still be written. Recipes were source-checked and bash syntax-checked; no benchmark was launched.

**Search oracle-skills streams and evaluate final rows**

```sh
# This arm refuses --jobs-suffix; use a disposable checkout without prior arm output.
test ! -e evovle_skills/jobs/oracle_skills_gepa
for stream in csm hr itsm; do
  bash evovle_skills/src/scripts/run_gepa.sh "$stream" \
    --oracle-skills --final-row-only --model gpt-5 --backend local \
    --concurrency 8 --num-runs 3 \
    --run-name "repro_skills_gepa_oracle_${REPRO_TAG}_${stream}" \
    --max-metric-calls 50 --reflection-minibatch-size 3 --trials-per-task 1 \
    --seed 0 --max-retries 1
done
```

Search uses task-specific oracle skills; held-out evaluation uses the full final library. CSM/HR end at v3; ITSM at v4. No ALE or earlier held-out rows are part of this arm. The outer run_oracle_skill_gepa.sh wrapper hardcodes the original absolute checkout; this inner launcher works in an isolated checkout.

Missing information / conditions:

- No complete historical runtime lock: per-run Python/Codex/Node versions, dependency install state, container digests and immutable model snapshot are not recovered.
- Historical concurrency, timeout, environment overrides and GEPA RNG seeds are not preserved in the inspected search summaries. Recipe values select current documented settings, not proof of the historical launch command.
- No complete optimization token or dollar budget. Retained adapter statistics and reflection usage omit some failed attempts and are not total billed cost.
- The downloadable result bundle does not include executable task environments, gated ALE data, trained checkpoints, full adapted code/state or frozen capability libraries. These assets are required for fresh evaluation.
- A fresh search is stochastic and can select a different winner. Three evaluation repetitions are not three independently optimized harnesses.
- Fixed oracle_skills_gepa output tree cannot be relocated by the launcher; use a fresh disposable checkout to avoid reusing archived cells.

Evidence: `analysis/arms.py`; `evovle_skills/src/scripts/run_gepa.sh`; `evovle_skills/meta_harness/splits.py`; `evovle_skills/meta_harness/cl_eval.py`; `evovle_skills/meta_harness/run_gepa.py`; `install.md`; `scripts/env.sh`; `reference/gepa/pyproject.toml`; `reference/gepa/uv.lock`; `reference/EnterpriseOps-Gym/pyproject.toml`; `reference/EnterpriseOps-Gym/uv.lock`; `reference/agents-last-exam/pyproject.toml`; `reference/agents-last-exam/uv.lock`; `evovle_skills/src/scripts/run_oracle_skill_gepa.sh`; `evovle_skills/meta_harness/gepa_reflection.py`; `evovle_skills/meta_harness/gepa_adapter.py`

### skills-skillopt — SkillOpt

Historical rerun status: **unavailable**.

Prerequisites:

- Obtain SkillOpt source, an executable configuration and dependency/environment lock for this exact evaluation export from the experiment authors.
- Obtain the recorded optimized artifacts and their stage mapping, original EOG task/capability data and verifier assets.

Missing information / conditions:

- No executable SkillOpt runner or command was found under the registered result directory.
- Optimization budget, optimizer settings, adaptation data selection, concurrency, task timeout and measured trial durations are not available in the archived evaluation export.
- The adjacent service_sweep artifacts belong to a different six-pass experiment and cannot supply this row’s budget.
- GPT-5.5 is recorded by the registry/directory identifier; an immutable provider model snapshot and source revision are unavailable.

Evidence: `analysis/arms.py:637`; `ye_liu/cumulative_skill_skillopt/`

### agents-oracle — Task-specific Codex

Historical rerun status: **partial**.

Prerequisites:

- Use a complete experiment-source checkout, not the static website. Set REPRO_SOURCE to its root.
- Set REPRO_RUN_ID to a fresh directory-safe run identifier and REPRO_CONCURRENCY to an explicit positive integer. The template concurrency is a new-run choice; historical overrides are unknown.
- For EOG: run the EnterpriseOps-Gym MCP/SQL services from reference/EnterpriseOps-Gym and preserve their dataset/database seeds; install/authenticate Codex CLI with access to the requested model.
- Make eval_service/sdk importable (the launch scripts set PYTHONPATH); install its declared dependencies. The inspected runner documentation requires httpx, with datasets when reloading Hugging Face data.
- For ALE: obtain reference/agents-last-exam, use its Python >=3.12 environment and dependency lock (uv sync), and provision the Docker/cloud environment with the same task image and guard assets. Configure credentials privately through ALE_SECRET_FILE; never copy archived credentials.

**EOG rerun template**

```sh
cd "${REPRO_SOURCE:?}"
EVOVLE_AGENTS_JOBS_ARM_DIR="repro_oracle_${REPRO_RUN_ID:?}" EVOVLE_AGENTS_RUNTIME=acp EVOVLE_AGENTS_MAX_THREADS=12 EVOVLE_AGENTS_MAX_DEPTH=1 EVOVLE_CODEX_MAX_EPISODES=4 \
  bash evovle_agents/src/scripts/run_oracle_agents.sh --domains "csm hr itsm" --dataset eog \
  --backend local --model gpt-5-codex --num-runs 3 \
  --concurrency "${REPRO_CONCURRENCY:?}" --timeout-s 900 --transport stdio \
  --run-id "${REPRO_RUN_ID:?}"
```

Current source template; not a recovered historical launch. EOG model matches inspected saved config.toml. Timeout/episodes/transport and explicit concurrency remain new-run settings where historical overrides are absent. This evaluates each cohort once per run under its reference pool.

**ALE rerun template**

```sh
cd "${REPRO_SOURCE:?}"
EVOVLE_AGENTS_JOBS_ARM_DIR="repro_oracle_${REPRO_RUN_ID:?}" EVOVLE_AGENTS_RUNTIME=acp EVOVLE_AGENTS_MAX_THREADS=12 EVOVLE_AGENTS_MAX_DEPTH=1 EVOVLE_CODEX_MAX_EPISODES=4 ALE_WALL_TIME_S=7200 ALE_MODEL=gpt-5 \
  bash evovle_agents/src/scripts/run_oracle_agents.sh --dataset ale --backend local --model gpt-5 \
  --num-runs 3 --concurrency "${REPRO_CONCURRENCY:?}" \
  --run-id "${REPRO_RUN_ID:?}"
```

Current local-backend template with model explicitly pinned to gpt-5 and task wall clock to 7,200 seconds. Keep the original ALE image, task inventory, hard capability guard and exclusion manifest; the hosted backend can select a different preset.

Missing information / conditions:

- The archived launcher command, full environment overrides, exact dependency lock and historical source revision were not preserved in the exported evaluation snapshot.
- A fresh live-model run is stochastic. Matching its protocol does not guarantee the same scores; use the downloadable trial/cell data to reproduce the archived arithmetic.
- Obtain the versioned task splits, capability libraries, original verifier/environment assets and archived task-exclusion manifest before running; current datasets/manifests may differ.
- The local experiment worktree has no Git HEAD commit; no immutable historical code revision could be established. A source-file checksum identifies the inspected current file only.
- Historical Codex binary version, provider snapshot and per-trial reasoning settings are not completely recorded.

Evidence: `evovle_agents/src/scripts/run_oracle_agents.sh`; `evovle_agents/src/config.py`; `evovle_agents/src/runner.py`; `evolve_tools/src/ale_eval.py`; `analysis/arms.py`; `evovle_agents/src/runner.py:382`; `evovle_agents/src/agent_library.py:243`; `evovle_agents/src/ale_eval.py:134`

### agents-oracle-claude — Task-specific Claude Code

Historical rerun status: **unavailable**.

Prerequisites:

- Obtain the original Claude Code runner and its locked dependencies/container image from the experiment authors. The registered folder contains exported results, not executable runner source.
- Obtain the original Vertex provider/model endpoint configuration and use your own credentials. Sonnet-4.6 is the reported display label; an immutable historical model identifier was not recovered.
- Obtain the versioned dataset, stage capability bundles, verifier assets and archived task exclusions.

Missing information / conditions:

- No source-supported launch command exists in the supplied result-only export. Do not substitute the Codex launcher or invent Claude CLI flags.
- Historical Claude Code version, exact model/Vertex region, prompts and launch overrides, ALE solver budget and concurrency are absent from the export.
- EOG timeout records establish a 900-second cap; ALE limits are not established. Three accuracy repeats exist, but some usage measurements come from a separate one-run token sweep.

Evidence: `analysis/arms.py`; `yang_li/results_final/README.md`; `yang_li/results_final/per_run/agents/oracle_agents/`

### agents-codex — Codex

Historical rerun status: **partial**.

Prerequisites:

- Use a complete experiment-source checkout, not the static website. Set REPRO_SOURCE to its root.
- Set REPRO_RUN_ID to a fresh directory-safe run identifier and REPRO_CONCURRENCY to an explicit positive integer. The template concurrency is a new-run choice; historical overrides are unknown.
- For EOG: run the EnterpriseOps-Gym MCP/SQL services from reference/EnterpriseOps-Gym and preserve their dataset/database seeds; install/authenticate Codex CLI with access to the requested model.
- Make eval_service/sdk importable (the launch scripts set PYTHONPATH); install its declared dependencies. The inspected runner documentation requires httpx, with datasets when reloading Hugging Face data.
- For ALE: obtain reference/agents-last-exam, use its Python >=3.12 environment and dependency lock (uv sync), and provision the Docker/cloud environment with the same task image and guard assets. Configure credentials privately through ALE_SECRET_FILE; never copy archived credentials.

**EOG rerun template**

```sh
cd "${REPRO_SOURCE:?}"
EVOVLE_AGENTS_JOBS_ARM_DIR="repro_codex_${REPRO_RUN_ID:?}" EVOVLE_AGENTS_RUNTIME=acp EVOVLE_AGENTS_MAX_THREADS=12 EVOVLE_AGENTS_MAX_DEPTH=1 EVOVLE_CODEX_MAX_EPISODES=4 \
  bash evovle_agents/src/scripts/run_cumulative_agents.sh --domains "csm hr itsm" --dataset eog \
  --backend local --model gpt-5-codex --num-runs 3 \
  --concurrency "${REPRO_CONCURRENCY:?}" --timeout-s 900 --transport stdio \
  --run-id "${REPRO_RUN_ID:?}"
```

Current source template; not a recovered historical launch. EOG model matches inspected saved config.toml. Timeout/episodes/transport and explicit concurrency remain new-run settings where historical overrides are absent. Default launcher evaluates the cumulative lower-triangular matrix, not only the diagonal; no --diagonal flag is used.

**ALE rerun template**

```sh
cd "${REPRO_SOURCE:?}"
EVOVLE_AGENTS_JOBS_ARM_DIR="repro_codex_${REPRO_RUN_ID:?}" EVOVLE_AGENTS_RUNTIME=acp EVOVLE_AGENTS_MAX_THREADS=12 EVOVLE_AGENTS_MAX_DEPTH=1 EVOVLE_CODEX_MAX_EPISODES=4 ALE_WALL_TIME_S=7200 ALE_MODEL=gpt-5 \
  bash evovle_agents/src/scripts/run_cumulative_agents.sh --dataset ale --backend local --model gpt-5 \
  --num-runs 3 --concurrency "${REPRO_CONCURRENCY:?}" \
  --run-id "${REPRO_RUN_ID:?}"
```

Current local-backend template with model explicitly pinned to gpt-5 and task wall clock to 7,200 seconds. Keep the original ALE image, task inventory, hard capability guard and exclusion manifest; the hosted backend can select a different preset.

Missing information / conditions:

- The archived launcher command, full environment overrides, exact dependency lock and historical source revision were not preserved in the exported evaluation snapshot.
- A fresh live-model run is stochastic. Matching its protocol does not guarantee the same scores; use the downloadable trial/cell data to reproduce the archived arithmetic.
- Obtain the versioned task splits, capability libraries, original verifier/environment assets and archived task-exclusion manifest before running; current datasets/manifests may differ.
- The local experiment worktree has no Git HEAD commit; no immutable historical code revision could be established. A source-file checksum identifies the inspected current file only.
- Historical Codex binary version, provider snapshot and per-trial reasoning settings are not completely recorded.

Evidence: `evovle_agents/src/scripts/run_cumulative_agents.sh`; `evovle_agents/src/config.py`; `evovle_agents/src/runner.py`; `evolve_tools/src/ale_eval.py`; `analysis/arms.py`

### agents-claude — Claude Code

Historical rerun status: **unavailable**.

Prerequisites:

- Obtain the original Claude Code runner and its locked dependencies/container image from the experiment authors. The registered folder contains exported results, not executable runner source.
- Obtain the original Vertex provider/model endpoint configuration and use your own credentials. Sonnet-4.6 is the reported display label; an immutable historical model identifier was not recovered.
- Obtain the versioned dataset, stage capability bundles, verifier assets and archived task exclusions.

Missing information / conditions:

- No source-supported launch command exists in the supplied result-only export. Do not substitute the Codex launcher or invent Claude CLI flags.
- Historical Claude Code version, exact model/Vertex region, prompts and launch overrides, ALE solver budget and concurrency are absent from the export.
- EOG timeout records establish a 900-second cap; ALE limits are not established. Three accuracy repeats exist, but some usage measurements come from a separate one-run token sweep.

Evidence: `analysis/arms.py`; `yang_li/results_final/README.md`; `yang_li/results_final/per_run/agents/cumulative_agents/`

### agents-memory — Codex Memory

Historical rerun status: **partial**.

Prerequisites:

- Use a complete experiment-source checkout, not the static website. Set REPRO_SOURCE to its root.
- Set REPRO_RUN_ID to a fresh directory-safe run identifier and REPRO_CONCURRENCY to an explicit positive integer. The template concurrency is a new-run choice; historical overrides are unknown.
- For EOG: run the EnterpriseOps-Gym MCP/SQL services from reference/EnterpriseOps-Gym and preserve their dataset/database seeds; install/authenticate Codex CLI with access to the requested model.
- Make eval_service/sdk importable (the launch scripts set PYTHONPATH); install its declared dependencies. The inspected runner documentation requires httpx, with datasets when reloading Hugging Face data.
- For ALE: obtain reference/agents-last-exam, use its Python >=3.12 environment and dependency lock (uv sync), and provision the Docker/cloud environment with the same task image and guard assets. Configure credentials privately through ALE_SECRET_FILE; never copy archived credentials.
- Native memory requires Codex >=0.145.0 in the current runner. This is a minimum, not the historical version. Use a fresh jobs arm directory so old memory cannot enter the rerun.

**EOG rerun template**

```sh
cd "${REPRO_SOURCE:?}"
EVOVLE_AGENTS_JOBS_ARM_DIR="repro_memory_${REPRO_RUN_ID:?}" EVOVLE_AGENTS_RUNTIME=acp EVOVLE_AGENTS_MAX_THREADS=12 EVOVLE_AGENTS_MAX_DEPTH=1 EVOVLE_CODEX_MAX_EPISODES=4 EVOVLE_MEMORY_EXTRACT_TIMEOUT=600 EVOVLE_MEMORY_CONSOLIDATE_TIMEOUT=900 EVOVLE_MEMORY_EXTRACT_CONCURRENCY=8 EVOVLE_MEMORY_MIN_IDLE_HOURS=1 \
  bash evovle_agents/src/scripts/run_cumulative_agents.sh --domains "csm hr itsm" --dataset eog \
  --backend local --model gpt-5 --num-runs 3 \
  --concurrency "${REPRO_CONCURRENCY:?}" --timeout-s 900 --transport stdio \
  --run-id "${REPRO_RUN_ID:?}" --memory
```

Current source template; not a recovered historical launch. EOG model matches inspected saved config.toml. Timeout/episodes/transport and explicit concurrency remain new-run settings where historical overrides are absent. Default launcher evaluates the cumulative lower-triangular matrix, not only the diagonal; no --diagonal flag is used.

**ALE rerun template**

```sh
cd "${REPRO_SOURCE:?}"
EVOVLE_AGENTS_JOBS_ARM_DIR="repro_memory_${REPRO_RUN_ID:?}" EVOVLE_AGENTS_RUNTIME=acp EVOVLE_AGENTS_MAX_THREADS=12 EVOVLE_AGENTS_MAX_DEPTH=1 EVOVLE_CODEX_MAX_EPISODES=4 EVOVLE_MEMORY_EXTRACT_TIMEOUT=600 EVOVLE_MEMORY_CONSOLIDATE_TIMEOUT=900 EVOVLE_MEMORY_EXTRACT_CONCURRENCY=8 EVOVLE_MEMORY_MIN_IDLE_HOURS=1 ALE_WALL_TIME_S=7200 ALE_MODEL=gpt-5 \
  bash evovle_agents/src/scripts/run_cumulative_agents.sh --dataset ale --backend local --model gpt-5 \
  --num-runs 3 --concurrency "${REPRO_CONCURRENCY:?}" \
  --run-id "${REPRO_RUN_ID:?}" --memory
```

Current local-backend template with model explicitly pinned to gpt-5 and task wall clock to 7,200 seconds. Keep the original ALE image, task inventory, hard capability guard and exclusion manifest; the hosted backend can select a different preset.

Missing information / conditions:

- The archived launcher command, full environment overrides, exact dependency lock and historical source revision were not preserved in the exported evaluation snapshot.
- A fresh live-model run is stochastic. Matching its protocol does not guarantee the same scores; use the downloadable trial/cell data to reproduce the archived arithmetic.
- Obtain the versioned task splits, capability libraries, original verifier/environment assets and archived task-exclusion manifest before running; current datasets/manifests may differ.
- The local experiment worktree has no Git HEAD commit; no immutable historical code revision could be established. A source-file checksum identifies the inspected current file only.
- Historical Codex binary version, provider snapshot and per-trial reasoning settings are not completely recorded.
- Exact archived memory extraction/consolidation settings, stage memory snapshots and complete adaptation tokens/cost must be obtained to recreate the original treatment.

Evidence: `evovle_agents/src/scripts/run_cumulative_agents.sh`; `evovle_agents/src/config.py`; `evovle_agents/src/runner.py`; `evolve_tools/src/ale_eval.py`; `analysis/arms.py`; `evovle_agents/src/config.py:278`; `evovle_agents/src/scripts/run_cumulative_agents.py`

### agents-meta-harness — Meta-Harness

Historical rerun status: **partial**.

Prerequisites:

- Obtain the experiment source, benchmark task data and frozen capability libraries. Website CSVs can recompute reported aggregates but cannot execute an agent.
- Follow install.md for local EOG gyms, Docker connectivity, Codex CLI authentication and Python environments. Authenticate with your own credentials; never reuse or publish saved authentication files.
- Run namespace packages from the repository root. scripts/env.sh adds the root, eval_service/sdk (simple_agentic_evals), and reference/gepa/src to PYTHONPATH. Install the reference project dependencies instead of substituting another GEPA version.
- EOG requires the reference EnterpriseOps-Gym runtime and its domain gym containers. Tools also require its ReAct/LangChain stack. Verify gym endpoints before spending the search budget.
- ALE requires the reference/agents-last-exam Python 3.12 environment, gated task-data including grading references, a Linux sandbox image and the historical task eligibility/exclusion snapshot. A current manifest can change the denominator.
- Freeze source, dependency locks, Python/Codex/Node versions, container digests, model identifiers, task/split manifests and library hashes. Current source fingerprints do not identify the historical runtime.

**Prepare an isolated run**

```sh
# Run from a prepared writable experiment checkout, not the website.
set -euo pipefail
test -f scripts/env.sh
source scripts/env.sh
# Retain this tag for resume; use a new tag for each independent search.
export REPRO_TAG="$(date -u +%Y%m%d_%H%M%S)_$$"
export REPRO_RESULTS="$PWD/reproduction/$REPRO_TAG"
mkdir -p "$REPRO_RESULTS"
export EVOVLE_CODEX_MODEL=gpt-5
export EVOVLE_CODEX_TRANSPORT=stdio
export EVOVLE_CODEX_TIMEOUT_SEC=900
export EVOVLE_CODEX_MAX_EPISODES=4
export ALE_WALL_TIME_S=7200
export META_HARNESS_BACKEND=local
export META_HARNESS_CONCURRENCY=8
unset EVOVLE_SKILLS_JOBS_ARM_DIR EVOVLE_AGENTS_JOBS_ARM_DIR
```

New run using inspected current source. EOG timeout 900 seconds, four episodes, stdio transport and concurrency eight are explicit current settings, not established historical overrides. Append --dry-run to a search command to inspect its plan once prerequisites exist; preparation files may still be written. Recipes were source-checked and bash syntax-checked; no benchmark was launched.

**Search and evaluate EOG streams**

```sh
export EVOVLE_AGENTS_JOBS_MODE_SUFFIX="_meta_harness_repro_${REPRO_TAG}"
for spec in csm:1,2,3 hr:1,2,3,4 itsm:1,2,3,4; do
  stream=${spec%%:*}
  versions=${spec#*:}
  bash evovle_agents/src/scripts/run_meta_harness.sh "$stream" \
    --versions "$versions" --model gpt-5 --backend local \
    --concurrency 8 --num-runs 3 --fwt-all \
    --run-name "repro_agents_meta_harness_${REPRO_TAG}_${stream}" \
    --iterations 5 --trials-per-task 3 --resume
done
```

One stage chain per stream, pooled validation, three held-out repetitions and full forward/retention matrix. --fwt-all adds the forward cells; stagewise headline summaries pool j<=k. Fresh output roots/suffixes protect archived results.

**Run ALE with the recorded search repetition schedule**

```sh
export EVOVLE_AGENTS_JOBS_MODE_SUFFIX="_meta_harness_repro_${REPRO_TAG}"
versions=""
stage=0
for repetitions in 3 3 3 3 1 1; do
  stage=$((stage + 1))
  versions="${versions:+$versions,}$stage"
  bash evovle_agents/src/scripts/run_meta_harness.sh ale \
    --versions "$versions" --model gpt-5 --backend local \
    --concurrency 8 --iterations 5 --trials-per-task "$repetitions" \
    --run-name "repro_agents_meta_harness_${REPRO_TAG}_ale" \
    --resume --no-eval
done
# Resume completed stages and evaluate each winner three times.
bash evovle_agents/src/scripts/run_meta_harness.sh ale \
  --versions "$versions" --model gpt-5 --backend local \
  --concurrency 8 --iterations 5 --trials-per-task 1 \
  --run-name "repro_agents_meta_harness_${REPRO_TAG}_ale" \
  --resume --num-runs 3 --fwt-all
```

Requires the historical ALE eligibility snapshot and corresponding task/library files; current manifests can change split counts and denominators. Use a full version prefix, same run name and --resume at each stage so the preceding winner is restored. Passing only the newest stage starts carry state empty. Check prior stages completed before continuing.

**Evaluate an existing checkpoint without another search**

```sh
export REPRO_STREAM=hr
export EVOVLE_AGENTS_JOBS_MODE_SUFFIX="_meta_harness_eval_repro_${REPRO_TAG}"
python -m evovle_agents.meta_harness.cl_eval \
  --domain "$REPRO_STREAM" \
  --run-name "repro_agents_meta_harness_${REPRO_TAG}_${REPRO_STREAM}" \
  --model gpt-5 --backend local --concurrency 8 --num-runs 3 --fwt-all

```

HR example reads the newly generated lineage and evaluates into a separate output tree. To evaluate an archived chain, replace --run-name with protocol.search_stages run_name and restore all lineage-linked code/state/library files. Tools also needs your own sanitized model config. This launches fresh stochastic evaluation, not recomputation of archived metrics.

Missing information / conditions:

- No complete historical runtime lock: per-run Python/Codex/Node versions, dependency install state, container digests and immutable model snapshot are not recovered.
- Historical concurrency, timeout, environment overrides and GEPA RNG seeds are not preserved in the inspected search summaries. Recipe values select current documented settings, not proof of the historical launch command.
- No complete optimization token or dollar budget. Retained adapter statistics and reflection usage omit some failed attempts and are not total billed cost.
- The downloadable result bundle does not include executable task environments, gated ALE data, trained checkpoints, full adapted code/state or frozen capability libraries. These assets are required for fresh evaluation.
- A fresh search is stochastic and can select a different winner. Three evaluation repetitions are not three independently optimized harnesses.
- Five iterations and three requested candidates are configured plans, not completed work. Archived stages can be incomplete and retained results overwritten; a complete rerun can spend more than the archived run.

Evidence: `analysis/arms.py`; `evovle_agents/src/scripts/run_meta_harness.sh`; `evovle_agents/meta_harness/splits.py`; `evovle_agents/meta_harness/cl_eval.py`; `evovle_agents/meta_harness/run_stages.py`; `install.md`; `scripts/env.sh`; `reference/gepa/pyproject.toml`; `reference/gepa/uv.lock`; `reference/EnterpriseOps-Gym/pyproject.toml`; `reference/EnterpriseOps-Gym/uv.lock`; `reference/agents-last-exam/pyproject.toml`; `reference/agents-last-exam/uv.lock`; `evovle_agents/meta_harness/config.yaml`; `evovle_agents/meta_harness/skills/meta-harness/SKILL.md`

### agents-gepa — GEPA

Historical rerun status: **partial**.

Prerequisites:

- Obtain the experiment source, benchmark task data and frozen capability libraries. Website CSVs can recompute reported aggregates but cannot execute an agent.
- Follow install.md for local EOG gyms, Docker connectivity, Codex CLI authentication and Python environments. Authenticate with your own credentials; never reuse or publish saved authentication files.
- Run namespace packages from the repository root. scripts/env.sh adds the root, eval_service/sdk (simple_agentic_evals), and reference/gepa/src to PYTHONPATH. Install the reference project dependencies instead of substituting another GEPA version.
- EOG requires the reference EnterpriseOps-Gym runtime and its domain gym containers. Tools also require its ReAct/LangChain stack. Verify gym endpoints before spending the search budget.
- ALE requires the reference/agents-last-exam Python 3.12 environment, gated task-data including grading references, a Linux sandbox image and the historical task eligibility/exclusion snapshot. A current manifest can change the denominator.
- Freeze source, dependency locks, Python/Codex/Node versions, container digests, model identifiers, task/split manifests and library hashes. Current source fingerprints do not identify the historical runtime.

**Prepare an isolated run**

```sh
# Run from a prepared writable experiment checkout, not the website.
set -euo pipefail
test -f scripts/env.sh
source scripts/env.sh
# Retain this tag for resume; use a new tag for each independent search.
export REPRO_TAG="$(date -u +%Y%m%d_%H%M%S)_$$"
export REPRO_RESULTS="$PWD/reproduction/$REPRO_TAG"
mkdir -p "$REPRO_RESULTS"
export EVOVLE_CODEX_MODEL=gpt-5
export EVOVLE_CODEX_TRANSPORT=stdio
export EVOVLE_CODEX_TIMEOUT_SEC=900
export EVOVLE_CODEX_MAX_EPISODES=4
export ALE_WALL_TIME_S=7200
export META_HARNESS_BACKEND=local
export META_HARNESS_CONCURRENCY=8
unset EVOVLE_SKILLS_JOBS_ARM_DIR EVOVLE_AGENTS_JOBS_ARM_DIR
```

New run using inspected current source. EOG timeout 900 seconds, four episodes, stdio transport and concurrency eight are explicit current settings, not established historical overrides. Append --dry-run to a search command to inspect its plan once prerequisites exist; preparation files may still be written. Recipes were source-checked and bash syntax-checked; no benchmark was launched.

**Search and evaluate EOG streams**

```sh
for spec in csm:1,2,3 hr:1,2,3,4 itsm:1,2,3,4; do
  stream=${spec%%:*}
  versions=${spec#*:}
  bash evovle_agents/src/scripts/run_gepa.sh "$stream" \
    --versions "$versions" --model gpt-5 --backend local \
    --concurrency 8 --num-runs 3 --fwt-all \
    --run-name "repro_agents_gepa_${REPRO_TAG}_${stream}" \
    --max-metric-calls 50 --reflection-minibatch-size 3 --trials-per-task 1 --jobs-suffix "_gepa_repro_${REPRO_TAG}" --seed 0 --max-retries 1
done
```

One stage chain per stream, pooled validation, three held-out repetitions and full forward/retention matrix. --fwt-all adds the forward cells; stagewise headline summaries pool j<=k. Fresh output roots/suffixes protect archived results.

**Run ALE with the recorded search repetition schedule**

```sh
bash evovle_agents/src/scripts/run_gepa.sh ale \
  --versions 1,2,3,4,5,6 --model gpt-5 --backend local \
  --concurrency 8 --num-runs 3 --fwt-all \
  --run-name "repro_agents_gepa_${REPRO_TAG}_ale" \
  --max-metric-calls 50 --reflection-minibatch-size 3 --trials-per-task 1 \
  --jobs-suffix "_gepa_repro_${REPRO_TAG}" --seed 0 --max-retries 1
```

Requires the historical ALE eligibility snapshot and corresponding task/library files; current manifests can change split counts and denominators. One search trial/task throughout; --num-runs 3 is held-out evaluation.

**Evaluate an existing checkpoint without another search**

```sh
export REPRO_STREAM=hr
export EVOVLE_AGENTS_JOBS_MODE_SUFFIX="_gepa_eval_repro_${REPRO_TAG}"
python -m evovle_agents.meta_harness.cl_eval \
  --domain "$REPRO_STREAM" \
  --run-name "repro_agents_gepa_${REPRO_TAG}_${REPRO_STREAM}" \
  --model gpt-5 --backend local --concurrency 8 --num-runs 3 --fwt-all

```

HR example reads the newly generated lineage and evaluates into a separate output tree. To evaluate an archived chain, replace --run-name with protocol.search_stages run_name and restore all lineage-linked code/state/library files. Tools also needs your own sanitized model config. This launches fresh stochastic evaluation, not recomputation of archived metrics.

Missing information / conditions:

- No complete historical runtime lock: per-run Python/Codex/Node versions, dependency install state, container digests and immutable model snapshot are not recovered.
- Historical concurrency, timeout, environment overrides and GEPA RNG seeds are not preserved in the inspected search summaries. Recipe values select current documented settings, not proof of the historical launch command.
- No complete optimization token or dollar budget. Retained adapter statistics and reflection usage omit some failed attempts and are not total billed cost.
- The downloadable result bundle does not include executable task environments, gated ALE data, trained checkpoints, full adapted code/state or frozen capability libraries. These assets are required for fresh evaluation.
- A fresh search is stochastic and can select a different winner. Three evaluation repetitions are not three independently optimized harnesses.
- Adjacent max_trial_call150 directories are distinct experiments and excluded from this 50-call arm.

Evidence: `analysis/arms.py`; `evovle_agents/src/scripts/run_gepa.sh`; `evovle_agents/meta_harness/splits.py`; `evovle_agents/meta_harness/cl_eval.py`; `evovle_agents/meta_harness/run_gepa.py`; `install.md`; `scripts/env.sh`; `reference/gepa/pyproject.toml`; `reference/gepa/uv.lock`; `reference/EnterpriseOps-Gym/pyproject.toml`; `reference/EnterpriseOps-Gym/uv.lock`; `reference/agents-last-exam/pyproject.toml`; `reference/agents-last-exam/uv.lock`; `evovle_agents/meta_harness/gepa_reflection.py`; `evovle_agents/meta_harness/gepa_adapter.py`
