const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const DB = (() => {
  const ORDER = ["tools", "skills", "agents"];
  const TRACKS = {
    tools: {
      label: "Tools",
      blurb: "Deterministic build, no LLM: rank tools by <b>how many tasks use them</b>, grow nested versions T<sub>1</sub> &sub; T<sub>2</sub> &sub; T<sub>3</sub>, then place each task at the <b>earliest version that covers all its tools</b>.",
      seedNote: "one domain &rarr; many tasks &middot; each task wires several tools",
      benchNote: 'fixed tool set at T<sub>i</sub> &middot; a <b class="db-ink">new tool</b> expands it at T<sub>i+1</sub>',
      chipKind: "tool",
      feats: [
        "Every task uses <b>&ge;1 new tool</b> plus at least one carried-forward tool.",
        "Versions T<sub>i</sub> are cut from the seed by tool-usage <b>frequency</b>.",
      ],
    },
    skills: {
      label: "Skills",
      blurb: "Deterministic build, no LLM: procedural content is <b>mined from prompts</b> into a hidden reference library, matched to tasks via verifier keywords, then released from <b>core to long tail</b>. At test time the agent must <b>retrieve</b> skills from the growing pool.",
      seedNote: "skills are hidden from the system prompt &middot; oracle tools are given to isolate the effect",
      benchNote: 'tasks at T<sub>i</sub> need a <b class="db-ink">skill new at that version</b> &middot; older skills optional',
      chipKind: "skill",
      feats: [
        "Skills are <b>latent</b>: needed to solve the task but never shown.",
        "Oracle tools are provided, so we measure the <b>skill</b>, not tool discovery.",
        "Each task requires a skill <b>new at its time step</b>.",
      ],
    },
    agents: {
      label: "Agents",
      blurb: "Deterministic build, no LLM: tools are bundled by the <b>entity they operate on</b> into specialist agents. A tool-less lead receives the <b>full cumulative pool</b> and must select, delegate, and coordinate.",
      seedNote: "tools that share an owner become one specialist &middot; the lead has no direct tools",
      benchNote: 'fixed agent set at T<sub>i</sub> &middot; a <b class="db-ink">new agent</b> expands it at T<sub>i+1</sub>',
      chipKind: "agent",
      feats: [
        "Specialists are <b>entity-scoped</b> bundles of tools (and related procedures).",
        "The lead must <b>delegate</b> into a growing pool of specialists.",
        "Every task uses <b>&ge;1 agent new at its version</b>.",
      ],
    },
  };

  let mounted = false;
  let active = "tools";

  // ----- Tools track: a precise, animated walk-through of the frequency split.
  // A tiny worked example (a calendar-like domain) instantiates the real
  // algorithm from evolve_tools/src/frequency_config.py so a first-time reader
  // can see EXACTLY how tasks are sliced into versions by tool-usage frequency:
  //   (1) every task carries the set of tools it needs;
  //   (2) pool all tools, rank by how many tasks use each (core -> long tail);
  //   (3) grow nested catalogs T1 c T2 c T3 (add the next-most-frequent tools);
  //   (4) assign every task to the EARLIEST version that covers all its tools.
  const TC = {
    create_event: "#2563eb",
    list_events:  "#0ea5e9",
    find_slot:    "#6366f1",
    send_invite:  "#d97706",
    delete_event: "#dc2626",
  };
  // Tools sorted by descending task-frequency (ties alphabetical) == rank order.
  // `ver` = the version (0-based) that first introduces the tool.
  const T_TOOLS = [
    { id: "create_event", freq: 5, ver: 0 },
    { id: "list_events",  freq: 3, ver: 0 },
    { id: "find_slot",    freq: 2, ver: 1 },
    { id: "send_invite",  freq: 2, ver: 1 },
    { id: "delete_event", freq: 1, ver: 2 },
  ];
  // Each task's oracle tool set. `ver` = earliest version that covers all of
  // its tools (so >=1 of them is new at `ver`; the rest are carried-forward).
  const T_TASKS = [
    { id: "A", tools: ["create_event", "list_events"], ver: 0 },
    { id: "B", tools: ["create_event", "list_events", "send_invite"], ver: 1 },
    { id: "C", tools: ["create_event", "find_slot"], ver: 1 },
    { id: "D", tools: ["create_event", "list_events", "find_slot"], ver: 1 },
    { id: "E", tools: ["create_event", "send_invite", "delete_event"], ver: 2 },
  ];
  const T_VERS = [
    { tag: "T₁", delta: ["create_event", "list_events"] },
    { tag: "T₂", delta: ["find_slot", "send_invite"] },
    { tag: "T₃", delta: ["delete_event"] },
  ];
  // version each tool is introduced at — used to label a task's tools new/old.
  const T_TOOLVER = Object.fromEntries(T_TOOLS.map((t) => [t.id, t.ver]));
  const T_STEPS = [
    "tasks need tools",
    "rank by frequency",
    "cut cumulative versions",
    "assign to earliest version",
  ];
  const T_CAPS = [
    "Start from the seed: every task carries the <b>set of tools</b> it needs to be solved.",
    "Pool all tools and count <b>how many tasks use each</b>, then rank them most-used &rarr; long tail (ties broken alphabetically).",
    "Grow a nested chain <b>T₁ &sub; T₂ &sub; T₃</b> by adding the next-most-frequent tools — but <b>where to cut</b> is set by the <b>min_new_tasks</b> floor: <b>T₁ is the smallest prefix that makes ≥ N tasks solvable</b> (here N=1 — the top-2 tools first make a whole task, Task A, solvable), then each later version grows until <b>≥ N new</b> tasks clear.",
    "Place each task at the <b>earliest version</b> that covers <b>all</b> its tools — now read off the guarantee: each task has <b>≥1 new</b> tool (new at its version) and, from T₂ on, also <b>≥1 old</b> carried-forward tool.",
  ];
  // What the construction guarantees (from the dataset card + environment.py).
  const T_FEATS = [
    "<b>Every task uses ≥1 new tool</b> (the one new at its version) — and from <b>T₂ onward</b> also <b>≥1 old tool</b> carried forward, so each version tests mixing new APIs with known ones.",
    "<b>Tools only accumulate</b>: T₁ &sub; T₂ &sub; T₃ — nothing is ever removed, and the tools added each version are the most-frequent of what remains.",
    "<b>Every new tool is exercised</b> at the version it appears, and per-task difficulty (|tools|) is balanced across versions so a version's effect isolates tool novelty.",
    "<b>Cuts are principled, not arbitrary</b>: each version is the <b>smallest frequency-prefix</b> that clears the <b>min_new_tasks</b> floor (≥ N newly-solvable tasks). In the real benchmark N=7, first met at the <b>top-40</b> tools ⟹ <b>C₁ = 40</b> — the smallest first version that can host 7 whole composite tasks.",
  ];

  function tchip(id, opts) {
    opts = opts || {};
    const c = TC[id] || "var(--accent)";
    const cls = "dbt-tool" + (opts.muted ? " is-muted" : "");
    const n = opts.count != null
      ? `<b class="dbt-tool-n">&times;${opts.count}</b>` : "";
    return `<span class="${cls}" style="--tc:${c}">${id}${n}</span>`;
  }
  // Tool chip tagged new/old relative to a task's assigned version. `old`
  // (carried-forward) chips are muted just like in step 3; `new` chips keep
  // the tool colour — so the new+old guarantee is readable at a glance.
  function tchipNO(id, isOld) {
    const c = TC[id] || "var(--accent)";
    return `<span class="dbt-tool${isOld ? " is-muted" : ""}" style="--tc:${c}">${id}` +
      `<b class="dbt-flag dbt-flag--${isOld ? "old" : "new"}">${isOld ? "old" : "new"}</b></span>`;
  }

  function toolsPanelHTML() {
    const maxF = Math.max.apply(null, T_TOOLS.map((t) => t.freq));

    const p1 = `<div class="dbt-phase dbt-p1"><div class="dbt-tasklist">${
      T_TASKS.map((t) =>
        `<div class="dbt-task"><span class="dbt-task-tag">Task ${t.id}</span>` +
        `<span class="dbt-task-tools">${t.tools.map((id) => tchip(id)).join("")}</span></div>`
      ).join("")
    }</div></div>`;

    const p2 = `<div class="dbt-phase dbt-p2"><div class="dbt-rank">${
      T_TOOLS.map((t) =>
        `<div class="dbt-rankrow">` +
        `<span class="dbt-rank-name" style="--tc:${TC[t.id]}">${t.id}</span>` +
        `<span class="dbt-rank-track"><span class="dbt-rank-bar" style="--tc:${TC[t.id]};--w:${Math.round(t.freq / maxF * 100)}%"></span></span>` +
        `<span class="dbt-rank-cnt">${t.freq} task${t.freq > 1 ? "s" : ""}</span>` +
        `</div>`
      ).join("")
    }</div><div class="dbt-rank-axis"><span>core &middot; most-used</span><span>long tail</span></div></div>`;

    // phase 3 — cut cumulative versions. WHERE each version stops is set by the
    // min_new_tasks FLOOR: V1 = the smallest frequency-prefix that makes >= N
    // tasks SOLVABLE (all of a task's tools present); each later version then
    // grows the prefix until >= N NEW tasks become solvable. Toy floor N=1; the
    // real benchmark uses min_new_tasks_per_stage = 7 (-> C1 = 40 tools).
    const p3seen = new Set();
    const p3rows = T_VERS.map((v, k) => {
      const cum = T_TOOLS.filter((t) => t.ver <= k);
      const have = new Set(cum.map((t) => t.id));
      const solv = T_TASKS.filter((t) => t.tools.every((x) => have.has(x)));
      const fresh = solv.filter((t) => !p3seen.has(t.id));
      solv.forEach((t) => p3seen.add(t.id));
      const freshChips = fresh.length
        ? fresh.map((t) => `<i class="dbt-solv-chip">Task ${t.id}</i>`).join("")
        : `<i class="dbt-solv-chip is-none">none</i>`;
      const badge = k === 0
        ? `<span class="dbt-cut-badge dbt-cut-badge--floor">${solv.length} &ge; floor (N=1) &rarr; smallest first version</span>`
        : `<span class="dbt-cut-badge">+${fresh.length} new &middot; ${solv.length}/${T_TASKS.length} solvable</span>`;
      const main = `<div class="dbt-cat"><span class="dbt-cat-tag">${v.tag}</span>` +
        `<span class="dbt-cat-tools">${cum.map((t) => tchip(t.id, { muted: t.ver < k })).join("")}</span>` +
        `<span class="dbt-cat-delta">${k === 0 ? "core catalog" : "+ " + v.delta.join(", ")}</span></div>`;
      const sub = `<div class="dbt-cut-sub"><span class="dbt-cut-arrow">&#8627;</span> newly solvable: ${freshChips} ${badge}</div>`;
      return `<div class="dbt-cutrow">${main}${sub}</div>`;
    }).join("");
    const p3 = `<div class="dbt-phase dbt-p3">` +
      `<div class="dbt-rulebar">Where to <b>cut</b> each version is set by the <b>min_new_tasks</b> floor: <b>V₁ is the smallest frequency-prefix that makes ≥ N tasks solvable</b>, and every later version grows the prefix until <b>≥ N new</b> tasks become solvable. <i>(toy floor N=1)</i></div>` +
      `<div class="dbt-cats dbt-cats--cut">${p3rows}</div>` +
      `<div class="dbt-foot">Can't cut smaller — the <b>top-1</b> prefix <code>{create_event}</code> leaves <b>0</b> solvable tasks, below the floor. In the real benchmark the floor is <b>min_new_tasks = 7</b>, first reached only once the <b>top-40</b> tools are on &rArr; <b>C₁ = 40</b>: the smallest possible first version that can host 7 whole composite tasks.</div>` +
      `</div>`;

    const p4 = `<div class="dbt-phase dbt-p4"><div class="dbt-assign">${
      T_VERS.map((v, k) => {
        const inV = T_TASKS.filter((t) => t.ver === k);
        return `<div class="dbt-asg-ver"><span class="dbt-asg-tag">${v.tag}</span><div class="dbt-asg-tasks">${
          inV.map((t) => {
            const chips = t.tools.map((id) => tchipNO(id, T_TOOLVER[id] < t.ver)).join("");
            const nNew = t.tools.filter((id) => T_TOOLVER[id] === t.ver).length;
            const nOld = t.tools.length - nNew;
            const sum = nOld > 0 ? `${nNew} new + ${nOld} old` : `${nNew} new &middot; core`;
            return `<div class="dbt-asg-task"><span class="dbt-asg-name">Task ${t.id}</span>` +
              `<span class="dbt-asg-tools">${chips}</span>` +
              `<span class="dbt-asg-sum">${sum}</span></div>`;
          }).join("")
        }</div></div>`;
      }).join("")
    }</div></div>`;

    return `
      <div class="db-panel${active === "tools" ? " is-active" : ""}" data-panel="tools">
        <div class="dbt" data-phase="1">
          <div class="dbt-bar">
            <ol class="dbt-steps">${
              T_STEPS.map((s, i) =>
                `<li data-step="${i + 1}" role="button" tabindex="0" title="Click to study this step"><b>${i + 1}</b>${s}</li>`
              ).join("")
            }</ol>
            <button class="dbt-play" type="button" data-playing="true" title="Pause" aria-label="Pause or play the walk-through"></button>
          </div>
          <div class="dbt-stage">${p1}${p2}${p3}${p4}</div>
          <div class="dbt-caps">${
            T_CAPS.map((c, i) => `<p data-cap="${i + 1}">${c}</p>`).join("")
          }</div>
          <div class="dbt-feats">
            <span class="dbt-feats-k">Guarantee</span>
            <ul>${T_FEATS.map((f) => `<li>${f}</li>`).join("")}</ul>
          </div>
          <!-- Entry point into the full built-dataset detail page (the former
               top-nav "Benchmark" view): statistics, example tasks, and the
               real-world-fit assessment. Routes to the #datasets view. -->
          <a class="dbt-cta" href="#stats">
            <span class="dbt-cta-k">Scale</span>
            <span class="dbt-cta-tx">
              <b>17 streams · 802 tasks · 520 tools · 42 skills · 62 agents</b>
              <i>Jump to benchmark statistics</i>
            </span>
            <span class="dbt-cta-arrow" aria-hidden="true">&rarr;</span>
          </a>
        </div>
      </div>`;
  }

  // =====================================================================
  // Skills track walk-through. DIFFERENT from tools — mirrors
  // evovle_skills/builder (splitter + tagger + sequencer):
  //   * skills are LATENT: the system-prompt policy is split into an oracle
  //     skill library and HELD OUT; the agent starts empty and must author
  //     its own skills (oracle TOOLS are given, to isolate the skill).
  //   * a task is tagged to a skill from its VERIFIER signature, not tools.
  //   * versions grow by SKILL COVERAGE (most-covered first), adding skills
  //     until >= min-step-size NEW tasks become solvable (default 15) — NOT
  //     a frequency size-schedule like tools.
  //   * each task needs >=1 skill NEW at its version; OLD skills optional.
  // The worked example below is internally consistent with that algorithm
  // (coverage order == intro order; earliest-covering placement).
  const SC = {
    "employee-records": "#6366f1",
    "leave-management": "#8b5cf6",
    "payroll": "#0ea5e9",
    "benefits": "#14b8a6",
    "offboarding": "#d97706",
    "compliance": "#dc2626",
  };
  const S_SKILLS = [ // sorted by descending task coverage == version intro order
    { id: "employee-records", cov: 5, ver: 0 },
    { id: "leave-management", cov: 4, ver: 0 },
    { id: "benefits", cov: 3, ver: 1 },
    { id: "payroll", cov: 3, ver: 1 },
    { id: "offboarding", cov: 2, ver: 2 },
    { id: "compliance", cov: 2, ver: 2 },
  ];
  const S_SKILLVER = Object.fromEntries(S_SKILLS.map((s) => [s.id, s.ver]));
  const S_TASKS = [
    { id: "A", skills: ["employee-records"], ver: 0 },
    { id: "B", skills: ["employee-records", "leave-management"], ver: 0 },
    { id: "C", skills: ["leave-management"], ver: 0 },
    { id: "D", skills: ["employee-records", "payroll"], ver: 1 },
    { id: "E", skills: ["leave-management", "benefits"], ver: 1 },
    { id: "F", skills: ["employee-records", "payroll", "benefits"], ver: 1 },
    { id: "G", skills: ["employee-records", "payroll", "offboarding"], ver: 2 },
    { id: "H", skills: ["leave-management", "benefits", "compliance"], ver: 2 },
    { id: "I", skills: ["offboarding", "compliance"], ver: 2 },
  ];
  const S_VERS = [
    { tag: "T₁", delta: ["employee-records", "leave-management"] },
    { tag: "T₂", delta: ["benefits", "payroll"] },
    { tag: "T₃", delta: ["offboarding", "compliance"] },
  ];
  const S_STEPS = [
    "hide policy &rarr; oracle skills",
    "tag tasks &rarr; skills",
    "order by coverage, grow versions",
    "assign &middot; &ge;1 new skill",
  ];
  const S_CAPS = [
    "A deterministic <b>title-keyword</b> rule (no LLM) routes each <b>§</b> three ways: the <b>behavioural contract</b> stays in the stripped prompt; <b>procedure</b> + <b>reference/authority</b> become <b>hidden oracle skills</b>; <b>glossaries</b> are dropped from the prompt and used only to build the tagging universe. Anything unrecognized <b>defaults to a skill</b> — so the keep/hide line is a heuristic, not a semantic judgement. (Oracle <b>tools are given</b>, to isolate the skill.)",
    "Tagging is deterministic: parse a task's <b>verifier SQL</b> into a signature of <b>table.column</b> and <b>table.column = value</b> tokens, then match it against each skill's <b>index</b>. A table-qualified <b>value pair</b> is strong evidence (&times;3); a bare column is weak (&times;1) — tag when the score clears the bar, or on any pair hit. (Note `leave_request.status` vs `employee.status` — the table disambiguates.)",
    "Sort skills by <b>task coverage</b>, then sweep them in that order; after each skill, count the tasks that <b>just became fully solvable</b>. The moment that count reaches <b>min-step-size</b>, <b>cut a version</b> — so <b>how many skills land in a T is derived</b> from when enough new tasks unlock, not chosen. Coverage-greedy, <b>not</b> a frequency schedule like tools.",
    "Place each task at the <b>earliest version</b> covering all its skills — so every task needs <b>&ge;1 skill new at its version</b>, while <b>old skills are optional</b> (e.g. Task I lands at T₃ needing only new skills).",
  ];
  const S_FEATS = [
    "<b>Skills are latent</b>: the policy is stripped from the prompt and held out as an answer key — the agent must <b>author</b> its own skills (skill.write) to solve tasks.",
    "<b>Versions grow by coverage, not frequency</b>: skills are added most-covered-first until <b>&ge; min-step-size</b> new tasks become solvable (15 in the real build); cumulative S₁ &sub; S₂ &sub; S₃.",
    "<b>Every task needs ≥1 new skill</b> (new at its version); <b>older skills are optional</b>. <b>Oracle tools are provided</b>, so the metric isolates skill generation — not tool discovery.",
  ];

  // Step 1 — how the splitter classifies each system-prompt section (by title
  // keyword): Contract + Glossary are KEPT in the stripped prompt; Procedure +
  // Reference are EXTRACTED as hidden skills.
  const S_SECTIONS = [
    { t: "General instructions", cls: "Contract", bin: "keep",
      ex: "“Confirm before any destructive action; never expose another user’s PII.”" },
    { t: "Operational constraints", cls: "Contract", bin: "keep",
      ex: "“Act only within the caller’s region; return ≤ 50 rows per query.”" },
    { t: "Employee records", cls: "Procedure", bin: "skill", skill: "employee-records",
      ex: "“To onboard: insert employee, set status = active, assign a manager_id.”" },
    { t: "Leave management", cls: "Procedure", bin: "skill", skill: "leave-management",
      ex: "“Approve only if balance ≥ days requested, then set status = approved.”" },
    { t: "Benefits enrollment", cls: "Procedure", bin: "skill", skill: "benefits",
      ex: "“During the window, create an enrollment; set plan_tier from salary band.”" },
    { t: "Payroll run", cls: "Procedure", bin: "skill", skill: "payroll",
      ex: "“Lock timesheets, compute gross − deductions, then mark the run = posted.”" },
    { t: "Offboarding", cls: "Procedure", bin: "skill", skill: "offboarding",
      ex: "“Revoke access, set status = terminated, and schedule final pay.”" },
    { t: "Compliance & access", cls: "Reference", bin: "skill", skill: "compliance",
      ex: "“Only HR-Admin may edit compensation; managers have read-only access.”" },
    { t: "Predefined lists / enums", cls: "Glossary", bin: "tag",
      ex: "leave_request.status ∈ { pending, approved, rejected }" },
  ];
  // Step 2 — one worked verifier→signature→match example (the tagger weights a
  // table-qualified (col=val) pair ×3 and a bare (table.col) ×1; tag if score≥3
  // or any pair hit). Task C's verifier disambiguates `status` via its table.
  const S_TAG_EX = {
    task: "C",
    sql: "SELECT COUNT(*) FROM leave_request\nWHERE status = 'approved';",
    sig: [
      { tok: "leave_request.status", kind: "col" },
      { tok: "leave_request.status = approved", kind: "pair" },
    ],
    cand: [
      { skill: "leave-management", idx: ["leave_request.status", "leave_request.status=approved"], score: "3", tag: true },
      { skill: "employee-records", idx: ["employee.status", "employee.dept"], score: "0", tag: false },
    ],
  };
  // Step 3 — illustrative min-step-size for the worked example (15 in the real build).
  const S_THRESH = 3;

  function schip(id, opts) {
    opts = opts || {};
    const c = SC[id] || "var(--accent-2)";
    const n = opts.count != null ? `<b class="dbt-tool-n">&times;${opts.count}</b>` : "";
    return `<span class="dbt-skill${opts.muted ? " is-muted" : ""}" style="--tc:${c}">${id}${n}</span>`;
  }
  function schipNO(id, isOld) {
    const c = SC[id] || "var(--accent-2)";
    return `<span class="dbt-skill${isOld ? " is-muted" : ""}" style="--tc:${c}">${id}` +
      `<b class="dbt-flag dbt-flag--${isOld ? "old" : "new"}">${isOld ? "old" : "new"}</b></span>`;
  }

  // Replay the sequencer's greedy version-cut so the trace is faithful: walk
  // skills in coverage order, add one at a time, count newly-solvable unplaced
  // tasks, and cut a version once that count reaches `thresh`.
  function computeGreedy(thresh) {
    const order = S_SKILLS.map((s) => s.id);
    const placed = new Set();
    const cum = new Set();
    const steps = [];
    let verIdx = 0, skillsThisVer = 0;
    order.forEach((sk, i) => {
      cum.add(sk);
      skillsThisVer += 1;
      const elig = S_TASKS.filter((t) => !placed.has(t.id) && t.skills.every((x) => cum.has(x)));
      const last = i === order.length - 1;
      const step = { skill: sk, count: elig.length, cut: null };
      if (elig.length >= thresh || last) {
        elig.forEach((t) => placed.add(t.id));
        verIdx += 1;
        step.cut = { tag: (S_VERS[verIdx - 1] || {}).tag || ("T" + verIdx), nSkills: skillsThisVer, nTasks: elig.length };
        skillsThisVer = 0;
      }
      steps.push(step);
    });
    return steps;
  }

  function skillsPanelHTML() {
    // phase 1 — classify each § (by title) into KEEP (stripped prompt) vs HIDE
    // (oracle skill), and say why.
    const secRow = (s) => {
      let right;
      if (s.bin === "keep") right = `<span class="dbt-badge dbt-badge--keep">${s.cls}</span>`;
      else if (s.bin === "skill") right = `<span class="dbt-badge dbt-badge--skill">${s.cls}</span><span class="dbt-sec-arrow">&rarr;</span>${schip(s.skill)}`;
      else right = `<span class="dbt-badge dbt-badge--tag">${s.cls}</span>`;
      return `<div class="dbt-sec"><div class="dbt-sec-top"><span class="dbt-sec-t">&sect; ${s.t}</span>${right}</div>` +
        `<div class="dbt-sec-ex">${s.ex}</div></div>`;
    };
    const keptRows = S_SECTIONS.filter((s) => s.bin === "keep").map(secRow).join("");
    const skillRows = S_SECTIONS.filter((s) => s.bin === "skill").map(secRow).join("");
    const tagRows = S_SECTIONS.filter((s) => s.bin === "tag").map(secRow).join("");
    // the bins are carved out of ONE document — the EOG system prompt — so show
    // that source first, then split it.
    const srcSecs = S_SECTIONS.map((s, i) =>
      `<li><span class="dbt-src-num">&sect;${i + 1}</span> ${s.t}</li>`).join("");
    const p1 = `<div class="dbt-phase dbt-p1">` +
      `<figure class="dbt-src"><figcaption class="dbt-src-cap"><span class="db-cap-k">Source</span> EnterpriseOps-Gym — one <b>system prompt</b> (numbered policy sections)</figcaption>` +
        `<div class="dbt-src-doc"><div class="dbt-src-title"># Operating policy</div><ol class="dbt-src-secs">${srcSecs}</ol></div></figure>` +
      `<div class="dbt-splitar"><span class="dbt-splitar-line"></span>` +
        `<span class="dbt-splitar-lab">A deterministic rule splits this prompt: <b>match each &sect;'s title</b> by keyword (no LLM, no content analysis) and route it <b>three ways</b> &darr;</span></div>` +
      `<div class="dbt-route">` +
        `<div class="dbt-route-l">` +
          `<div class="dbt-bin dbt-bin--keep"><div class="dbt-bin-h"><span class="dbt-bin-k dbt-bin-k--keep">KEEP</span> Contract &rarr; stripped prompt (agent sees this)</div>${keptRows}</div>` +
          `<div class="dbt-bin dbt-bin--tag dbt-drop"><div class="dbt-bin-h"><span class="dbt-bin-k dbt-bin-k--tag">DROP</span> Glossary &rarr; not shown to the agent; parsed only to build the verifier-tagging universe (step 2)</div>${tagRows}</div>` +
        `</div>` +
        `<div class="dbt-bin dbt-bin--skill"><div class="dbt-bin-h"><span class="dbt-bin-k dbt-bin-k--skill">HIDE</span> Procedure + Reference &rarr; oracle skills (held out)</div>${skillRows}</div>` +
      `</div>` +
      `<div class="dbt-foot">Because it's title-based, the line is <b>fuzzy</b>: an <i>Operational constraints</i> block is kept, yet <b>access-scope authority</b> becomes a skill — any constraint written <i>inside</i> a procedure rides along into that skill, and a title matching <b>no</b> rule <b>defaults to a skill</b>.</div>` +
      `</div>`;

    // phase 2 — HOW tagging works: parse a verifier's SQL into a signature and
    // match it against each skill's index (pair = strong evidence).
    const ex = S_TAG_EX;
    const sigChips = ex.sig.map((s) =>
      `<span class="dbt-sig dbt-sig--${s.kind}">${s.tok}<b>${s.kind === "pair" ? "pair &times;3" : "col &times;1"}</b></span>`
    ).join("");
    const candRows = ex.cand.map((c) =>
      `<div class="dbt-cand${c.tag ? " is-tag" : ""}">${schip(c.skill)}` +
      `<span class="dbt-cand-idx">${c.idx.map((x) => `<code>${x}</code>`).join("")}</span>` +
      `<span class="dbt-cand-score">score ${c.score}</span>` +
      `<span class="dbt-cand-mark">${c.tag ? "tag &check;" : "&times;"}</span></div>`
    ).join("");
    const how = `<div class="dbt-tag-how">` +
      `<div class="dbt-tag-step"><div class="dbt-tag-h"><span class="dbt-tag-n">1</span> Task ${ex.task} &mdash; the EOG <b>verifier SQL</b></div>` +
        `<pre class="dbt-sql">${ex.sql.replace(/</g, "&lt;")}</pre></div>` +
      `<div class="dbt-tag-step"><div class="dbt-tag-h"><span class="dbt-tag-n">2</span> parse &rarr; <b>signature</b> (tables / cols / values)</div><div class="dbt-sigs">${sigChips}</div></div>` +
      `<div class="dbt-tag-step"><div class="dbt-tag-h"><span class="dbt-tag-n">3</span> match each skill's <b>index</b> <i>(table-qualified pair = strong)</i></div><div class="dbt-cands">${candRows}</div></div>` +
      `<div class="dbt-tag-step dbt-tag-out"><div class="dbt-tag-h"><span class="dbt-tag-n">&rArr;</span> tag Task ${ex.task} &rarr; ${schip(ex.cand.find((c) => c.tag).skill)}</div></div>` +
      `</div>`;
    const res = `<div class="dbt-tag-res"><div class="dbt-tag-res-h">same parse + match for every task &rarr;</div>` +
      `<div class="dbt-tasklist">${
        S_TASKS.map((t) =>
          `<div class="dbt-task"><span class="dbt-task-tag">Task ${t.id}</span>` +
          `<span class="dbt-task-tools">${t.skills.map((id) => schip(id)).join("")}</span></div>`
        ).join("")
      }</div></div>`;
    const p2 = `<div class="dbt-phase dbt-p2"><div class="dbt-tag">${how}${res}</div></div>`;

    // phase 3 — order by coverage, then DERIVE versions: add skills until ≥ N
    // new tasks become solvable, then cut.
    const strip = S_SKILLS.map((s) => schip(s.id, { count: s.cov }))
      .join('<span class="dbt-rank-sep">&rsaquo;</span>');
    const trace = computeGreedy(S_THRESH).map((st) => {
      const w = Math.min(100, Math.round((st.count / S_THRESH) * 100));
      const cut = st.cut
        ? `<span class="dbt-gcut">&#9986; cut &rarr; <b>${st.cut.tag}</b> = ${st.cut.nSkills} new skills, ${st.cut.nTasks} tasks</span>`
        : "";
      return `<div class="dbt-gstep${st.cut ? " is-cut" : ""}">` +
        `<span class="dbt-gadd">+ ${schip(st.skill)}</span>` +
        `<span class="dbt-gtrack"><i style="--w:${w}%"></i></span>` +
        `<span class="dbt-gcount">${st.count}/${S_THRESH}</span>${cut}</div>`;
    }).join("");
    const p3 = `<div class="dbt-phase dbt-p3">` +
      `<div class="dbt-rankstrip"><span class="dbt-rankstrip-lab">by coverage</span>${strip}</div>` +
      `<div class="dbt-greedy"><div class="dbt-greedy-rule">Walk skills in coverage order; <b>cut a version</b> once <b>&ge; ${S_THRESH}</b> new tasks become solvable <i>(= min-step-size; <b>15</b> in the real build, ${S_THRESH} here)</i>. So a version's skill-count is <b>derived</b>, not chosen.</div>${trace}</div>` +
      `</div>`;

    // phase 4 — assign tasks to earliest version, labelling new vs old skills
    const p4 = `<div class="dbt-phase dbt-p4"><div class="dbt-assign">${
      S_VERS.map((v, k) => {
        const inV = S_TASKS.filter((t) => t.ver === k);
        return `<div class="dbt-asg-ver"><span class="dbt-asg-tag">${v.tag}</span><div class="dbt-asg-tasks">${
          inV.map((t) => {
            const chips = t.skills.map((id) => schipNO(id, S_SKILLVER[id] < t.ver)).join("");
            const nNew = t.skills.filter((id) => S_SKILLVER[id] === t.ver).length;
            const nOld = t.skills.length - nNew;
            const sum = nOld > 0 ? `${nNew} new + ${nOld} old` : `${nNew} new &middot; no old`;
            return `<div class="dbt-asg-task"><span class="dbt-asg-name">Task ${t.id}</span>` +
              `<span class="dbt-asg-tools">${chips}</span>` +
              `<span class="dbt-asg-sum">${sum}</span></div>`;
          }).join("")
        }</div></div>`;
      }).join("")
    }</div></div>`;

    return `
      <div class="db-panel${active === "skills" ? " is-active" : ""}" data-panel="skills">
        <div class="dbt" data-phase="1">
          <div class="dbt-bar">
            <ol class="dbt-steps">${
              S_STEPS.map((s, i) =>
                `<li data-step="${i + 1}" role="button" tabindex="0" title="Click to study this step"><b>${i + 1}</b>${s}</li>`
              ).join("")
            }</ol>
            <button class="dbt-play" type="button" data-playing="true" title="Pause" aria-label="Pause or play the walk-through"></button>
          </div>
          <div class="dbt-stage">${p1}${p2}${p3}${p4}</div>
          <div class="dbt-caps">${
            S_CAPS.map((c, i) => `<p data-cap="${i + 1}">${c}</p>`).join("")
          }</div>
          <div class="dbt-feats">
            <span class="dbt-feats-k">Guarantee</span>
            <ul>${S_FEATS.map((f) => `<li>${f}</li>`).join("")}</ul>
          </div>
          <!-- Entry point into the full skill-benchmark detail page. Routes to
               the #skill-datasets view (/skills/benchmark): the 4-tab dataset
               explorer (How it's built / Evolution / Real-world fit / Browser). -->
          <a class="dbt-cta" href="#stats">
            <span class="dbt-cta-k">Scale</span>
            <span class="dbt-cta-tx">
              <b>17 streams · 802 tasks · 520 tools · 42 skills · 62 agents</b>
              <i>Jump to benchmark statistics</i>
            </span>
            <span class="dbt-cta-arrow" aria-hidden="true">&rarr;</span>
          </a>
        </div>
      </div>`;
  }

  // =====================================================================
  // Agents track walk-through. Mirrors evovle_agents (capabilities.py +
  // build_capabilities.py + agent_library.py + build_agents.py):
  //   * an AGENT is now a CAPABILITY — a tool-coherent, DISJOINT bundle of the
  //     domain's tools, derived by PARTITIONING the tool universe by ENTITY
  //     (tool_capability: the table each tool acts on). Every tool belongs to
  //     exactly ONE capability, so the partition is total + disjoint +
  //     non-empty: each agent owns its COMPLETE bundle (never empty).
  //   * each capability -> one Codex SUBAGENT, built DETERMINISTICALLY (no LLM).
  //     build_capabilities re-homes ALL workflow content BY TABLE (field rules
  //     by their table; each workflow's Source policy + Notes by its primary
  //     write target; references unioned), and verify_no_content_dropped ABORTS
  //     the build if any policy/field/reference would be lost. Every agent also
  //     carries the FULL domain policy as operating context -> COMPLETE.
  //   * a task needs >1 agent when its selected_tools SPAN several capabilities
  //     (task_capabilities). ~98-100% do (49/50 csm, 75/75 hr, 82/83 itsm), yet
  //     stay solvable (the spanned bundles jointly cover all its gold tools).
  //   * rosters grow per version (a capability enters when a version's tools
  //     first touch its entity); the lead is a tool-less ROUTER that delegates
  //     + coordinates; carried-forward agents are distractors.
  // Toy: a small HR tool universe partitioned by entity (real csm=7 caps/57
  // tools, hr=6, itsm=7).
  const CC = {  // capability colours
    directory: "#2563eb", leave: "#16a34a", payroll: "#d97706",
    benefits: "#7c3aed", access: "#dc2626",
  };
  const CAP = {  // capability slug -> { title, entity, DISJOINT tool bundle }
    directory: { title: "Directory", entity: "employee",     tools: ["get_employee", "update_employee"] },
    leave:     { title: "Leave",     entity: "leave_request", tools: ["get_leave_balance", "approve_leave"] },
    payroll:   { title: "Payroll",   entity: "payroll_run",   tools: ["run_payroll"] },
    benefits:  { title: "Benefits",  entity: "benefit",       tools: ["enroll_benefit"] },
    access:    { title: "Access",    entity: "access_grant",   tools: ["grant_access", "revoke_access", "check_access"] },
  };
  const CAP_ORDER = ["directory", "leave", "payroll", "benefits", "access"];
  const CAP_OF_TOOL = {};                          // tool -> owning capability
  CAP_ORDER.forEach((c) => CAP[c].tools.forEach((t) => { CAP_OF_TOOL[t] = c; }));
  const CAP_UNIVERSE = CAP_ORDER.flatMap((c) => CAP[c].tools);  // the tool universe
  // The version a capability first enters the roster, staged by CAPABILITY
  // FREQUENCY (core caps first) — the agents track's OWN version axis (see
  // capabilities._capability_staging). The pool only grows T1={directory,leave}
  // ⊂ T2=+{payroll,benefits} ⊂ T3=+{access}.
  const CAP_VER = { directory: 0, leave: 0, payroll: 1, benefits: 1, access: 2 };
  // old workflow skills (dropped as UNITS) -> their facts re-home by table.
  const WF = [
    { id: "employee-records", table: "employee", cap: "directory" },
    { id: "leave-management", table: "leave_request", cap: "leave" },
    { id: "payroll-run", table: "payroll_run", cap: "payroll" },
  ];
  // one worked task: its gold tools span 3 capabilities -> needs 3 agents.
  const CAP_TASK = { id: "onboard + first pay-run", tools: ["get_employee", "run_payroll", "grant_access"] };
  // per-version routing examples (gold capability set; >=1 new at that version).
  const CAP_ROUTE = [
    { id: "P", ver: 0, caps: ["directory", "leave"] },
    { id: "Q", ver: 1, caps: ["directory", "payroll"] },
    { id: "R", ver: 1, caps: ["leave", "benefits"] },
    { id: "S", ver: 2, caps: ["payroll", "access", "directory"] },
  ];
  const A_STEPS = [
    "partition tools by entity",
    "build complete agents",
    "task spans &rarr; &ge;2 agents",
    "versions &middot; route &amp; delegate",
  ];
  const A_CAPS = [
    "An <b>agent is a capability</b> — a <b>disjoint</b> bundle of the domain's tools, found by <b>partitioning the tool universe by entity</b> (the table each tool acts on), with <b>no LLM</b>. Every tool lands in <b>exactly one</b> capability, so the partition is <b>total, disjoint &amp; non-empty</b> — each agent owns its <b>complete</b> tool bundle (never empty).",
    "Each capability is built into one subagent <b>deterministically</b>. <b>All</b> workflow content is <b>re-homed by table</b> — field rules by their table, each workflow's policy + notes by its primary write target, references unioned — and a hard verifier <b>aborts the build</b> if any fact is lost. Plus every agent carries the <b>full domain policy</b> as context &rArr; each subagent is <b>complete</b>.",
    "A task needs <b>one agent per capability its tools touch</b>. Because the bundles are <b>disjoint</b> and a task's tools usually span several entities, it needs <b>&ge;2 agents</b> — yet stays <b>solvable</b> (the spanned bundles jointly cover all its gold tools). <b>~98–100%</b> of tasks are multi-agent.",
    "Agents are a <b>given</b>, accumulating resource. The agents track stages its <b>own</b> versions by <b>capability frequency</b> (core caps first), <b>not</b> by skill emergence (coarse caps saturate at T₁), and <b>cuts</b> each version with a <b>min_new_tasks</b> + <b>capability-growth</b> floor — so the roster <b>grows every version</b> (T₁ &sub; T₂ &sub; T₃). The lead is a tool-less <b>router</b>: it must <b>delegate</b> to the task's gold agents (&ge;1 <b>new</b>) and <b>coordinate</b> several; carried-forward extras are <b>distractors</b>.",
  ];
  const A_FEATS = [
    "<b>Agent = capability = a disjoint, complete tool bundle</b> (partition by entity, no LLM): total, disjoint, non-empty. Real domains carve <b>csm 7</b>, <b>hr 6</b>, <b>itsm 7</b> capabilities over their tool universes.",
    "<b>Every subagent is complete &amp; nothing is dropped</b>: all workflow facts (field rules, policy, references) are re-homed by table and <b>verify_no_content_dropped</b> aborts the build on any loss; every agent also gets the full domain policy. Workflow skills are dropped only <b>as units</b> (name/grouping).",
    "<b>Coordination is forced</b>: a task needs one agent per capability its tools span, so <b>49/50 csm · 75/75 hr · 82/83 itsm</b> tasks need <b>&ge;2</b> agents — yet every task stays solvable. The roster <b>accumulates</b> per version and extras are <b>distractors</b>; the metric is the lead's <b>delegation</b>.",
  ];
  const A_TAG = ["T₁", "T₂", "T₃"];   // version tags (NOT agent names) — matches tools/skills

  const cap_chip = (c, opts) => {
    opts = opts || {};
    return `<span class="dbt-agent${opts.muted ? " is-muted" : ""}" style="--tc:${CC[c]}">${CAP[c].title}</span>`;
  };
  const cap_chipNO = (c, isOld) =>
    `<span class="dbt-agent${isOld ? " is-muted" : ""}" style="--tc:${CC[c]}">${CAP[c].title}` +
    `<b class="dbt-flag dbt-flag--${isOld ? "old" : "new"}">${isOld ? "old" : "new"}</b></span>`;
  // tool chip coloured by its OWNING capability (so the partition reads at a glance)
  const cap_tool = (t, opts) => {
    opts = opts || {};
    return `<span class="dbt-ctool${opts.muted ? " is-muted" : ""}" style="--tc:${CC[CAP_OF_TOOL[t]]}">${t}</span>`;
  };
  const mtool = (t) => `<span class="dbt-mini">${t}</span>`;

  function agentsPanelHTML() {
    // phase 1 — partition the tool universe BY ENTITY into disjoint capability
    // bundles (the agent roster). Mirrors capabilities.capability_tool_map.
    const uni = CAP_UNIVERSE.map((t) =>
      `<span class="dbt-ctool" style="--tc:var(--border-strong)">${t}</span>`).join("");
    const bins = CAP_ORDER.map((c) =>
      `<div class="dbt-capbin" style="--tc:${CC[c]}">` +
        `<div class="dbt-capbin-h"><span class="dbt-capbin-dot"></span><b>${CAP[c].title}</b>` +
          `<span class="dbt-capbin-ent">entity <code>${CAP[c].entity}</code></span></div>` +
        `<div class="dbt-capbin-tools">${CAP[c].tools.map(mtool).join("")}</div></div>`).join("");
    const p1 = `<div class="dbt-phase dbt-p1">` +
      `<figure class="dbt-uni-fig"><figcaption class="dbt-uni-cap"><span class="db-cap-k">Tool universe</span> every tool the domain's tasks ever call (union of all selected_tools)</figcaption>` +
        `<div class="dbt-uni">${uni}</div></figure>` +
      `<div class="dbt-splitar"><span class="dbt-splitar-line"></span>` +
        `<span class="dbt-splitar-lab">Partition by <b>entity</b>: parse each tool's name &rarr; the <b>table it acts on</b> &rarr; route it to <b>exactly one</b> capability (deterministic, no LLM).</span></div>` +
      `<div class="dbt-capgrid">${bins}</div>` +
      `<div class="dbt-foot"><b>The roster.</b> The partition is <b>disjoint</b> (every tool in exactly one bundle), <b>total</b> (no tool dropped) and <b>non-empty</b> (each capability owns &ge;1 tool) — so each <b>capability = one agent</b> that owns its <b>complete</b> tool bundle.</div>` +
      `</div>`;

    // phase 2 — build each capability into a COMPLETE subagent: re-home ALL
    // workflow content by table + full domain policy; verifier aborts on loss.
    const wfRows = WF.map((w) =>
      `<div class="dbt-attr-row"><span class="dbt-mini">${w.id}</span><span class="dbt-attr-ar">&rarr;</span>` +
      `<code class="dbt-tbl">${w.table}</code><span class="dbt-attr-ar">&rarr;</span>${cap_chip(w.cap)}</div>`).join("");
    const acard = `<div class="dbt-acard" style="--tc:${CC.directory}">` +
      `<div class="dbt-acard-h">${cap_chip("directory")}<span class="dbt-acard-tag">one complete subagent</span></div>` +
      `<div class="dbt-acard-row"><span class="dbt-acard-k">tools</span><span class="dbt-acard-v">${CAP.directory.tools.map(mtool).join("")}<i>complete bundle</i></span></div>` +
      `<div class="dbt-acard-row"><span class="dbt-acard-k">SKILL.md</span><span class="dbt-acard-v">Scope · Required fields · Operating rules · references <i>re-homed by table</i></span></div>` +
      `<div class="dbt-acard-row"><span class="dbt-acard-k">context</span><span class="dbt-acard-v">full domain policy <i>shared by every agent</i></span></div>` +
      `<div class="dbt-acard-row"><span class="dbt-acard-k">model</span><span class="dbt-acard-v">inherits the orchestrator</span></div>` +
      `<div class="dbt-acard-complete">&#10003; complete — owns every tool + every rule it can act on</div></div>`;
    const p2 = `<div class="dbt-phase dbt-p2">` +
      `<div class="dbt-rulebar">Each capability becomes <b>one subagent</b>, assembled <b>deterministically</b> (no LLM): it owns its <b>complete tool bundle</b>, and <b>all</b> workflow content is <b>re-homed onto it by table</b> — then a hard verifier checks <b>nothing was lost</b>.</div>` +
      `<div class="dbt-tag">` +
        `<div class="dbt-tag-how">` +
          `<div class="dbt-tag-step"><div class="dbt-tag-h"><span class="dbt-tag-n">1</span> old <b>workflow skills</b> — dropped as <b>units</b>, facts kept</div>` +
            `<div class="dbt-attr-line">${WF.map((w) => `<span class="dbt-mini">${w.id}</span>`).join("")}</div></div>` +
          `<div class="dbt-tag-step"><div class="dbt-tag-h"><span class="dbt-tag-n">2</span> re-home each fact <b>by table</b> &rarr; the capability that owns it</div>` +
            `<div class="dbt-attr">${wfRows}</div></div>` +
          `<div class="dbt-tag-step dbt-tag-out"><div class="dbt-tag-h"><span class="dbt-tag-n">&#10003;</span> <b>verify_no_content_dropped</b> — build <b>aborts</b> if any field-cell, policy line or reference fails to re-home</div></div>` +
        `</div>` +
        `<div class="dbt-tag-res"><div class="dbt-tag-res-h">the assembled agent (capability directory) &rarr;</div>${acard}</div>` +
      `</div>` +
      `<div class="dbt-foot"><b>Trade-off.</b> Workflow skills lose their <b>grouping/name</b> as units — but <b>every fact</b> (field rules, policy, references) is preserved and re-homed by table, and each agent also carries the <b>full domain policy</b>, so no rule is invisible to the agent that can act on it.</div>` +
      `</div>`;

    // phase 3 — a task whose tools SPAN several capabilities needs one agent per
    // capability. Mirrors capabilities.task_capabilities.
    const tk = CAP_TASK;
    const tcaps = CAP_ORDER.filter((c) => tk.tools.some((x) => CAP_OF_TOOL[x] === c));
    const mapRows = tk.tools.map((x) =>
      `<div class="dbt-attr-row">${cap_tool(x)}<span class="dbt-attr-ar">&rarr;</span>${cap_chip(CAP_OF_TOOL[x])}</div>`).join("");
    const rates = [["csm", "49 / 50"], ["hr", "75 / 75"], ["itsm", "82 / 83"]];
    const rateRows = rates.map(([d, n]) =>
      `<div class="dbt-stat"><span class="dbt-stat-d">${d}</span><span class="dbt-stat-n">${n}</span><span class="dbt-stat-l">need &ge;2 agents</span></div>`).join("");
    const p3 = `<div class="dbt-phase dbt-p3"><div class="dbt-tag">` +
      `<div class="dbt-tag-how">` +
        `<div class="dbt-tag-step"><div class="dbt-tag-h"><span class="dbt-tag-n">1</span> Task &ldquo;${tk.id}&rdquo; — its gold <b>tools</b></div>` +
          `<div class="dbt-attr-line">${tk.tools.map((x) => cap_tool(x)).join("")}</div></div>` +
        `<div class="dbt-tag-step"><div class="dbt-tag-h"><span class="dbt-tag-n">2</span> map each tool &rarr; the <b>one</b> capability that owns it</div>` +
          `<div class="dbt-attr">${mapRows}</div></div>` +
        `<div class="dbt-tag-step dbt-tag-out"><div class="dbt-tag-h"><span class="dbt-tag-n">&rArr;</span> tools <b>span</b> ${tcaps.map((c) => cap_chip(c)).join(" ")} &rarr; needs <b>${tcaps.length} agents</b> · coordinate — yet <b>solvable</b></div></div>` +
      `</div>` +
      `<div class="dbt-tag-res"><div class="dbt-tag-res-h">why &ge;2 agents is the norm &rarr;</div><div class="dbt-stats">${rateRows}</div>` +
        `<div class="dbt-stat-note">Disjoint bundles + tasks touching several entities &rArr; coordination is <b>forced</b>; the rare solo task touches a single entity.</div></div>` +
      `</div></div>`;

    // phase 4 — the roster GROWS per version. The agents track stages its OWN
    // versions by CAPABILITY FREQUENCY (core caps first) and decides WHERE to
    // cut with TWO floors (capabilities._capability_staging ->
    // evolve_tools.build_frequency_anchors_adaptive):
    //   - min_new_tasks_per_stage : >= N tasks become newly solvable, AND
    //   - min_growth_frac         : the roster grows by >= a fraction of caps.
    // Each task lands at the earliest version whose roster covers its caps.
    const capVers = A_TAG.map((tag, k) => ({
      tag, k,
      cum: CAP_ORDER.filter((c) => CAP_VER[c] <= k),
      delta: CAP_ORDER.filter((c) => CAP_VER[c] === k),
    }));
    const p4seen = new Set();
    const chain = capVers.map((v) => {
      const have = new Set(v.cum);
      const solv = CAP_ROUTE.filter((r) => r.caps.every((c) => have.has(c)));
      const fresh = solv.filter((r) => !p4seen.has(r.id));
      solv.forEach((r) => p4seen.add(r.id));
      const freshChips = fresh.length
        ? fresh.map((r) => `<i class="dbt-solv-chip">Task ${r.id}</i>`).join(" ")
        : `<i class="dbt-solv-chip is-none">none</i>`;
      const dcap = `+${v.delta.length} cap${v.delta.length === 1 ? "" : "s"}`;
      const fcount = `+${fresh.length} new task${fresh.length === 1 ? "" : "s"}`;
      const badge = v.k === 0
        ? `<span class="dbt-cut-badge dbt-cut-badge--floor">${dcap} &middot; ${fresh.length} task${fresh.length === 1 ? "" : "s"} &ge; floor (N=1)</span>`
        : `<span class="dbt-cut-badge">${dcap} &middot; ${fcount} &ge; floor</span>`;
      const main = `<div class="dbt-cat"><span class="dbt-cat-tag">${v.tag}</span>` +
        `<span class="dbt-cat-tools">${v.cum.map((c) => cap_chip(c, { muted: CAP_VER[c] < v.k })).join(" ")}</span>` +
        `<span class="dbt-cat-delta">${v.k === 0 ? "initial roster" : "+ " + v.delta.map((c) => CAP[c].title).join(", ")}</span></div>`;
      const sub = `<div class="dbt-cut-sub"><span class="dbt-cut-arrow">&#8627;</span> newly solvable: ${freshChips} ${badge}</div>`;
      return `<div class="dbt-cutrow">${main}${sub}</div>`;
    }).join("");
    const routes = capVers.map((v) => {
      const inV = CAP_ROUTE.filter((r) => r.ver === v.k);
      return `<div class="dbt-asg-ver"><span class="dbt-asg-tag">${v.tag}</span><div class="dbt-asg-tasks">${
        inV.map((r) => {
          const chips = r.caps.map((c) => cap_chipNO(c, CAP_VER[c] < r.ver)).join(" ");
          const n = r.caps.length;
          const sum = n > 1 ? `route to ${n} agents &middot; <b>coordinate</b>` : "route to 1 agent";
          return `<div class="dbt-asg-task${n > 1 ? " is-coord" : ""}"><span class="dbt-asg-name">Task ${r.id}</span>` +
            `<span class="dbt-asg-tools">${chips}</span><span class="dbt-asg-sum">${sum}</span></div>`;
        }).join("")
      }</div></div>`;
    }).join("");
    const p4 = `<div class="dbt-phase dbt-p4">` +
      `<div class="dbt-rulebar">The agents track stages its <b>own</b> versions by <b>capability frequency</b> (core caps first), <b>not</b> by skill emergence (coarse caps would saturate at T₁ — 0 new agents after). Where to <b>cut</b> each version is set by <b>two floors</b>: <b>&ge; min_new_tasks</b> newly-solvable tasks <b>and</b> a <b>capability-growth</b> floor; each task lands at the <b>earliest version whose roster covers its caps</b>, so the pool only grows T₁ &sub; T₂ &sub; T₃.</div>` +
      `<div class="dbt-asg-h">the <b>roster</b> after each cut — grows every version &rarr;</div>` +
      `<div class="dbt-cats dbt-cats--cut">${chain}</div>` +
      `<div class="dbt-asg-h">the lead <b>routes</b> each task to its gold agents (&ge;1 <b>new</b>) &amp; <b>coordinates</b> &rarr;</div>` +
      `<div class="dbt-assign">${routes}</div>` +
      `<div class="dbt-foot"><b>Real floors</b> (<code>capabilities._capability_staging</code>). <code>min_new_tasks</code> = <b>7</b>/version (enterprise <b>100</b>); the growth floor <code>min_growth_frac</code> = <b>0.15</b> (enterprise <b>0.02</b> &asymp; floor-only, so the task floor sets the step size). Staged by frequency the roster grows <b>every</b> version (never saturating) — for the dense enterprise domain this spreads into up to <b>~15</b> balanced versions (110–254 tasks each). Carried-forward extras become <b>distractors</b>.</div>` +
      `</div>`;

    return `
      <div class="db-panel${active === "agents" ? " is-active" : ""}" data-panel="agents">
        <div class="dbt" data-phase="1">
          <div class="dbt-bar">
            <ol class="dbt-steps">${
              A_STEPS.map((s, i) =>
                `<li data-step="${i + 1}" role="button" tabindex="0" title="Click to study this step"><b>${i + 1}</b>${s}</li>`
              ).join("")
            }</ol>
            <button class="dbt-play" type="button" data-playing="true" title="Pause" aria-label="Pause or play the walk-through"></button>
          </div>
          <div class="dbt-stage">${p1}${p2}${p3}${p4}</div>
          <div class="dbt-caps">${
            A_CAPS.map((c, i) => `<p data-cap="${i + 1}">${c}</p>`).join("")
          }</div>
          <div class="dbt-feats">
            <span class="dbt-feats-k">Guarantee</span>
            <ul>${A_FEATS.map((f) => `<li>${f}</li>`).join("")}</ul>
          </div>
          <!-- Entry point into the full agent-benchmark detail page. Routes to
               the #agent-datasets view (/agents/benchmark): the 4-tab dataset
               explorer (How it's built / Evolution / Real-world fit / Browser). -->
          <a class="dbt-cta" href="#stats">
            <span class="dbt-cta-k">Scale</span>
            <span class="dbt-cta-tx">
              <b>17 streams · 802 tasks · 520 tools · 42 skills · 62 agents</b>
              <i>Jump to benchmark statistics</i>
            </span>
            <span class="dbt-cta-arrow" aria-hidden="true">&rarr;</span>
          </a>
        </div>
      </div>`;
  }

  // Drive every 4-phase walk-through (.dbt) on the page. The reader can CLICK
  // any step to jump to it (which pauses auto-advance so they can study it) and
  // use the play/pause button to resume. Auto-advance only runs while playing
  // AND on screen (IntersectionObserver reports a display:none subtree as not
  // intersecting, so switching tab / landing page pauses it automatically).
  function startWalkthroughs(root) {
    root.querySelectorAll(".dbt").forEach((dbt) => {
      if (dbt._wired) return;
      dbt._wired = true;
      const N = dbt.querySelectorAll(".dbt-steps li").length || 4;
      let phase = 1, playing = true, visible = false, timer = null;

      const render = () => {
        dbt.setAttribute("data-phase", String(phase));
        const b = dbt.querySelector(".dbt-play");
        if (b) {
          b.dataset.playing = String(playing);
          b.title = playing ? "Pause" : "Play";
        }
      };
      const sync = () => {
        if (playing && visible) {
          if (!timer) timer = setInterval(() => { phase = (phase % N) + 1; render(); }, 3200);
        } else if (timer) {
          clearInterval(timer);
          timer = null;
        }
      };
      const goTo = (p) => { phase = ((p - 1 + N) % N) + 1; render(); };
      render();

      const steps = dbt.querySelector(".dbt-steps");
      const onStep = (li) => {
        if (!li) return;
        playing = false;          // studying a step -> stop auto-advance
        goTo(Number(li.dataset.step));
        sync();
      };
      if (steps) {
        steps.addEventListener("click", (e) => onStep(e.target.closest("li[data-step]")));
        steps.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onStep(e.target.closest("li[data-step]")); }
        });
      }
      const btn = dbt.querySelector(".dbt-play");
      if (btn) btn.addEventListener("click", () => { playing = !playing; render(); sync(); });

      if ("IntersectionObserver" in window) {
        new IntersectionObserver((es) => {
          es.forEach((e) => { visible = e.isIntersecting; });
          sync();
        }, { threshold: 0.3 }).observe(dbt);
      } else {
        visible = true;
        sync();
      }
    });
  }

  function select(k) {
    if (!TRACKS[k]) return;
    active = k;
    const root = document.getElementById("db-root");
    if (!root) return;
    $$(".db-tab", root).forEach((b) => b.classList.toggle("is-active", b.dataset.dbtrack === k));
    $$(".db-panel", root).forEach((p) => p.classList.toggle("is-active", p.dataset.panel === k));
    const blurb = $(".db-blurb", root);
    if (blurb) blurb.innerHTML = TRACKS[k].blurb;
  }

  function mount() {
    if (mounted) return;
    const root = document.getElementById("db-root");
    if (!root) return;
    const tabs = ORDER.map((k) =>
      `<button class="db-tab${k === active ? " is-active" : ""}" type="button" data-dbtrack="${k}">` +
      `<span class="db-tab-dot db-dot--${k}"></span>${TRACKS[k].label}</button>`
    ).join("");
    root.innerHTML =
      `<div class="db-tabs" role="tablist">${tabs}</div>` +
      `<p class="db-blurb">${TRACKS[active].blurb}</p>` +
      `<div class="db-panels">${
        ORDER.map((k) => (k === "tools" ? toolsPanelHTML() : k === "skills" ? skillsPanelHTML() : agentsPanelHTML())).join("")
      }</div>`;
    root.addEventListener("click", (e) => {
      const b = e.target.closest(".db-tab");
      if (b && b.dataset.dbtrack) select(b.dataset.dbtrack);
    });
    startWalkthroughs(root);
    mounted = true;
  }

  return { mount, select };
})();
