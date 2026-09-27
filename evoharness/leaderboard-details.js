/* System cards for the static leaderboard. Recorded results live in static/baselines/. */
const LB_DETAILS = (() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const datasets = () => typeof LB_BASELINE_DATA === "undefined" ? {} : LB_BASELINE_DATA.systems;
  // Identity includes track and experiment type: identical display names can be
  // task-specific controls, deployment runs, or unregistered memory methods.
  function keyFor(axis, row) {
    let key = { GEPA: "gepa", "Meta-Harness": "meta-harness", "Codex memory": "memory", SkillOpt: "skillopt" }[row.name];
    if (row.name === "Codex") key = row.cat === "ref" ? "oracle" : "codex";
    if (row.name === "Claude Code") key = row.cat === "ref" ? "oracle-claude" : "claude";
    if (axis === "tools") {
      if (row.name === "ReAct / Codex") key = row.cat === "ref" ? "oracle" : "react";
      key = { "Raw Memory": "raw-memory", "Reasoning Bank": "reasoning-bank", MemToolAgent: "memtoolagent" }[row.name] || key;
    }
    return key && datasets()[`${axis}-${key}`] ? `${axis}-${key}` : "";
  }
  const familyText = {
    ref: "Task-specific reference: the system receives the capabilities selected for each task instead of adapting to an accumulating pool.",
    deploy: "Frontier deployment: the system is evaluated under an accumulating harness without stage-specific self-evolving adaptation.",
    memory: "Memory-based adaptation: the method carries persistent information between stages of harness evolution.",
    skill: "Skill-learning ablation: the experiment varies the source of the skill library. These rows report EOG only.",
  };
  let current = null;
  let selection = { stream: "", metric: "score", view: "stages" };
  const dialog = () => document.getElementById("lb-system-dialog");
  const body = () => document.querySelector("[data-lb-detail-body]");
  const fmt = (n) => n == null ? "—" : Number(n).toFixed(1);
  const estimate = (r, metric) => `${fmt(r[metric])}<span class="lbd-sd"> ± ${fmt(r[metric + "Sd"])}</span>`;
  const taskCounts = (r) => r.tasks.every(n => n === r.tasks[0]) ? `${r.tasks[0]}` : r.tasks.join(" / ");
  const context = () => {
    const key = current.key || keyFor(current.axis, current.row);
    const results = datasets()[key];
    return { profile: results, key, results };
  };

  function headline() {
    const r = current.row;
    const { results } = context();
    return `<div class="lbd-headlines" aria-label="Evaluation results">${["eog", "ale"].map(env => {
      const a = results?.aggregates[env];
      if (results) return `<div><span>${env.toUpperCase()}</span>${a
        ? `<strong>${fmt(a.pass)}<small>% Pass</small></strong><p>${fmt(a.score)}% Score ± ${fmt(a.scoreSd)}</p>
          <p>${taskCounts(a)} tasks/run · ${a.runs} runs</p>`
        : '<p>No results available</p>'}</div>`;
      return `<div><span>${env.toUpperCase()}</span><strong>${fmt(r[env])}<small>% Pass</small></strong>
        <p>${fmt(r[env + "Score"])}% Score</p></div>`;
    }
    ).join("")}</div>`;
  }

  function settings(profile) {
    const rows = [...profile.settings,
      ["Evaluation coverage", `${profile.evaluationCells} cells; ${profile.evaluationTrials.toLocaleString()} recorded task trials across all stages and runs`, "Evaluation only; excludes search/adaptation"]];
    return `<section class="lbd-section" data-lbd-part="configuration"><h3 tabindex="-1">Configuration and search budget</h3>
      <p class="lbd-help">Settings distinguish recorded experiment values from implementation defaults. Unavailable settings are marked explicitly.</p>
      <dl class="lbd-settings">${rows.map(([label, value, basis]) =>
        `<div><dt>${esc(label)}</dt><dd>${esc(value)}<span class="lbd-basis">${esc(basis)}</span></dd></div>`).join("")}</dl>
      <ul class="lbd-notes">${profile.notes.map(n => `<li>${esc(n)}</li>`).join("")}</ul>
      ${searchBudgetTable(profile)}
    </section>`;
  }

  function searchBudgetTable(profile) {
    const records = profile.searchBudget || profile.reproduction?.protocol?.search_stages;
    if (!records?.length) return "";
    const value = v => v == null ? "—" : esc(Array.isArray(v) ? v.join(" / ") : v);
    return `<details class="lbd-search-budget"><summary>Recorded search work by stream and stage</summary>
      <p>Search repetitions are per validation task for each candidate, separate from the three held-out evaluation runs. Requested budgets are limits or plans; retained trials are the work still present in saved artifacts, not complete billed compute. A dash means not recorded.</p>
      <div class="lbd-table-wrap" tabindex="0" role="region" aria-label="Recorded search budgets by stage"><table class="lbd-table"><thead><tr>
        <th scope="col">Stream</th><th scope="col">Stage</th><th scope="col">Learn tasks</th><th scope="col">Val tasks</th><th scope="col">Trials/task</th><th scope="col">Requested budget</th><th scope="col">Retained trials</th>
      </tr></thead><tbody>${records.map(r => `<tr><th scope="row">${esc(r.domain.toUpperCase())}</th><td>v${r.version}</td>
        <td>${value(r.n_train)}</td><td>${value(r.n_val ?? r.validation_task_counts)}</td><td>${value(r.trials_per_task ?? r.recorded_trials_per_task)}</td>
        <td>${r.searched === false ? "Not searched" : profile.arm === "meta" ? "5 iterations; 3 candidates requested each" : r.max_metric_calls == null ? "—" : `${value(r.max_metric_calls)} metric calls`}</td>
        <td>${value(r.retained_adapter_statistics?.n_trials ?? r.retained_candidate_trials)}</td></tr>`).join("")}</tbody></table></div>
      <p class="lbd-help">Multiple task counts reflect different retained candidates or fallback training sets. Retained validation files may include seed/incumbent evaluations and omit failed or overwritten attempts.</p>
      <p><a href="static/baselines/search-stage-evidence.json" download>Search evidence, validation task IDs &amp; checkpoint hashes (JSON) ↓</a></p>
    </details>`;
  }

  function chart(stream) {
    const metric = selection.metric;
    const values = stream.stages;
    const x = i => values.length === 1 ? 330 : 48 + i * 592 / (values.length - 1);
    const y = v => 166 - v * 1.32;
    const label = metric === "score" ? "Score" : "Pass";
    return `<svg class="lbd-chart" viewBox="0 0 690 207" role="img" aria-label="${esc(stream.label)} ${label} by recorded stage. Exact values and standard deviations are in the table below.">
      ${[0, 25, 50, 75, 100].map(v => `<line x1="48" y1="${y(v)}" x2="650" y2="${y(v)}" class="lbd-grid"/>
        <text x="37" y="${y(v) + 4}" text-anchor="end">${v}%</text>`).join("")}
      <polyline points="${values.map((v, i) => `${x(i)},${y(v[metric])}`).join(" ")}"/>
      ${values.map((v, i) => `<circle cx="${x(i)}" cy="${y(v[metric])}" r="4"><title>Stage ${v.stage}: ${fmt(v[metric])}% ± ${fmt(v[metric + "Sd"])}%</title></circle>
        <text x="${x(i)}" y="${y(v[metric]) - 12}" text-anchor="middle" class="lbd-value">${fmt(v[metric])}</text>
        <text x="${x(i)}" y="190" text-anchor="middle">v${v.stage}</text>`).join("")}
    </svg>`;
  }

  function stageTable(stream) {
    const label = selection.metric === "score" ? "Score" : "Pass";
    const control = context().results.kind === "control";
    return `${chart(stream)}<div class="lbd-table-wrap" tabindex="0" role="region" aria-label="Results after each stage">
      <table class="lbd-table"><caption>${control ? "Each point evaluates that cohort with its reference harness. Cohorts are not accumulated." : "At stage k, pool the recorded evaluations on seen cohorts j ≤ k. No missing stages are inferred."}</caption>
        <thead><tr><th scope="col">${control ? "Cohort" : "Stage"}</th><th scope="col">${label} (%) ± SD</th><th scope="col">Tasks / run</th><th scope="col">Runs</th><th scope="col">Eval cohorts</th></tr></thead>
        <tbody>${stream.stages.map(r => `<tr><th scope="row">v${r.stage}</th><td>${estimate(r, selection.metric)}</td>
          <td>${taskCounts(r)}</td><td>${r.runs}</td><td>${r.cohorts.map(j => `v${j}`).join(", ")}</td></tr>`).join("")}</tbody></table></div>`;
  }

  function matrixTable(stream) {
    const stages = stream.adaptStages;
    const cohorts = stream.cohorts;
    const control = context().results.kind === "control";
    const cells = new Map(stream.cells.map(c => [`${c.stage}:${c.cohort}`, c]));
    return `<div class="lbd-matrix-key"><span class="is-diagonal">Same cohort</span><span>Earlier cohort</span><span class="is-forward">Forward evaluation</span></div>
      <div class="lbd-table-wrap" tabindex="0" role="region" aria-label="Full stage evaluation matrix">
      <table class="lbd-table lbd-matrix"><caption>${control ? "Reference controls evaluate matching cohorts only; off-diagonal cells are not cumulative experiments." : "R[k, j]: harness at stage k, evaluated on task cohort j."} Values are ${selection.metric === "score" ? "Score" : "Pass"} (%) ± SD.</caption>
        <thead><tr><th scope="col">${control ? "Cohort" : "Stage"} ↓ / Eval →</th>${cohorts.map(j => `<th scope="col">v${j}</th>`).join("")}</tr></thead>
        <tbody>${stages.map(k => `<tr><th scope="row">v${k}</th>${cohorts.map(j => {
          const r = cells.get(`${k}:${j}`);
          return r ? `<td class="${k === j ? "is-diagonal" : j > k ? "is-forward" : ""}">${estimate(r, selection.metric)}
            <small>${taskCounts(r)} tasks/run${j > k ? " · forward" : ""}</small></td>`
            : '<td class="lbd-missing" aria-label="Not evaluated">—</td>';
        }).join("")}</tr>`).join("")}</tbody></table></div>
        <p class="lbd-help">Forward cells evaluate a later cohort before adaptation to it. They are excluded from the stage summary. A dash means no recorded evaluation.</p>`;
  }

  function renderResults() {
    const { results } = context();
    if (!results) return;
    const stream = results.streams[selection.stream];
    const incomplete = (selection.view === "matrix" ? stream.cells : stream.stages)
      .filter(r => r.runs !== 3 || !r.tasks.every(n => n === r.tasks[0]));
    const host = body().querySelector("[data-lbd-results]");
    host.innerHTML = `<p class="lbd-result-title">${esc(stream.label)} · ${selection.metric === "score" ? "Partial-credit score" : "Strict task pass rate"}</p>
      ${selection.view === "matrix" ? matrixTable(stream) : stageTable(stream)}
      ${incomplete.length ? `<p class="lbd-notice"><b>Incomplete records.</b> ${incomplete.map(r =>
        `v${r.stage}${r.cohort ? ` → cohort v${r.cohort}` : ""}: ${r.tasks.join(" / ")} tasks in runs ${r.runIds.join(" / ")}`).join("; ")}.
        Missing task records are not filled with zeros; compare these cells with care.</p>` : ""}`;
  }

  function resultsSection(key, results) {
    const entries = Object.entries(results.streams);
    selection.stream = entries.find(([, s]) => s.benchmark === "eog")?.[0] || entries[0][0];
    return `<section class="lbd-section" data-lbd-part="results"><div class="lbd-section-head"><h3 tabindex="-1">Results by stream and stage</h3><span class="lbd-snapshot">August 2026 snapshot</span></div>
      <p class="lbd-help">Score gives partial credit; Pass counts fully solved tasks. Values average evaluation runs 1–3 of the recorded harness. ± is population standard deviation across runs; these are not independent adaptation searches.</p>
      <div class="lbd-controls">
        <label>Stream<select data-lbd-control="stream">${["eog", "ale"].map(env => `<optgroup label="${env.toUpperCase()}">${entries.filter(([, s]) => s.benchmark === env)
          .map(([id, s]) => `<option value="${id}"${id === selection.stream ? " selected" : ""}>${esc(s.label)}</option>`).join("")}</optgroup>`).join("")}</select></label>
        <label>Metric<select data-lbd-control="metric"><option value="score">Score (%)</option><option value="pass">Pass (%)</option></select></label>
        <label>View<select data-lbd-control="view"><option value="stages">${results.kind === "control" ? "By cohort" : "After each stage"}</option><option value="matrix">Full evaluation matrix</option></select></label>
      </div>
      <p class="lbd-help">${results.kind === "control" ? "Reference controls report each cohort separately. The benchmark aggregate above pools all these cohorts." : "The stage summary weights recorded seen tasks equally within a run, then averages runs. It differs from ACC that weights each cohort equally. The benchmark aggregate uses each stream’s final recorded stage."}</p>
      <div data-lbd-results aria-live="polite" aria-atomic="false"></div>
      <div class="lbd-downloads"><b>Download all streams for this system</b>
        <a href="static/baselines/${key}-stages.csv" download>Stage summary CSV ↓</a>
        <a href="static/baselines/${key}-matrix.csv" download>Full matrix CSV ↓</a>
        <a href="static/baselines/${key}-runs.csv" download>Individual runs CSV ↓</a>
        <a href="static/baselines/${key}-trials.csv" download>Counted tasks &amp; outcomes CSV ↓</a>
        <a href="static/baselines/${key}-configuration.json" download>Configuration JSON ↓</a></div>
    </section>`;
  }

  function open(info) {
    current = info;
    selection = { stream: "", metric: "score", view: "stages" };
    const { profile, key, results } = context();
    document.getElementById("lb-system-title").textContent = info.row?.name || results.name;
    body().innerHTML = `<p class="lbd-eyebrow">Evolving ${esc(info.axis)}</p>
      <p class="lbd-description">${esc(profile?.description || familyText[info.row?.cat] || "Reported baseline system.")}</p>
      <div class="lbd-tags"><span>${esc(profile?.model || info.model)}</span><span>${esc(profile?.harness || info.harness)}</span>${profile?.kind === "control" || info.row?.ref ? "<span>Reference control</span>" : ""}</div>
      ${results ? `<nav class="lbd-jumps" aria-label="System detail sections">
        <button type="button" data-lbd-jump="configuration">Configuration &amp; budgets ↓</button>
        <button type="button" data-lbd-jump="results">Stream &amp; stage results ↓</button></nav>` : ""}
      ${headline()}
      ${relatedExperiments(key)}
      ${profile ? settings(profile) : `<section class="lbd-section"><h3>Reported setup</h3>
        <p>The leaderboard reports <b>${esc(info.model)}</b> in <b>${esc(info.harness)}</b>, with three evaluation runs and population standard deviations.
          ${info.row.cat === "skill" ? "The appendix does not state the task count for this ablation." : `The ${esc(info.axis)} track contains ${RESULTS[info.axis].tasks.eog} EOG and ${RESULTS[info.axis].tasks.ale} ALE evaluation tasks.`}</p>
        <p class="lbd-help">Detailed configuration and stage-level results are not available for this system.</p></section>`}
      ${results ? resultsSection(key, results) : ""}`;
    if (results) renderResults();
    const dlg = dialog();
    if (!dlg.open) dlg.showModal();
    body().scrollTop = 0;
    dlg.querySelector("[data-lbd-close]").focus();
  }

  function openExperiment(key) {
    const result = datasets()[key];
    if (result) open({ key, axis: result.track });
  }

  function relatedExperiments(key) {
    const related = { "tools-react": "tools-react-ale-v", "skills-oracle": "skills-oracle-gpt55", "skills-gepa": "skills-gepa-oracle" }[key];
    if (!related || !datasets()[related]) return "";
    return `<p class="lbd-help">Related run: <button type="button" class="lbd-inline" data-lbd-experiment="${related}">${esc(datasets()[related].name)} ↗</button></p>`;
  }

  function init() {
    const dlg = dialog();
    if (!dlg) return;
    dlg.querySelector("[data-lbd-close]").addEventListener("click", () => dlg.close());
    // Native dialog provides Escape, focus trapping, and return to the trigger.
    let startedOutside = false;
    const outside = e => {
      const r = dlg.getBoundingClientRect();
      return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
    };
    dlg.addEventListener("pointerdown", e => { startedOutside = e.target === dlg && outside(e); });
    dlg.addEventListener("click", e => {
      if (startedOutside && e.target === dlg && outside(e)) dlg.close();
      startedOutside = false;
    });
    body().addEventListener("change", e => {
      const control = e.target.closest("[data-lbd-control]");
      if (!control) return;
      selection[control.dataset.lbdControl] = control.value;
      renderResults();
    });
    body().addEventListener("click", e => {
      const experiment = e.target.closest("[data-lbd-experiment]");
      if (experiment) { openExperiment(experiment.dataset.lbdExperiment); return; }
      const button = e.target.closest("[data-lbd-jump]");
      if (!button) return;
      const section = body().querySelector(`[data-lbd-part="${button.dataset.lbdJump}"]`);
      section.querySelector("h3").focus({ preventScroll: true });
      section.scrollIntoView({ block: "start" });
    });
  }
  return { init, open, keyFor };
})();
