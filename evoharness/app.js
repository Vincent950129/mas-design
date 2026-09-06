/* EvoHarnessBench — frontend-only paper page. No backend. */
/* $ / $$ are declared in db.js */

function alignFeedbackLoop() {
  const fb = document.querySelector("#landing .cd-feedback");
  const lead = document.querySelector("#landing .cd-lead");
  const env = document.querySelector("#landing .cd-env");
  if (!fb || !lead || !env) return;
  const fbR = fb.getBoundingClientRect();
  if (fbR.width < 50) return;
  const leadR = lead.getBoundingClientRect();
  const envR = env.getBoundingClientRect();
  const leftPct = ((leadR.left + leadR.width / 2) - fbR.left) / fbR.width * 100;
  const rightPct = (fbR.right - (envR.left + envR.width / 2)) / fbR.width * 100;
  fb.style.setProperty("--loop-left", leftPct.toFixed(2) + "%");
  fb.style.setProperty("--loop-right", rightPct.toFixed(2) + "%");
}
window.addEventListener("resize", alignFeedbackLoop);

/* The inner loop closes through the persistent state: the environment's feedback may write
 * z_t, and the next task starts from whatever it holds. Both legs cross from inside the
 * stage box out to the band below it, which is the point -- z_t outlives the stage -- so
 * they are drawn as an overlay and measured off the nodes they join. */
function alignFwCycle() {
  const fw = document.querySelector("#fw");
  if (!fw) return;
  const cyc = fw.querySelector(".fw-cycle");
  const task = fw.querySelector(".fw-loop .fw-node");
  const env = fw.querySelector(".fw-node--env");
  const zb = fw.querySelector(".fw-band--across");
  if (!cyc || !task || !env || !zb) return;
  /* Nothing is measurable while the view above this one is display:none, and once the loop
   * row wraps the return leg would run up through whatever Task wrapped above. Either way
   * the .fw-fb line carries the same thing in words instead. */
  const read = () => {
    const box = fw.getBoundingClientRect();
    const t = task.getBoundingClientRect();
    const e = env.getBoundingClientRect();
    const z = zb.getBoundingClientRect();
    const ok = box.width > 50 && Math.abs(t.top - e.top) < 2 && z.top - e.bottom > 24;
    return { box, t, e, z, ok };
  };
  let m = read();
  fw.classList.toggle("is-looped", m.ok);
  if (!m.ok) return;
  /* Drawing the legs retires that line, which moves the state band up by its height: measure
   * again now it has, or both legs get placed against a boundary that no longer exists. The
   * gap left is still twice the bar above, so this cannot turn the legs back off. */
  m = read();
  if (!m.ok) { fw.classList.remove("is-looped"); return; }
  const HEAD = 9;   // the arrowhead sits beyond the line, so the line stops short of its tip
  const GAP = 4;    // and neither leg touches the node it leaves from
  const put = (sel, x, top, h) => {
    const r = cyc.querySelector(sel);
    r.style.left = `${x - m.box.left - 1}px`;
    r.style.top = `${top - m.box.top}px`;
    r.style.height = `${Math.max(0, h)}px`;
  };
  const down = m.e.bottom + GAP;
  const up = m.t.bottom + GAP + HEAD;
  put(".fw-riser--w", (m.e.left + m.e.right) / 2, down, m.z.top - HEAD - down);
  put(".fw-riser--r", (m.t.left + m.t.right) / 2, up, m.z.top - up);
}
window.addEventListener("resize", alignFwCycle);
/* Node widths move when the webfont lands, and both loops are anchored to node centres. */
document.fonts?.ready.then(() => { alignFeedbackLoop(); alignFwCycle(); });

/* The drifting band of task figures at the top of the overview tab. It carries its own few-KB
 * manifest of thumbnails the gallery already ships, so the first thing the page shows about a
 * task costs nothing like the 4.3MB corpus behind the gallery -- that only loads if someone
 * clicks a panel, which takes them to the task itself.
 *
 * The manifest arrives ordered by the stage each task enters at, and the band keeps that order:
 * drift runs leftwards, so what comes in from the right is what the harness releases later. */
const MQ = (() => {
  const PX_PER_SEC = 42;   // drift speed, held constant however many panels there are
  const still = window.matchMedia("(prefers-reduced-motion: reduce)");

  const esc = (v) => String(v == null ? "" : v).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /* The harness the task is handed, which is the axis the band exists to show: a stage is
   * not just a point in a stream, it is a bigger pool of tools, skills or specialists than
   * the stage before. Stage 1 has nothing before it, so it states the pool it starts from. */
  const unit = (n, ax) => (n === 1 ? ax.replace(/s$/, "") : ax);
  /* A gain needs a stage before it to be a gain: at the first stage of a stream the whole
   * pool is nominally new, and "+45 tools" there would read as growth that has not happened
   * yet. Nor does every later stage grow -- EOG hands out the same roster of specialists
   * throughout, and only their tools change underneath -- so a panel with nothing new to
   * report states the pool it was handed instead of claiming a gain of zero. */
  const gain = (h) => (h.first ? `${h.pool} ${unit(h.pool, h.ax)} to start`
    : h.new ? `+${h.new} ${unit(h.new, h.ax)}`
      : `${h.pool} ${unit(h.pool, h.ax)} in the pool`);

  /* A panel says what the figure is, where the task sits and what the harness holds for it;
   * the whole of it is one button, since the only thing to do with a panel is go and read
   * the task. An aria-label on a button silences the text inside it, so it has to carry the
   * same facts. The second copy of the band is scenery: no place in the tab order or the
   * a11y tree. */
  function panel(p, dup) {
    const where = p.env === "ale" ? "Agentic Last Exam" : "EnterpriseOps-Gym";
    const h = p.hx;
    const held = h.first
      ? `the ${h.ax} harness starts at ${h.pool}`
      : h.new
        ? `${gain(h)} ${h.new === 1 ? "arrives" : "arrive"} in the harness here, ${h.pool} in the pool`
        : `the ${h.ax} harness holds ${h.pool} here, none of them new`;
    const said = `${where}, stage ${p.st}: ${held}, ${h.need} needed for this task`;
    return `<button class="mq-panel" type="button" data-env="${esc(p.env)}"
      data-tid="${esc(p.tid)}"${dup ? ' tabindex="-1" aria-hidden="true"' : ""}
      title="${esc(p.title)} \u2014 ${esc(said)}"
      aria-label="Open the task: ${esc(p.title)}. ${esc(said)}">
      <span class="mq-shot"><img src="${esc(p.src)}" alt="" width="${p.w}" height="${p.h}"
        loading="lazy" decoding="async"></span>
      <span class="mq-meta">
        <span class="mq-lab">${esc(p.lab)}</span>
        <span class="mq-st">stage ${p.st}</span>
      </span>
      <span class="mq-harn" data-ax="${esc(h.ax)}">
        <span class="mq-gain${!h.first && h.new ? "" : " is-flat"}">${esc(gain(h))}</span>
        ${h.items.map((x) => `<span class="mq-item">${esc(x)}</span>`).join("")}
      </span>
    </button>`;
  }

  /* Panels are the one place on the overview tab that points into the corpus, so a click
   * has to land on the task itself rather than just the gallery: open the view, wait for
   * the payload it fetches on arrival, then search the id through the real control. */
  function show(tid) {
    PV.open("tasks");
    Promise.resolve(TG.load()).then(() => {
      const q = document.querySelector('[data-pv-view="tasks"] .cs-q');
      if (!q) return;
      q.value = tid;
      q.dispatchEvent(new Event("input", { bubbles: true }));
    });
  }

  /* The manifest, once. The floor below the band runs off the same stages, so it waits on
   * this rather than fetching its own copy. */
  let feed = null;

  function init() {
    const band = document.querySelector("[data-mq]");
    if (!band) return;
    /* Opened from disk rather than served, no fetch can reach the manifest, and a blocked
     * one is a console error the catch below never sees. The band stays out instead. */
    if (location.protocol === "file:") return;
    feed = fetch("static/marquee.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status}`))));
    feed
      .then((panels) => {
        if (!panels.length) return;
        const track = band.querySelector("[data-mq-track]");
        const one = panels.map((p) => panel(p, false)).join("");
        track.innerHTML = still.matches
          ? one
          : one + panels.map((p) => panel(p, true)).join("");
        band.hidden = false;
        /* Speed is set from the width the panels actually came out at, so adding or
         * dropping panels changes how long a lap takes, not how fast things move. */
        if (!still.matches) {
          const w = track.scrollWidth / 2;
          if (w > 0) track.style.animationDuration = `${(w / PX_PER_SEC).toFixed(1)}s`;
        }
        band.addEventListener("click", (e) => {
          const b = e.target.closest(".mq-panel");
          if (b) show(b.dataset.tid);
        });
      })
      /* The band is scenery: a page served without the manifest simply does without it. */
      .catch(() => {});
  }
  return { init, feed: () => feed || Promise.reject(new Error("no manifest")) };
})();

/* The floor under the band. The band is the outer half of this benchmark -- the harness
 * arriving stage by stage -- and on its own it says nothing about what that costs anyone.
 * This is the inner half: four families of system running inside a stage, and what each of
 * them does when a panel drops out of the band and the pool underneath them grows.
 *
 * Families rather than products, because the benchmark is not a list of four agents -- any
 * system that takes a harness can be run against it, and the shape is what decides how a
 * release lands. So each card is drawn as the thing that separates it: where the deciding
 * happens, and whether anything survives a boundary. A single agent decides in one place and
 * calls the harness itself. A centralized MAS decides in one place and delegates, so the lead
 * sits on the path of every exchange. A decentralized one has no such place at all: peers run
 * at once off a shared context and pass findings to each other. The second card is the first
 * one again, plus the one thing that outlives a stage.
 *
 * That boundary is the whole point. Under deployment evaluation the next stage hands the
 * system a fresh instance and this stage's work is gone. A self-evolving system carries z_t
 * across, which is worth something and costs something: part of what it holds now describes
 * a harness that has moved.
 *
 * The stages, the pool counts and the names in the boxes are real streams out of the corpus,
 * so the floor is running the benchmark rather than a cartoon of it. */
const SIM = (() => {
  const still = window.matchMedia("(prefers-reduced-motion: reduce)");
  /* One stage in three beats, and they are slow beats: this sits directly under a band that
   * is already drifting, and two things moving quickly in one eyeful is a page nobody reads. */
  const RUN = 7600, DROP = 1500, ADAPT = 3000, SWAP = 2600;
  const BEAT = 1250;   // a task finishing, which is what puts a mark in a tray
  const HOLD = 3;      // capability names a card shows at once
  const MARKS = 6;     // marks a tray holds before the stage turns over
  const LEG = 3;       // stages of one stream before a different axis takes over
  const AX = ["tools", "skills", "agents"];   // the three, in the order the paper reads them

  const esc = (v) => String(v == null ? "" : v).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  /* Names are the corpus's own and a few of them are long, so a box cuts to what it holds:
   * a character every four and a half units, at the size the labels are drawn. */
  const cut = (s, w) => {
    const n = Math.floor((w - 8) / 4.5);
    return s && s.length > n ? s.slice(0, n - 1) + "\u2026" : s || "";
  };

  /* ---- the pieces every diagram is made of ------------------------------------------- */
  /* Wide and shallow: four of these sit two-up under a band that is already tall, so the
   * diagrams lie down rather than stack, and the row of capabilities runs down the side
   * instead of taking a third of the page to say the same thing.
   *
   * The drawing fills its coordinate space to the edges, so the viewport is given a margin
   * of its own. A rect stroked on the boundary is otherwise cut in half by the viewport --
   * and a box with no bottom edge, a few pixels above the tray's own line, reads as a
   * diagram overlapping the row beneath it. The ratio is stated as well as implied, for
   * engines that will not take an intrinsic size from a viewBox alone. */
  const VW = 300, VH = 64, PAD = 2;
  const fig = (inner) =>
    `<svg class="sim-fig" viewBox="${-PAD} ${-PAD} ${VW + PAD * 2} ${VH + PAD * 2}"
      preserveAspectRatio="xMidYMid meet"
      style="aspect-ratio:${VW + PAD * 2}/${VH + PAD * 2}" aria-hidden="true">${inner}</svg>`;
  /* A node, and when the traffic reaches it: the pulse is on a delay so it lands with the
   * packet rather than on a rhythm of its own. */
  const box = (x, y, w, h, t, cls = "", d = 0) =>
    `<g class="sn ${cls}" style="--d:${d}s">` +
    `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="5"/>` +
    `<text x="${x + w / 2}" y="${y + h / 2 + 3}">${esc(t)}</text></g>`;
  /* A capability, which is the one kind of node that changes: it carries the axis it came
   * off, since a harness is tools and skills and specialists at once and only one of the
   * three grows at a time. */
  const cap = (x, y, w, h, c, d) =>
    `<g class="sn sn-cap" data-ax="${esc(c ? c.ax : "tools")}" style="--d:${d}s">` +
    `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="5"/>` +
    `<text x="${x + w / 2}" y="${y + h / 2 + 3}">${esc(cut(c && c.n, w))}</text></g>`;
  const wire = (a, b) => `<line class="sl" x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}"/>`;
  /* A packet is a dash travelling the line it belongs to. Give it the line's length and it
   * works on a diagonal, a vertical, anything -- no keyframes per link. */
  const flow = (a, b, d) =>
    `<line class="sf" x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}"` +
    ` style="--len:${Math.hypot(b[0] - a[0], b[1] - a[1]).toFixed(1)};--d:${d}s"/>`;

  /* Where the capabilities sit, for however many of them the pool holds. Early stages of the
   * agents axis open with two specialists, not three, and a row with a blank in it reads as
   * a rendering fault rather than a small pool. */
  const rows = (n) => (n > 2 ? [0, 22, 44] : n === 2 ? [11, 33] : [22]);
  const cols = (n) => (n > 2 ? [52, 150, 248] : n === 2 ? [101, 199] : [150]);

  /* ---- the four systems --------------------------------------------------------------- */
  /* What a capability is depends on the axis, so the picture has to as well. A tool is an
   * endpoint: the system calls out and a result comes back. A skill is a procedure: it is
   * read and complied with, never called, so the traffic runs inward. A specialist agent is
   * neither -- on that axis the arrivals are not things the system calls but members it
   * gains, so they take the place of the generic workers instead of sitting beyond them. */
  const inward = (ax) => ax === "skills";
  const roster = (ax) => ax === "agents";

  /* One agent, working the harness itself. The system is the box on the left. */
  function react(h, ax) {
    const A = [76, 31];
    let w = "", f = "", n = "";
    rows(h.length).forEach((y, i) => {
      const c = [176, y + 10], t = i * 1.2;
      w += wire(A, c);
      f += inward(ax) ? flow(c, A, t) : flow(A, c, t) + flow(c, A, t + 0.5);
      n += cap(176, y, 120, 20, h[i], t + 0.35);
    });
    return fig(w + f + box(4, 16, 72, 30, "agent", "sn-lead") + n);
  }

  /* The same agent, and the one thing that outlives the stage: z_t is what it stands on, read
   * before it acts and written after, which is how a stale entry comes to be there at all. */
  function mem(h, ax) {
    const A = [86, 10];
    /* Read up, write down, and far enough apart that a packet has somewhere to travel. */
    let w = wire([30, 36], [30, 20]) + wire([56, 20], [56, 36]);
    let f = flow([30, 36], [30, 20], 0) + flow([56, 20], [56, 36], 1.9);
    let n = "";
    rows(h.length).forEach((y, i) => {
      const c = [146, y + 10], t = i * 1.2 + 0.5;
      w += wire(A, c);
      f += inward(ax) ? flow(c, A, t) : flow(A, c, t) + flow(c, A, t + 0.4);
      n += cap(146, y, 150, 20, h[i], t + 0.3);
    });
    return fig(w + f + box(4, 0, 82, 20, "agent", "sn-lead")
      + box(4, 36, 82, 28, "z\u209C memory", "sn-mem", 2.1) + n);
  }

  /* Centralized: nothing reaches a capability except through a specialist, and no specialist
   * acts except when the lead says so. Every exchange is two hops out and two back, one at a
   * time, so the lead is on the path of all of it. On the agents axis the specialists are
   * the arrivals themselves: the roster is what grows, and the lead routes straight to it. */
  function hub(h, ax) {
    const L = [54, 31];
    let w = "", f = "", n = "";
    rows(h.length).forEach((y, i) => {
      const t = i * 1.2;
      if (roster(ax)) {
        const c = [120, y + 10];
        w += wire(L, c);
        f += flow(L, c, t) + flow(c, L, t + 0.6);
        n += cap(120, y, 176, 20, h[i], t + 0.3);
        return;
      }
      const a = [76, y + 10], b = [132, y + 10], c = [152, y + 10];
      w += wire(L, a) + wire(b, c);
      f += inward(ax)
        ? flow(c, b, t) + flow(a, L, t + 0.5)
        : flow(L, a, t) + flow(b, c, t + 0.28) + flow(c, b, t + 0.56) + flow(a, L, t + 0.84);
      n += box(76, y, 56, 20, "specialist", "sn-work", t + 0.2)
        + cap(152, y, 144, 20, h[i], t + 0.45);
    });
    return fig(w + f + box(2, 16, 52, 30, "lead", "sn-lead sn-hub") + n);
  }

  /* Decentralized: no lead to route through. Workers run at once off a shared workspace and
   * pass what they find to each other, so an expansion reaches all of them at the same
   * moment and none waits for a turn. On the agents axis the arrivals are the peers: a new
   * specialist joins the workspace above and the bus they talk over below. */
  function mesh(h, ax) {
    const X = cols(h.length);
    let w = "", f = "", n = "";
    X.forEach((x, i) => {
      if (roster(ax)) {
        w += wire([x, 20], [x, 12]) + wire([x, 44], [x, 58]);
        f += flow([x, 20], [x, 12], 0.2 + i * 0.3);
        n += cap(x - 46, 20, 92, 24, h[i], 0.6 + i * 0.3);
        return;
      }
      w += wire([x, 20], [x, 12]) + wire([x, 39], [x, 44]);
      f += (inward(ax) ? flow([x, 44], [x, 39], 0.1)
        : flow([x, 39], [x, 44], 0.1) + flow([x, 44], [x, 39], 0.7))
        + flow([x, 20], [x, 12], 2.3);
      n += box(x - 30, 20, 60, 19, "worker", "sn-work", 0.9)
        + cap(x - 47, 44, 94, 20, h[i], 0.45);
    });
    /* Peer to peer, both ways, while the work is still going on. */
    if (roster(ax)) {
      const a = [X[0], 58], b = [X[X.length - 1], 58];
      w += wire(a, b);
      f += flow(a, b, 1.5) + flow(b, a, 2.2);
    } else {
      [[82, 120], [180, 218]].forEach(([a, b]) => {
        w += wire([a, 30], [b, 30]);
        f += flow([a, 30], [b, 30], 1.4) + flow([b, 30], [a, 30], 1.8);
      });
    }
    return fig(w + f + box(4, 0, 292, 12, "shared workspace", "sn-bar", 2.9) + n);
  }

  /* Four families, not four products. Nothing here is tied to a particular agent: what the
   * benchmark grips is the shape -- where the deciding happens, and whether anything survives
   * a stage boundary -- so anyone can bring their own system and find it in one of these.
   * The paper's own runs are named as examples, in small grey, and that is all they are. */
  const SYS = [
    { id: "sas", name: "Single agent", kind: "one agent, calling the harness",
      eg: "ReAct, Codex", mode: "deployment", draw: react },
    { id: "mem", name: "Agent with memory", kind: "same agent, carrying z\u209C",
      eg: "Raw Memory", mode: "self-evolving", draw: mem },
    { id: "cmas", name: "Centralized MAS", kind: "a lead routes to specialists",
      eg: "AutoGen", mode: "deployment", draw: hub },
    { id: "dmas", name: "Decentralized MAS", kind: "peer to peer, shared context",
      eg: "DeLM", mode: "deployment", draw: mesh },
  ];

  /* ---- the floor ---------------------------------------------------------------------- */
  /* The three axes are three separate evaluations, not one harness growing on all of them.
   * The construction pipeline runs independently per axis, so a stream evolves tools, or
   * skills, or specialist agents -- seventeen streams, and a system is measured on one of
   * them at a time. The floor therefore climbs one stream, then hands over to a different
   * axis and starts that one on its own, and the two axes it is not running are named but
   * carry no pool: nothing arrives on all three at once, because no run ever sees all three.
   *
   * Taking the stages from wherever the band happened to be would run a pool of 82 tools
   * into one of 5 agents and call it growth. A stream is where the claim is legible: the
   * pool only ever grows and the stage numbers are contiguous. */
  let root = null, lads = [], lad = 0, at = 0, seat = [], leg = 0;
  let held = [], live = false, on = true;
  let byTid = new Map();     // the manifest behind a rendered panel, for the one that drops
  let turn = 0, pulse = 0;   // the phase chain, and the tick that fills the trays

  const now = () => lads[lad];
  const rung = () => now().rungs[at];

  /* What the cards are holding: the newest capabilities in the pool of the one stream being
   * run, newest first. All of one axis, because that is all a stream has. Nothing is dropped
   * for being old -- it falls off the end of a three-box row because newer ones arrived,
   * which is the pool doing its work. Returns how many of them just landed. */
  function refill() {
    const rs = now().rungs, out = [];
    for (let i = at; i >= 0 && out.length < HOLD; i -= 1) {
      rs[i].items.forEach((n) => {
        if (out.length < HOLD && !out.includes(n)) out.push(n);
      });
    }
    held = out.map((n) => ({ n, ax: now().ax }));
    return Math.min(rs[at].items.length, HOLD);
  }

  const card = (s) => `<article class="sim-card" data-sys="${s.id}" data-mode="${s.mode}">
      <header class="sim-card-h"><b>${esc(s.name)}</b>
        <span class="sim-kind">${esc(s.kind)}</span>
        <span class="sim-eg">e.g. ${esc(s.eg)}</span>
        <span class="sim-mode">${esc(s.mode)}</span></header>
      ${s.draw(held, now().ax)}
      <div class="sim-tray">
        <span class="sim-tag">${s.mode === "deployment" ? "this stage" : "z<sub>t</sub>"}</span>
        <span class="sim-marks">${Array.from({ length: MARKS },
    (_, i) => `<i style="--i:${i}"></i>`).join("")}</span>
        <span class="sim-note" data-note></span>
      </div>
    </article>`;

  const say = (html) => { root.querySelector("[data-say]").innerHTML = html; };
  const note = (s, t) => {
    root.querySelector(`[data-sys="${s}"] [data-note]`).textContent = t;
  };
  const cards = () => Array.from(root.querySelectorAll(".sim-card"));

  /* What the harness holds, drawn into every card at once: the systems differ in what they
   * do with a capability, never in which ones they were handed. Redrawn rather than
   * relabelled, because the picture itself depends on what kind of thing arrived -- an
   * endpoint to call, a procedure to follow, or another member of the system. */
  function label(fresh) {
    cards().forEach((c) => {
      const sys = SYS.find((x) => x.id === c.dataset.sys);
      c.querySelector(".sim-fig").outerHTML = sys.draw(held, now().ax);
      c.querySelectorAll(".sn-cap").forEach((g, i) => {
        g.classList.toggle("is-new", fresh > 0 && i < fresh);
      });
    });
  }

  function phase(p) {
    root.dataset.phase = p;
    clearTimeout(pulse);
    if (p === "run") pulse = setTimeout(fill, BEAT);
  }

  /* Tasks finishing, one every beat. Nothing about a mark says which system earned it --
   * they all run the same evaluation split -- but a tray that fills is a stage with work in
   * it, which is what makes the boundary cost something. */
  function fill() {
    if (root.dataset.phase !== "run") return;
    cards().forEach((c) => {
      const row = c.querySelector(".sim-marks");
      const next = row.querySelector("i:not(.is-on)");
      if (next) { next.classList.add("is-on"); return; }
      /* A deployment tray fills and then waits for the boundary to empty it. z_t is never
       * emptied, so its tray is the last few pieces of work instead: the oldest drops off
       * the end, which is how the stale ones eventually leave. */
      if (c.dataset.mode !== "deployment") {
        row.firstElementChild.remove();
        row.insertAdjacentHTML("beforeend", '<i class="is-on"></i>');
      }
    });
    pulse = setTimeout(fill, BEAT);
  }

  const unit = (n, ax) => (n === 1 ? ax.replace(/s$/, "") : ax);

  /* The stage, and the pool it opens -- on the one axis this stream evolves. The other two
   * axes are named and left empty: they are separate streams, run separately, and putting a
   * count on them here would claim a harness that grows on three axes at once. */
  function gauge(r, flash) {
    root.querySelector("[data-st]").innerHTML = `H<sub>${r.st}</sub>`;
    root.querySelectorAll("[data-met]").forEach((m) => {
      const live_ = m.dataset.met === now().ax;
      m.classList.toggle("is-live", live_);
      m.setAttribute("aria-pressed", String(live_));
      m.textContent = live_ ? `${r.pool} ${unit(r.pool, now().ax)}` : m.dataset.met;
      m.classList.remove("is-up");
      if (live_ && flash) {
        /* Reflowing the node is what restarts the animation on it, so the count landing and
         * the flash that marks it landing are the same event. */
        void m.offsetWidth;
        m.classList.add("is-up");
      }
    });
  }

  /* The stage boundary, which is where the two evaluation modes part company. */
  function expand(r) {
    const s = now();
    label(refill());
    gauge(r, true);
    say(`<b>+${r.new} ${esc(unit(r.new, s.ax))}</b> arrive${r.new === 1 ? "s" : ""}`);
    cards().forEach((c) => {
      const dep = c.dataset.mode === "deployment";
      c.querySelectorAll(".sim-marks i").forEach((m, i) => {
        m.classList.toggle("is-on", !dep && m.classList.contains("is-on"));
        /* What z_t keeps is not all still true: the entries written before this release
         * describe a harness that no longer exists. */
        m.classList.toggle("is-stale", !dep && i < 2 && m.classList.contains("is-on"));
      });
      note(c.dataset.sys, dep ? "fresh instance" : "carried \u00b7 2 stale");
    });
  }

  /* Handing over to a different axis, which is not a release: it is another evaluation
   * altogether, on a stream of its own. So nothing carries -- not the trays, and not z_t,
   * which belonged to the stream that just ended. */
  function open(r) {
    refill();
    label(0);
    gauge(r, false);
    /* Nothing is marked as having arrived, because on a handover nothing did. */
    cards().forEach((c) => {
      c.querySelectorAll(".sim-marks i").forEach((m) => {
        m.classList.remove("is-on", "is-stale");
      });
      note(c.dataset.sys, "");
    });
  }

  /* A panel has to be whole to be worth dropping -- one sliced off by the edge of the window
   * looks like a rendering fault in mid-air. The band itself only has to be on screen: it
   * runs the full width of the page, so it is never inside it. */
  const near = (r) => r.width > 0 && r.top < innerHeight - 40 && r.bottom > 0;
  const whole = (r) => near(r) && r.left > 0 && r.right < innerWidth;

  /* The panel that drops. A task standing at the stage the floor is climbing to, if the band
   * has one on screen, so what falls is a real task arriving at a real stage; otherwise the
   * release itself. Either way the numbers on the floor are the streams' -- the panel comes
   * without its own harness strip, which speaks for a stream of its own. */
  function fly(r) {
    const dock = root.querySelector("[data-dock]");
    const band = document.querySelector("[data-mq]");
    if (!dock || !band || still.matches) return;
    const hit = Array.from(document.querySelectorAll(".mq-panel"))
      .filter((n) => !n.hasAttribute("aria-hidden") && whole(n.getBoundingClientRect()))
      .find((n) => (byTid.get(n.dataset.tid) || {}).st === r.st);
    const g = document.createElement("div");
    g.className = "sim-fly";
    g.setAttribute("aria-hidden", "true");
    let box;
    if (hit) {
      g.innerHTML = hit.innerHTML;
      g.querySelector(".mq-harn")?.remove();
      box = hit.getBoundingClientRect();
    } else {
      const b = band.getBoundingClientRect();
      if (!near(b)) return;
      g.classList.add("is-pkt");
      g.innerHTML = `<span class="sim-pkt-st">stage ${r.st}</span>` +
        r.items.map((x) => `<code data-ax="${esc(now().ax)}">${esc(x)}</code>`).join("");
      box = { left: b.left + b.width / 2 - 95, top: b.bottom - 46, width: 190 };
    }
    Object.assign(g.style,
      { left: `${box.left}px`, top: `${box.top}px`, width: `${box.width}px` });
    document.body.appendChild(g);
    const d = dock.getBoundingClientRect();
    const s = 0.42, h = g.offsetHeight;
    const tx = d.left + d.width / 2 - box.left - (box.width * s) / 2;
    const ty = d.top + d.height / 2 - box.top - (h * s) / 2;
    requestAnimationFrame(() => {
      g.style.transform = `translate(${tx.toFixed(1)}px, ${ty.toFixed(1)}px) scale(${s})`;
      g.style.opacity = "0";
    });
    setTimeout(() => g.remove(), DROP + 200);
  }

  /* A different axis takes over. The stream that just ran is remembered where it stopped,
   * so when this axis comes round again it carries on climbing rather than restarting -- and
   * what the reader sees between the two is a handover, not a release: no panel drops, the
   * trays empty, and the pool moves to the axis that is now being evaluated. */
  function hand() {
    /* The release is over, so the marks that named it come off before the handover starts. */
    root.querySelectorAll(".sn-cap.is-new").forEach((g) => g.classList.remove("is-new"));
    seat[lad] = (at + 1) % now().rungs.length;
    lad = (lad + 1) % lads.length;
    at = seat[lad];
    leg = LEG;
    phase("swap");
    say("a different axis, evaluated separately");
    turn = setTimeout(() => { open(rung()); cycle(); }, SWAP);
  }

  function cycle() {
    if (!live || !on) return;
    phase("run");
    say("support any agentic system");
    cards().forEach((c) => note(c.dataset.sys, ""));
    turn = setTimeout(() => {
      /* One more stage of this stream if the leg has one left, otherwise the next axis. */
      if (leg <= 1 || at + 1 >= now().rungs.length) { hand(); return; }
      at += 1;
      leg -= 1;
      phase("drop");
      say("the harness is moving under them");
      fly(rung());
      turn = setTimeout(() => {
        expand(rung());
        phase("adapt");
        turn = setTimeout(cycle, ADAPT);
      }, DROP);
    }, RUN);
  }

  function stop() { clearTimeout(turn); clearTimeout(pulse); }
  function start() { stop(); cycle(); }

  /* The axis chips are controls, not readouts. Three axes means three separate evaluations,
   * and a reader who came for the one the floor is not running should not have to wait for
   * it to come round: clicking picks up that stream where it was left, which is what the
   * handover would have done anyway. */
  function jump(ax) {
    const i = lads.findIndex((l) => l.ax === ax);
    if (i < 0 || i === lad) return;
    stop();
    seat[lad] = at;
    lad = i;
    at = seat[lad];
    leg = LEG;
    if (live && on) { open(rung()); cycle(); return; }
    /* Held, or asked not to move: show the axis that was asked for and leave it there. */
    root.dataset.phase = "run";
    open(rung());
    say("support any agentic system");
  }

  function chips() {
    root.querySelectorAll("[data-met]").forEach((m) => {
      m.addEventListener("click", () => jump(m.dataset.met));
    });
  }

  /* Motion nobody asked for, in the corner of the eye, forever: the button is the way out of
   * that, and it doubles as the way to hold a phase still and read it. */
  function button() {
    const b = root.querySelector("[data-btn]");
    b.addEventListener("click", () => {
      on = !on;
      root.classList.toggle("is-held", !on);
      b.textContent = on ? "Pause" : "Play";
      b.setAttribute("aria-pressed", String(!on));
      if (on) start(); else stop();
    });
  }

  function init() {
    root = document.querySelector("[data-sim]");
    if (!root || location.protocol === "file:") return;
    Promise.all([
      fetch("static/stream.json").then((r) => (r.ok ? r.json() : Promise.reject(r.status))),
      /* The band's manifest, for the panel that drops. It is already on its way for the
       * band itself, and the floor runs without it if it never lands. */
      MQ.feed().catch(() => []),
    ]).then(([streams, panels]) => {
      lads = streams.filter((s) => s.rungs.length > 1);
      if (lads.length < 2) return;
      panels.forEach((p) => byTid.set(p.tid, p));
      seat = lads.map(() => 0);
      leg = LEG;
      const r = rung();
      refill();
      root.innerHTML = `<div class="sim-head">
          <span class="sim-stage" data-dock><b data-st>H<sub>${r.st}</sub></b>
            <span class="sim-mets">${AX.map((a) => {
    const live_ = a === now().ax;
    return `<button class="sim-met${live_ ? " is-live" : ""}" type="button" data-met="${a}"
      data-ax="${a}" aria-pressed="${live_}"
      title="Evaluate on the ${a} axis">${
      live_ ? `${r.pool} ${unit(r.pool, a)}` : a}</button>`;
  }).join("")}</span>
          </span>
          <span class="sim-say" data-say></span>
          <button class="sim-btn" type="button" data-btn aria-pressed="false">Pause</button>
        </div>
        <div class="sim-grid">${SYS.map(card).join("")}</div>
        <p class="sim-foot">Any system that takes a harness can be evaluated on these
          streams. <a class="sim-cta" href="#evaluate">Bring your own agent!</a></p>`;
      root.hidden = false;
      button();
      chips();
      if (still.matches) {
        /* Asked not to animate: the floor still says who is running and what they were
         * handed, it just does not perform it. */
        root.dataset.phase = "run";
        root.querySelector("[data-btn]").hidden = true;
        say("support any agentic system");
        return;
      }
      /* A stage clock running behind a tab nobody is looking at is heat, not information. */
      new IntersectionObserver((es) => {
        live = es[0].isIntersecting;
        if (live && on) start(); else stop();
      }, { threshold: 0.15 }).observe(root);
    }).catch(() => {});
  }

  return { init };
})();

const LP = (() => {
  let page = 1;
  function go(n) {
    n = Math.max(1, Math.min(3, n | 0));
    page = n;
    const root = document.getElementById("landing");
    if (!root) return;
    $$(".lp-page", root).forEach((p) => p.classList.toggle("is-active", Number(p.dataset.lpPage) === n));
    $$(".lp-step", root).forEach((s) => s.classList.toggle("is-active", Number(s.dataset.lp) === n));
    $$(".lp-dots i", root).forEach((d) => d.classList.toggle("is-active", Number(d.dataset.lp) === n));
    const prev = $(".lp-prev", root);
    const next = $(".lp-next", root);
    if (prev) prev.disabled = n === 1;
    if (next) next.disabled = n === 3;
    if (n === 1) alignFwCycle();   // the figure was display:none until now
    if (n === 2) DB.mount();
  }
  function init() {
    const root = document.getElementById("landing");
    if (!root) return;
    root.addEventListener("click", (e) => {
      const dot = e.target.closest(".lp-dots i");
      if (dot && dot.dataset.lp) { go(Number(dot.dataset.lp)); return; }
      const step = e.target.closest(".lp-step");
      if (step && step.dataset.lp) { go(Number(step.dataset.lp)); return; }
      if (e.target.closest(".lp-next")) { go(page + 1); return; }
      if (e.target.closest(".lp-prev")) { go(page - 1); return; }
    });
    go(1);
  }
  return { init, go };
})();

/* The three main-results tables, transcribed from the paper.
 *
 * Per system and per environment: Pass (%) is strict -- every verifier on the task has to
 * pass -- and Score is the mean verifier pass rate, so the gap between them is partial
 * credit. `Sd` fields are the paper's ± : population standard deviation over 3 runs, not
 * a standard error and not a confidence interval. `H` is summed agent duration in hours
 * (not wall clock) and `Tok` is input-plus-output in millions. There is no dollar cost
 * anywhere in the record, so nothing here plots one.
 *
 * `overall` is the task-weighted fold of the two Pass rates, which is why it sits nearer
 * the EOG column: EOG carries most of the tasks. */
/* Every row carries the backbone model and the scaffold it ran in, because the
 * table mixes conditions the paper is careful to distinguish: the controlled
 * systems hold GPT-5 fixed, SkillOpt is GPT-5.5, and Claude Code is Sonnet-4.6
 * inside its own harness. `llm`, `harness` and `agency` fall back to the axis
 * default, so a row only names what it changes. */
const RESULTS = {
  tools: {
    env: "eog",
    tasks: { eog: 454, ale: 63 },
    llm: "GPT-5",
    harness: "ReAct \u00b7 Codex",
    agency: "sas",
    host: "ReAct on EOG, Codex on ALE",
    rows: [
      { sec: "(Task-specific) Frontier deployment" },
      { name: "ReAct / Codex", cat: "ref", ref: true,
        eog: 26.0, eogSd: 0.6, eogScore: 57.0, eogScoreSd: 1.6, eogH: 48.3, eogTok: 27.2,
        ale: 11.6, aleSd: 1.5, aleScore: 34.6, aleScoreSd: 3.4, aleH: 9.7, aleTok: 82.2,
        overall: 24.2 },
      { sec: "Frontier deployment · cumulative harness" },
      { name: "ReAct / Codex", cat: "deploy",
        eog: 30.2, eogSd: 0.8, eogScore: 60.0, eogScoreSd: 0.9, eogH: 28.6, eogTok: 75.8,
        ale: 12.2, aleSd: 0.7, aleScore: 30.0, aleScoreSd: 1.7, aleH: 9.2, aleTok: 100.8,
        overall: 28.1 },
      { name: "AutoGen", cat: "deploy", mas: true, harness: "AutoGen",
        eog: 30.8, eogSd: 0.1, eogScore: 62.6, eogScoreSd: 0.2, eogH: 24.4, eogTok: 63.7,
        ale: 11.3, aleSd: 2.3, aleScore: 32.2, aleScoreSd: 2.4, aleH: 6.5, aleTok: 19.6,
        overall: 28.6 },
      { name: "DeLM", cat: "deploy", mas: true, harness: "DeLM",
        eog: 20.3, eogSd: 1.8, eogScore: 51.4, eogScoreSd: 1.5, eogH: 97.7, eogTok: 179.1,
        ale: 6.2, aleSd: 1.8, aleScore: 23.7, aleScoreSd: 1.5, aleH: 16.7, aleTok: 30.9,
        overall: 18.7 },
      { sec: "Memory-based self-evolving adaptation" },
      { name: "Raw Memory", cat: "memory",
        eog: 33.0, eogSd: 0.9, eogScore: 66.2, eogScoreSd: 0.6, eogH: 25.7, eogTok: 124.5,
        ale: 7.9, aleSd: 2.2, aleScore: 21.4, aleScoreSd: 3.6, aleH: 8.4, aleTok: 184.3,
        overall: 29.9 },
      { name: "Reasoning Bank", cat: "memory",
        eog: 36.9, eogSd: 1.3, eogScore: 68.7, eogScoreSd: 0.4, eogH: 21.1, eogTok: 150.8,
        ale: 11.1, aleSd: 1.3, aleScore: 28.4, aleScoreSd: 1.5, aleH: 10.0, aleTok: 106.8,
        overall: 33.8 },
      { name: "MemToolAgent", cat: "memory", best: true,
        eog: 38.6, eogSd: 1.0, eogScore: 68.9, eogScoreSd: 0.5, eogH: 23.9, eogTok: 148.0,
        ale: 10.1, aleSd: 2.0, aleScore: 25.8, aleScoreSd: 1.2, aleH: 13.1, aleTok: 83.8,
        overall: 35.1 },
      { name: "G-Memory", cat: "memory", mas: true, harness: "AutoGen",
        eog: 32.2, eogSd: 1.2, eogScore: 64.5, eogScoreSd: 0.6, eogH: 30.5, eogTok: 66.0,
        ale: 13.9, aleSd: 0.1, aleScore: 32.5, aleScoreSd: 1.6, aleH: 7.4, aleTok: 20.9,
        overall: 30.1 },
      { name: "LegoMem", cat: "memory", mas: true, harness: "LegoMem",
        eog: 22.2, eogSd: 0.7, eogScore: 57.3, eogScoreSd: 0.4, eogH: 52.8, eogTok: 141.7,
        ale: 8.3, aleSd: 1.7, aleScore: 23.7, aleScoreSd: 2.7, aleH: 13.8, aleTok: 39.5,
        overall: 20.6 },
      { sec: "Prompt-based / code-based adaptation" },
      { name: "GEPA", cat: "prompt",
        eog: 31.9, eogSd: 0.8, eogScore: 65.9, eogScoreSd: 0.3, eogH: 31.9, eogTok: 100.2,
        ale: 11.1, aleSd: 0.0, aleScore: 30.9, aleScoreSd: 1.4, aleH: 9.6, aleTok: 86.9,
        overall: 29.3 },
      { name: "Meta-Harness", cat: "code",
        eog: 35.2, eogSd: 0.7, eogScore: 65.8, eogScoreSd: 1.1, eogH: 27.3, eogTok: 99.0,
        ale: 11.1, aleSd: 1.3, aleScore: 30.4, aleScoreSd: 1.3, aleH: 11.2, aleTok: 107.8,
        overall: 32.3 },
    ],
    /* Figure 3. Deployment reports no FWT: with no stage-specific adaptation there is no
     * new-task delta to take a difference against. The dagger is the paper's own and marks
     * an average its domains disagree on, which is why it only ever lands on EOG -- that
     * number is a mean over csm, hr and itsm, where ALE is one environment. */
    xfer: {
      eog: [
        { name: "Deploy", fwt: null, bwt: -0.7, bwtDag: true },
        { name: "GEPA", fwt: 2.6, fwtDag: true, bwt: 0.4, bwtDag: true },
        { name: "Meta-H.", fwt: 1.0, fwtDag: true, bwt: 1.4, bwtDag: true },
      ],
      ale: [
        { name: "Deploy", fwt: null, bwt: -5.3 },
        { name: "GEPA", fwt: -28.5, bwt: 12.6 },
        { name: "Meta-H.", fwt: -11.1, bwt: 2.1 },
      ],
    },
  },
  skills: {
    env: "eog",
    tasks: { eog: 148, ale: 68 },
    llm: "GPT-5",
    harness: "Codex",
    agency: "sas",
    host: "Codex throughout; SAS only, since MAS skill-learning baselines are scarce",
    rows: [
      { sec: "(Task-specific) Frontier deployment" },
      { name: "Codex", cat: "ref", ref: true,
        eog: 18.9, eogSd: 1.1, eogScore: 57.8, eogScoreSd: 0.2, eogH: 3.8, eogTok: 29.9,
        ale: 7.4, aleSd: 2.1, aleScore: 27.9, aleScoreSd: 1.3, aleH: 11.4, aleTok: 80.1,
        overall: 15.3 },
      { sec: "Frontier deployment · cumulative harness" },
      { name: "Codex", cat: "deploy",
        eog: 18.9, eogSd: 0.6, eogScore: 59.1, eogScoreSd: 1.1, eogH: 3.7, eogTok: 31.0,
        ale: 8.3, aleSd: 0.7, aleScore: 25.5, aleScoreSd: 0.5, aleH: 10.8, aleTok: 82.7,
        overall: 15.6 },
      { sec: "Memory-based self-evolving adaptation" },
      { name: "Codex memory", cat: "memory",
        eog: 17.8, eogSd: 2.2, eogScore: 58.0, eogScoreSd: 1.0, eogH: 4.6, eogTok: 41.5,
        ale: 9.3, aleSd: 1.8, aleScore: 25.6, aleScoreSd: 3.5, aleH: 11.6, aleTok: 87.8,
        overall: 15.1 },
      { name: "Raw Memory", cat: "memory",
        eog: 21.6, eogSd: 1.0, eogScore: 61.5, eogScoreSd: 0.3, eogH: 2.8, eogTok: 93.0,
        ale: 7.4, aleSd: 0.0, aleScore: 20.2, aleScoreSd: 1.6, aleH: 12.2, aleTok: 156.4,
        overall: 17.1 },
      { name: "Reasoning Bank", cat: "memory",
        eog: 20.9, eogSd: 2.0, eogScore: 60.2, eogScoreSd: 1.2, eogH: 3.2, eogTok: 76.1,
        ale: 8.3, aleSd: 1.8, aleScore: 23.4, aleScoreSd: 4.1, aleH: 12.2, aleTok: 82.3,
        overall: 16.9 },
      { name: "MemToolAgent", cat: "memory",
        eog: 19.6, eogSd: 0.6, eogScore: 59.2, eogScoreSd: 0.5, eogH: 2.9, eogTok: 97.0,
        ale: 6.9, aleSd: 2.5, aleScore: 22.6, aleScoreSd: 3.7, aleH: 11.6, aleTok: 79.6,
        overall: 15.6 },
      { sec: "Prompt-based / code-based adaptation" },
      { name: "GEPA", cat: "prompt", best: true,
        eog: 24.1, eogSd: 1.4, eogScore: 61.0, eogScoreSd: 0.8, eogH: 4.1, eogTok: 44.2,
        ale: 7.4, aleSd: 2.1, aleScore: 27.8, aleScoreSd: 0.6, aleH: 11.7, aleTok: 97.8,
        overall: 18.8 },
      { name: "Meta-Harness", cat: "code",
        eog: 19.4, eogSd: 1.9, eogScore: 59.5, eogScoreSd: 1.0, eogH: 4.0, eogTok: 36.5,
        ale: 7.8, aleSd: 1.8, aleScore: 26.1, aleScoreSd: 2.4, aleH: 11.3, aleTok: 89.9,
        overall: 15.7 },
    ],
    /* Appendix rows the leaderboard ranks alongside the main table. Kept in
     * their own array so the Results tab keeps reproducing the paper's main
     * table exactly, while the leaderboard can rank the whole field. */
    more: [
      /* Table G.1. A different model inside its own harness, which is what the
       * LLM and Harness columns are for: these two rows are a controlled pair
       * with each other and with nothing else in the table. */
      { name: "Claude Code", cat: "ref", ref: true, llm: "Sonnet-4.6", harness: "Claude Code",
        eog: 29.3, eogSd: 0.8, eogScore: 65.5, eogScoreSd: 0.5, eogH: 2.5, eogTok: 19.1,
        ale: 13.2, aleSd: 0.0, aleScore: 35.0, aleScoreSd: 0.3, aleH: 36.0, aleTok: 389.7,
        overall: 24.2 },
      { name: "Claude Code", cat: "deploy", llm: "Sonnet-4.6", harness: "Claude Code",
        eog: 30.2, eogSd: 1.4, eogScore: 67.3, eogScoreSd: 1.0, eogH: 3.8, eogTok: 13.6,
        ale: 13.2, aleSd: 1.2, aleScore: 35.4, aleScoreSd: 1.5, aleH: 36.7, aleTok: 422.7,
        overall: 24.8 },
      /* Table I.2. Same agent, same stages; what varies is where the skill
       * library came from. EOG only, so the ALE columns and the overall pass
       * rate stay empty rather than being filled with the EOG number. */
      { name: "Empty skills", cat: "skill", eog: 16.9, eogSd: 2.5,
        eogScore: 56.1, eogScoreSd: 1.4, eogH: 3.5, eogTok: 74.7 },
      { name: "Zero-shot", cat: "skill", eog: 17.6, eogSd: 1.7,
        eogScore: 54.5, eogScoreSd: 1.3, eogH: 4.4, eogTok: 111.6 },
      { name: "One-shot", cat: "skill", eog: 11.5, eogSd: 0.6,
        eogScore: 41.1, eogScoreSd: 0.4, eogH: 2.8, eogTok: 61.1 },
      { name: "Raw trajectories", cat: "skill", eog: 20.0, eogSd: 1.7,
        eogScore: 59.3, eogScoreSd: 0.6, eogH: 4.3, eogTok: 87.5 },
      { name: "Self feedback", cat: "skill", eog: 12.8, eogSd: 2.2,
        eogScore: 42.1, eogScoreSd: 0.8, eogH: 2.8, eogTok: 57.3 },
      { name: "Batch self feedback", cat: "skill", eog: 16.2, eogSd: 2.4,
        eogScore: 57.3, eogScoreSd: 2.5, eogH: 3.2, eogTok: 74.3 },
      { name: "Batch teacher feedback", cat: "skill", eog: 22.1, eogSd: 3.0,
        eogScore: 59.7, eogScoreSd: 0.8, eogH: 3.1, eogTok: 33.8 },
      { name: "Skill creator", cat: "skill", eog: 20.9, eogSd: 1.5,
        eogScore: 60.6, eogScoreSd: 1.0, eogH: 3.1, eogTok: 33.8 },
      { name: "SkillOpt", cat: "skill", llm: "GPT-5.5", eog: 21.2, eogSd: 3.1,
        eogScore: 61.8, eogScoreSd: 1.6 },
    ],
    /* Figure 4, in the order the figure reads. Claude Code is here for retention only: its
     * model and native harness are not comparable to the controlled Codex setting, so the
     * paper keeps it out of the adaptation half. */
    xfer: {
      eog: [
        { name: "Deploy", fwt: null, bwt: 2.1, bwtDag: true },
        { name: "Claude Code", fwt: null, bwt: -2.6 },
        { name: "Codex mem.", fwt: -1.5, bwt: -0.6, bwtDag: true },
        { name: "GEPA", fwt: 1.1, fwtDag: true, bwt: 6.6 },
        { name: "Meta-H.", fwt: 1.4, fwtDag: true, bwt: 0, bwtDag: true },
      ],
      ale: [
        { name: "Deploy", fwt: null, bwt: -4.0 },
        { name: "Claude Code", fwt: null, bwt: 4.6 },
        { name: "Codex mem.", fwt: 2.4, bwt: -5.7 },
        { name: "GEPA", fwt: -4.0, bwt: 14.9 },
        { name: "Meta-H.", fwt: -12.2, bwt: 6.6 },
      ],
    },
  },
  agents: {
    env: "eog",
    tasks: { eog: 148, ale: 63 },
    llm: "GPT-5",
    harness: "Codex",
    agency: "mas",
    host: "Codex throughout; every row is a native multi-agent system, since the setting grades delegation",
    rows: [
      { sec: "(Task-specific) Frontier deployment" },
      { name: "Codex", cat: "ref", ref: true,
        eog: 6.5, eogSd: 1.8, eogScore: 36.3, eogScoreSd: 1.6, eogH: 24.8, eogTok: 570,
        ale: 5.3, aleSd: 3.0, aleScore: 19.2, aleScoreSd: 2.9, aleH: 27.4, aleTok: 20.0,
        overall: 6.2 },
      { sec: "Frontier deployment · cumulative harness" },
      { name: "Codex", cat: "deploy",
        eog: 8.8, eogSd: 4.5, eogScore: 42.9, eogScoreSd: 3.0, eogH: 25.3, eogTok: 587,
        ale: 4.2, aleSd: 2.0, aleScore: 16.4, aleScoreSd: 1.3, aleH: 37.8, aleTok: 30.3,
        overall: 7.4 },
      { sec: "Memory-based self-evolving adaptation" },
      { name: "Codex memory", cat: "memory",
        eog: 10.1, eogSd: 0.0, eogScore: 42.3, eogScoreSd: 0.6, eogH: 20.2, eogTok: 197,
        ale: 3.4, aleSd: 0.7, aleScore: 15.4, aleScoreSd: 2.2, aleH: 33.5, aleTok: 37.4,
        overall: 6.8 },
      { name: "G-Memory", cat: "memory", mas: true, harness: "AutoGen",
        eog: 18.2, eogSd: 1.1, eogScore: 55.1, eogScoreSd: 0.7, eogH: 29.4, eogTok: 30.4,
        ale: null, aleScore: null, overall: null },
      { name: "LEGOMem", cat: "memory", mas: true, harness: "LegoMem",
        eog: 13.3, eogSd: 0.6, eogScore: 44.7, eogScoreSd: 1.4, eogH: 16.1, eogTok: 21.8,
        ale: 5.5, aleSd: 0.9, aleScore: 18.9, aleScoreSd: 2.2, aleH: 13.6, aleTok: 34.0,
        overall: 11.0 },
      { name: "DeLM", cat: "memory", mas: true, harness: "DeLM",
        eog: 14.2, eogSd: 1.5, eogScore: 53.7, eogScoreSd: 1.1, eogH: 30.2, eogTok: 32.1,
        ale: null, aleScore: null, overall: null },
      { sec: "Prompt-based / code-based adaptation" },
      { name: "GEPA", cat: "prompt",
        eog: 14.9, eogSd: 0.6, eogScore: 54.1, eogScoreSd: 0.9, eogH: 16.5, eogTok: 172,
        ale: 6.3, aleSd: 1.3, aleScore: 23.6, aleScoreSd: 0.9, aleH: 28.2, aleTok: 25.9,
        overall: 12.3 },
      { name: "Meta-Harness", cat: "code", best: true,
        eog: 18.5, eogSd: 2.5, eogScore: 57.6, eogScoreSd: 1.2, eogH: 17.9, eogTok: 228,
        ale: 3.2, aleSd: 0.0, aleScore: 18.3, aleScoreSd: 3.0, aleH: 40.9, aleTok: 29.4,
        overall: 13.9 },
    ],
    more: [
      /* Table G.1, agents half. */
      { name: "Claude Code", cat: "ref", ref: true, llm: "Sonnet-4.6", harness: "Claude Code",
        eog: 11.0, eogSd: 1.7, eogScore: 47.2, eogScoreSd: 0.7, eogH: 10.3, eogTok: 7.1,
        ale: 16.9, aleSd: 2.0, aleScore: 41.3, aleScoreSd: 1.4, aleH: 32.4, aleTok: 240.3,
        overall: 12.8 },
      { name: "Claude Code", cat: "deploy", llm: "Sonnet-4.6", harness: "Claude Code",
        eog: 10.6, eogSd: 1.1, eogScore: 49.5, eogScoreSd: 0.3, eogH: 10.8, eogTok: 7.0,
        ale: 15.3, aleSd: 3.3, aleScore: 42.3, aleScoreSd: 3.1, aleH: 33.1, aleTok: 255.2,
        overall: 12.0 },
    ],
    /* Figure 6, in the order the figure reads. Every EOG value here carries the dagger: the
     * three domains agree on none of them, which is the environment-dependence the section
     * is about showing up inside EOG as well as against ALE. */
    xfer: {
      eog: [
        { name: "Deploy", fwt: null, bwt: 9.5, bwtDag: true },
        { name: "Claude Code", fwt: null, bwt: 4.6, bwtDag: true },
        { name: "Codex mem.", fwt: -1.5, fwtDag: true, bwt: -2.8, bwtDag: true },
        { name: "GEPA", fwt: 14.3, fwtDag: true, bwt: 6.4, bwtDag: true },
        { name: "Meta-H.", fwt: 8.8, fwtDag: true, bwt: 5.5, bwtDag: true },
      ],
      ale: [
        { name: "Deploy", fwt: null, bwt: -34.7 },
        { name: "Claude Code", fwt: null, bwt: 1.8 },
        { name: "Codex mem.", fwt: -14.1, bwt: -24.1 },
        { name: "GEPA", fwt: 7.9, bwt: -7.9 },
        { name: "Meta-H.", fwt: -0.9, bwt: -21.6 },
      ],
    },
  },
};

function fmt(v) {
  if (v == null || Number.isNaN(v)) return "—";
  return Number(v).toFixed(1);
}

function renderBars(axis, envKey) {
  const spec = RESULTS[axis];
  const key = envKey === "ale" ? "ale" : "eog";
  const rows = spec.rows.filter((r) => !r.sec);
  const max = Math.max(...rows.map((r) => r[key] || 0), 1);
  return rows.map((r) => {
    const v = r[key];
    const w = v == null ? 0 : (v / max) * 100;
    const cls = r.best ? "is-best" : r.ref ? "is-ref" : "";
    return `<div class="bar-row">
      <span class="name">${r.mas ? "▣ " : ""}${r.name}</span>
      <div class="bar-track"><div class="bar-fill ${cls}" style="width:${w}%"></div></div>
      <span class="val">${fmt(v)}</span>
    </div>`;
  }).join("");
}

function renderTable(axis) {
  const rows = RESULTS[axis].rows;
  const bestOverall = Math.max(...rows.filter((r) => r.overall != null).map((r) => r.overall));
  return `<div class="table-scroll"><table class="res">
    <thead><tr><th>System</th><th>EOG pass %</th><th>ALE pass %</th><th>Overall</th></tr></thead>
    <tbody>${rows.map((r) => {
      if (r.sec) return `<tr class="sec"><td colspan="4">${r.sec}</td></tr>`;
      const cls = [r.mas ? "group-mas" : "", r.best ? "best-row" : ""].join(" ");
      const ov = r.overall === bestOverall ? ` class="best"` : "";
      return `<tr class="${cls}"><td>${r.name}</td><td>${fmt(r.eog)}</td><td>${fmt(r.ale)}</td><td${ov}>${fmt(r.overall)}</td></tr>`;
    }).join("")}</tbody>
  </table></div>`;
}

/* Forward and backward transfer, which are signed: losing 34.7 points of retention is the
 * result this chart exists to show. Sign is read from which side of the axis a bar leaves,
 * not from its colour -- colour is the series, FWT against BWT, and it cannot carry both.
 *
 * The axis sits where the data puts it: the halves are scaled by the range above and below
 * zero, so a point is the same height on either side and neither half wastes the space it
 * was given. */
function renderXfer(axis, envKey) {
  const items = RESULTS[axis].xfer[envKey];
  const H = 120;
  const vals = items.flatMap((d) => [d.fwt, d.bwt]).filter((v) => v != null);
  const hi = Math.max(0, ...vals);
  const lo = Math.min(0, ...vals);
  /* Points per pixel is capped rather than fitted, or a chart whose largest move is half a
   * point draws it full height: on EOG the tool harness moves everything by a couple of
   * points at most, which is the finding, and it has to look like one. Each half is then
   * only as tall as its own data, so capping the scale leaves a short chart rather than a
   * tall empty one. */
  const FLOOR = 8;
  const ppp = H / Math.max(hi - lo, FLOOR);
  const px = (v) => Math.max(2, Math.round(Math.abs(v) * ppp));
  let upH = Math.round(hi * ppp);
  let dnH = Math.round(-lo * ppp);
  const MIN_PLOT = 30;
  if (upH + dnH < MIN_PLOT) {
    if (dnH >= upH) dnH = MIN_PLOT - upH;
    else upH = MIN_PLOT - dnH;
  }

  /* Both halves keep both slots, so FWT stays on the left of its column whichever side of
   * the axis it happens to leave from. */
  const slot = (kind, v, up, dag) => {
    if (v == null) {
      return up
        ? `<div class="xfer-bar ${kind} is-na" title="${kind.toUpperCase()} not reported"></div>`
        : '<div class="xfer-slot"></div>';
    }
    if ((v < 0) === up) return '<div class="xfer-slot"></div>';
    const t = `title="${kind.toUpperCase()} ${fmt(v)}%${
      dag ? " \u2014 the domains behind this average disagree" : ""}"`;
    /* Zero is neither direction: a flat mark on the axis rather than a bar of either sign. */
    return v === 0
      ? `<div class="xfer-bar ${kind} is-zero" ${t}></div>`
      : `<div class="xfer-bar ${kind}" style="height:${px(v)}px" ${t}></div>`;
  };

  return `<div class="xfer-bars">
    <div class="xfer-axis" style="top:calc(8px + ${upH}px)"></div>
    ${items.map((d) => {
      const dag = (on) => (on ? '<span class="xfer-dag">\u2020</span>' : "");
      const lab = [
        d.fwt == null ? "" : "FWT " + fmt(d.fwt) + dag(d.fwtDag),
        d.bwt == null ? "" : "BWT " + fmt(d.bwt) + dag(d.bwtDag),
      ].filter(Boolean).join(" \u00b7 ") || "\u2014";
      return `<div class="xfer-col">
        <div class="xfer-half is-up" style="height:${upH}px">${
          slot("fwt", d.fwt, true, d.fwtDag)}${slot("bwt", d.bwt, true, d.bwtDag)}</div>
        <div class="xfer-half is-dn" style="height:${dnH}px">${
          slot("fwt", d.fwt, false, d.fwtDag)}${slot("bwt", d.bwt, false, d.bwtDag)}</div>
        <div class="xfer-lab">${d.name}<br>${lab}</div>
      </div>`;
    }).join("")}
  </div>
  <p class="chart-cap">Left bar = FWT (new-task adaptation). Right bar = BWT (retention).
    Bars below the axis are negative. A stub on the axis is a method that does not report
    that measure.${items.some((d) => d.fwtDag || d.bwtDag)
      ? ' <span class="xfer-dag">\u2020</span> marks an average its domains disagree on.' : ""}</p>`;
}

function paintAxis(axis) {
  const spec = RESULTS[axis];
  const env = spec.env;
  const bars = document.querySelector(`[data-bars="${axis}"]`);
  const table = document.querySelector(`[data-table="${axis}"]`);
  const xfer = document.querySelector(`[data-xfer="${axis}"]`);
  if (bars) bars.innerHTML = renderBars(axis, env);
  if (table) table.innerHTML = renderTable(axis);
  if (xfer) xfer.innerHTML = renderXfer(axis, env);
  $$(`[data-env="${axis}"] button`).forEach((b) => b.classList.toggle("is-active", b.dataset.envKey === env));
}

function showResults(axis) {
  $$(".rs-tab").forEach((t) => t.classList.toggle("is-active", t.dataset.rs === axis));
  $$(".rs-panel").forEach((p) => p.classList.toggle("is-active", p.dataset.rsPanel === axis));
  if (axis !== "overview") paintAxis(axis);
}

function initResults() {
  $$(".rs-tab").forEach((t) => t.addEventListener("click", () => showResults(t.dataset.rs)));
  ["tools", "skills", "agents"].forEach((axis) => {
    paintAxis(axis);
    $$(`[data-env="${axis}"]`).forEach((box) => {
      box.addEventListener("click", (e) => {
        const b = e.target.closest("button[data-env-key]");
        if (!b) return;
        RESULTS[axis].env = b.dataset.envKey;
        paintAxis(axis);
      });
    });
  });
  showResults("overview");
}

function initNav() {
  /* Paper pages use hub nav only; no sticky section tabs. */
}

function initLandingCards() {
  $$("a.landing-card[data-axis]").forEach((card) => {
    card.addEventListener("click", () => {
      const axis = card.dataset.axis;
      setTimeout(() => showResults(axis), 0);
    });
  });
}

document.getElementById("copy-bib")?.addEventListener("click", async () => {
  const text = document.getElementById("bibtex")?.textContent || "";
  try {
    await navigator.clipboard.writeText(text);
    const b = document.getElementById("copy-bib");
    b.textContent = "Copied";
    setTimeout(() => { b.textContent = "Copy BibTeX"; }, 1400);
  } catch (_) {}
});

const FW = (() => {
  let step = 1;
  let timer = null;
  let playing = true;

  function paint(n) {
    step = n;
    $$("#fw .fw-stage").forEach((s) => {
      const h = Number(s.dataset.h);
      s.classList.toggle("is-on", h <= n);
      s.classList.toggle("is-current", h === n);
    });
  }

  function tick() {
    paint(step >= 3 ? 1 : step + 1);
  }

  function init() {
    const root = $("#fw");
    if (!root) return;
    paint(1);
    alignFwCycle();
    $$(".fw-mode").forEach((b) => {
      b.addEventListener("click", () => {
        $$(".fw-mode").forEach((x) => x.classList.toggle("is-active", x === b));
        root.classList.toggle("is-deploy", b.dataset.fw === "deploy");
        root.classList.toggle("is-adapt", b.dataset.fw === "adapt");
      });
    });
    $$("#fw .fw-stage").forEach((s) => {
      s.addEventListener("click", () => {
        playing = false;
        if (timer) { clearInterval(timer); timer = null; }
        paint(Number(s.dataset.h));
      });
    });
    const sync = (on) => {
      if (on && playing) {
        if (!timer) timer = setInterval(tick, 2200);
      } else if (timer) {
        clearInterval(timer);
        timer = null;
      }
    };
    if ("IntersectionObserver" in window) {
      new IntersectionObserver((es) => {
        es.forEach((e) => sync(e.isIntersecting));
      }, { threshold: 0.25 }).observe(root);
    } else {
      sync(true);
    }
  }
  return { init };
})();

/* Case-study browser: every case in the benchmark's per-task record.
 *
 * One case is a task at one (adapt stage, test stage) pair, with every system's attempt
 * beside it -- the question the record exists to answer is what a system did differently
 * on the same task under the same harness. Default order is by DISAGREEMENT between
 * systems, since a task they all solve or all fail teaches nothing.
 *
 * The project's observability app serves this over an API. This page is static, so the
 * table ships as static/cases.json: capability names, capability lists, prompts and
 * check lists are interned into shared dictionaries and the cases hold indices into
 * them, which is what makes 3,395 cases small enough to download. Fetched on first
 * sight of the section rather than up front. Nothing is recomputed here. */
const CS = (() => {
  const PAGE = 60;
  /* Field offsets into the interned case and attempt tuples (see the builder). */
  const C = { TRACK: 0, DS: 1, TASK: 2, TRAIN: 3, REL: 4, TEST: 5, CELL: 6, Q: 7,
              CHECKS: 8, NCHECK: 9, ORACLE: 10, GRADEABLE: 11, YOUNGER: 12,
              ORACLE_NEW: 13, USED_NEW: 14, SYS: 15 };
  const A = { SYS: 0, SCORE: 1, PASS: 2, RUNS: 3, USED: 4, SRC: 5, MISSED: 6,
              MISSED_G: 7, NEW_USED: 8, MOUNT: 9, CALLS: 10, COUNTED: 11,
              SPAWNS: 12, TOKENS: 13, NOTES: 14 };

  const S = { d: null, rows: [], shown: 0, active: -1, loading: false,
              f: { track: "tools", dataset: "", system: "", cell: "", stage: "",
                   needsNew: false, usedNew: false, disagree: true, q: "", sort: "spread" } };

  const el = (sel) => document.querySelector(sel);
  const esc = (v) => String(v == null ? "" : v).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pct = (v) => Math.round((v || 0) * 100);
  const names = (i) => S.d.lists[i].map((j) => S.d.names[j]);
  const scoreClass = (v) => (v >= 0.999 ? "cs-s-full" : v <= 0.001 ? "cs-s-zero" : "cs-s-part");
  const spread = (c) => {
    const sc = c[C.SYS].map((s) => s[A.SCORE] || 0);
    return Math.max(...sc) - Math.min(...sc);
  };

  const UNIT = { tools: "tools", skills: "skills", agents: "sub-agents" };
  const VERB = { tools: "called", skills: "opened", agents: "spawned" };
  const GRADED = "a graded check reads a table this one writes, so skipping it moves the score";
  const BLIND = "reads only, or writes a table no check here looks at, so skipping it cannot cost a point";

  const chips = (items, hot, cls) => (items.length
    ? items.map((x) => `<span class="cs-chip${cls ? " " + cls : ""}${
        hot && hot.has(x) ? " is-new" : ""}">${esc(x)}</span>`).join("")
    : '<span class="cs-none">none</span>');

  /* A pool can run to 178 names, so anything past a couple of lines folds away and the
   * short lists that carry the argument stay visible. */
  const listBlock = (items, hot, label, cls) => (items.length <= 10
    ? chips(items, hot, cls)
    : `<details class="cs-det"><summary>${items.length} ${esc(label)}</summary>
       <div class="cs-fold">${chips(items, hot, cls)}</div></details>`);

  const needChips = (items, hot, graded) => (items.length
    ? items.map((x) => {
        const seen = graded.has(x);
        return `<span class="cs-chip ${seen ? "is-graded" : "is-blind"}${
          hot.has(x) ? " is-new" : ""}" title="${seen ? GRADED : BLIND}">${esc(x)}</span>`;
      }).join("")
    : '<span class="cs-none">none</span>');

  /* A zero in calls usually means the trial kept no per-call log, not that the agent
   * called nothing. Fall back to the runner's own tally and say when there is neither. */
  function callsCell(s) {
    const traj = s[A.CALLS] || 0;
    const counted = s[A.COUNTED];
    const spawns = s[A.SPAWNS] || 0;
    const extra = spawns > 0 ? ` <span class="cs-mut">+${spawns.toFixed(1)} spawns</span>` : "";
    if (traj > 0) return traj.toFixed(1) + extra;
    if (counted != null) return `<span title="the runner's tally; this trial kept no per-call log">${counted.toFixed(1)}*</span>${extra}`;
    return spawns > 0 ? `<span class="cs-none">&mdash;</span>${extra}`
      : '<span class="cs-none" title="no per-call log for this trial">&mdash;</span>';
  }

  // -- filtering ----------------------------------------------------------- //

  /* Built on demand: the first search pays for it, the other filters never do. */
  function hay(c) {
    if (c.__h == null) {
      c.__h = (S.d.taskIds[c[C.TASK]] + " " + S.d.queries[c[C.Q]] + " "
        + names(c[C.ORACLE]).join(" ")).toLowerCase();
    }
    return c.__h;
  }

  function applyFilters() {
    const f = S.f;
    const track = S.d.tracks.indexOf(f.track);
    const ds = f.dataset ? S.d.datasets.indexOf(f.dataset) : -1;
    const cell = f.cell ? S.d.cellTypes.indexOf(f.cell) : -1;
    const sys = f.system ? S.d.systems.indexOf(f.system) : -1;
    const stage = f.stage ? Number(f.stage.slice(1)) : 0;
    const q = f.q.trim().toLowerCase();

    let out = S.d.cases.filter((c) => {
      if (c[C.TRACK] !== track) return false;
      if (ds >= 0 && c[C.DS] !== ds) return false;
      if (cell >= 0 && c[C.CELL] !== cell) return false;
      if (stage && c[C.TRAIN] !== stage) return false;
      if (f.needsNew && !S.d.lists[c[C.ORACLE_NEW]].length) return false;
      if (sys >= 0 && !c[C.SYS].some((s) => s[A.SYS] === sys)) return false;
      if (f.usedNew && !c[C.USED_NEW]) return false;
      if (f.disagree && spread(c) <= 0) return false;
      if (q && hay(c).indexOf(q) < 0) return false;
      return true;
    });
    /* The bundle already arrives in disagreement order, so only the other two sort. */
    if (f.sort === "score") {
      out = out.slice().sort((a, b) =>
        Math.max(...a[C.SYS].map((s) => s[A.SCORE] || 0))
        - Math.max(...b[C.SYS].map((s) => s[A.SCORE] || 0)));
    } else if (f.sort === "task") {
      out = out.slice().sort((a, b) =>
        S.d.datasets[a[C.DS]].localeCompare(S.d.datasets[b[C.DS]])
        || S.d.taskIds[a[C.TASK]].localeCompare(S.d.taskIds[b[C.TASK]])
        || a[C.TRAIN] - b[C.TRAIN]);
    }
    return out;
  }

  // -- list ---------------------------------------------------------------- //

  function shortId(id) {
    if (id.indexOf("/") >= 0) return id;
    const bits = id.split("_");
    return bits.length > 2 ? "…" + bits[bits.length - 1] : id;
  }

  function renderItem(c, i) {
    const strip = c[C.SYS].map((s) =>
      `<i class="${scoreClass(s[A.SCORE] || 0)}" title="${esc(S.d.systems[s[A.SYS]])}: ${pct(s[A.SCORE])}"></i>`).join("");
    const sc = c[C.SYS].map((s) => pct(s[A.SCORE]));
    const type = S.d.cellTypes[c[C.CELL]];
    const tag = type === "older task, newer harness"
      ? '<span class="cs-tag" title="an old task under a harness that has moved on">old task</span>'
      : type === "same release"
        ? '<span class="cs-tag is-same" title="the task and the system belong to the same release">same release</span>'
        : '<span class="cs-tag is-fwd" title="a task from a release the system never trained on">unseen release</span>';
    const needsNew = S.d.lists[c[C.ORACLE_NEW]].length
      ? `<span class="cs-tag is-need" title="needs a capability v${c[C.REL]} introduced: ${esc(names(c[C.ORACLE_NEW]).join(", "))}">needs new</span>` : "";
    return `<li data-i="${i}" class="${S.active === i ? "is-active" : ""}">
      <div class="cs-li-top"><span class="cs-li-badge">adapt v${c[C.TRAIN]} &middot; task v${c[C.REL]}</span>
        <strong>${esc(S.d.datasets[c[C.DS]])}</strong>${tag}${needsNew}</div>
      <div class="cs-li-id">${esc(shortId(S.d.taskIds[c[C.TASK]]))}</div>
      <div class="cs-li-q">${esc(S.d.queries[c[C.Q]].slice(0, 120))}&hellip;</div>
      <div class="cs-li-foot"><span class="cs-strip">${strip}</span>
        <span class="cs-li-sp">${Math.min(...sc)}&ndash;${Math.max(...sc)}</span></div>
    </li>`;
  }

  function renderList(append) {
    if (!append) {
      S.rows = applyFilters();
      S.shown = 0;
      S.active = -1;
    }
    S.shown = Math.min(S.rows.length, S.shown + PAGE);
    const left = S.rows.length - S.shown;
    const more = left > 0
      ? `<li class="cs-more"><button type="button" data-more>Load ${Math.min(PAGE, left)} more of ${left} left</button></li>`
      : "";
    el("[data-cs-list]").innerHTML =
      (S.rows.slice(0, S.shown).map(renderItem).join("") + more)
      || '<li class="cs-empty">Nothing matches these filters.</li>';
    el("[data-cs-count]").textContent = `${S.rows.length} case${S.rows.length === 1 ? "" : "s"}`;
    el("[data-cs-hint]").textContent = left > 0 ? `${S.shown} shown` : "";
    if (!append) {
      if (S.rows.length) open(0);
      else el("[data-cs-detail]").innerHTML = '<p class="cs-none">Nothing matches these filters.</p>';
    }
  }

  // -- detail -------------------------------------------------------------- //

  function renderDetail(c) {
    const track = S.d.tracks[c[C.TRACK]];
    const unit = UNIT[track];
    const verb = VERB[track];
    const newAtRelease = new Set(names(c[C.ORACLE_NEW]));
    const graded = new Set(names(c[C.GRADEABLE]));
    const needed = names(c[C.ORACLE]);
    const oracleSet = new Set(needed);
    const younger = names(c[C.YOUNGER]);
    const cellType = S.d.cellTypes[c[C.CELL]];

    const stageLine = c[C.TRAIN] === c[C.TEST]
      ? `adapted at v${c[C.TRAIN]} and evaluated against the same v${c[C.TEST]} harness`
      : `adapted at v${c[C.TRAIN]}, evaluated against the v${c[C.TEST]} harness`;

    /* What was mounted at test is not one thing: a task-specific arm gets only the
     * task's own harness. Group the systems by the mount they actually saw. */
    const mounts = [];
    c[C.SYS].forEach((s) => {
      const m = mounts.find((x) => x.list === s[A.MOUNT]);
      if (m) m.systems.push(S.d.systems[s[A.SYS]]);
      else mounts.push({ list: s[A.MOUNT], systems: [S.d.systems[s[A.SYS]]] });
    });
    const mountRows = mounts.map((m) => {
      const items = names(m.list);
      return `<div class="cs-k">${mounts.length > 1 ? `<span class="cs-mut">${esc(m.systems.join(", "))}</span><br>` : ""
        }Mounted at test (${items.length} ${esc(unit)})</div>
        <div class="cs-v">${listBlock(items, newAtRelease, unit)}</div>`;
    }).join("");

    const checkList = (S.d.checks[c[C.CHECKS]] || "").split(" | ").filter(Boolean);

    const sysRows = c[C.SYS].map((s) => {
      const used = names(s[A.USED]);
      const hit = used.filter((x) => oracleSet.has(x));
      const spare = used.filter((x) => !oracleSet.has(x));
      const nu = new Set(names(s[A.NEW_USED]));
      const missed = names(s[A.MISSED]);
      const missGrade = new Set(names(s[A.MISSED_G]));
      const src = S.d.sources[s[A.SRC]] || "";
      const known = src && src !== "not recorded";
      const note = S.d.notes[s[A.NOTES]] || "";

      /* An empty selection is two different things and the table has to say which: a
       * source means the log was read and named nothing, no source means nobody wrote
       * it down. */
      const selected = used.length
        ? `<div class="cs-sel-sum">${hit.length}/${oracleSet.size} required &middot; ${spare.length} other${spare.length === 1 ? "" : "s"}</div>
           ${hit.length ? listBlock(hit, nu, unit, "is-hit") : ""}
           ${spare.length ? `<div class="cs-sel-lbl">not required</div>${listBlock(spare, nu, unit, "is-spare")}` : ""}`
        : known
          ? `<span class="cs-zero" title="${esc(src)}">${esc(verb)} none</span>`
          : '<span class="cs-none" title="nothing on disk records what this trial reached">not recorded</span>';

      const missCell = !known ? '<span class="cs-none">&mdash;</span>'
        : missed.length
          ? (graded.size
            ? `<div class="cs-miss-sum">${missGrade.size ? `<b>${missGrade.size} checkable</b>` : "none checkable"}${
                missed.length > missGrade.size ? ` &middot; ${missed.length - missGrade.size} not` : ""}</div>
               ${missed.map((x) => `<span class="cs-chip ${missGrade.has(x) ? "is-miss" : "is-miss-soft"}" title="${
                 missGrade.has(x) ? GRADED : BLIND}">${esc(x)}</span>`).join("")}`
            : listBlock(missed, nu, unit, "is-miss"))
          : '<span class="cs-ok-txt">none</span>';

      return `<tr>
        <td><strong>${esc(S.d.systems[s[A.SYS]])}</strong>${note ? ` <span class="cs-mut" title="${esc(note)}">(control)</span>` : ""}</td>
        <td class="cs-score ${scoreClass(s[A.SCORE] || 0)}">${pct(s[A.SCORE])}</td>
        <td class="cs-mono">${s[A.PASS]}/${s[A.RUNS]}</td>
        <td class="cs-sel">${selected}</td>
        <td class="cs-sel">${missCell}</td>
        <td class="cs-mono">${callsCell(s)}</td>
        <td class="cs-mono">${s[A.TOKENS]}k</td>
      </tr>`;
    }).join("");

    const inferred = c[C.SYS].some((s) => (S.d.sources[s[A.SRC]] || "").startsWith("inferred"));

    return `
      <div class="cs-dhead">
        <div>
          <h3 class="cs-dtitle">${esc(S.d.datasets[c[C.DS]])} <span class="cs-mut">/ ${esc(track)}</span></h3>
          <p class="cs-dsub">Task <code>${esc(S.d.taskIds[c[C.TASK]])}</code>, written for v${c[C.REL]}; ${stageLine}.
            <span class="cs-mut">${esc(cellType)}.</span></p>
        </div>
        <div class="cs-scoreboard">${c[C.SYS].map((s) =>
          `<span class="cs-sb"><i class="${scoreClass(s[A.SCORE] || 0)}"></i>${esc(S.d.systems[s[A.SYS]])} ${pct(s[A.SCORE])}</span>`).join("")}</div>
      </div>

      <h4 class="cs-h4">The prompt, as the model received it</h4>
      <div class="cs-prompt">${esc(S.d.queries[c[C.Q]])}</div>

      <h4 class="cs-h4">Graded on ${c[C.NCHECK]} check${c[C.NCHECK] === 1 ? "" : "s"}</h4>
      ${checkList.length <= 4
        ? `<ol class="cs-checks">${checkList.map((x) => `<li>${esc(x)}</li>`).join("")}</ol>`
        : `<details class="cs-det"><summary>${checkList.length} graded checks</summary>
           <ol class="cs-checks">${checkList.map((x) => `<li>${esc(x)}</li>`).join("")}</ol></details>`}

      <h4 class="cs-h4">The harness</h4>
      <div class="cs-kv">
        <div class="cs-k">The task needs (${needed.length})</div>
        <div class="cs-v">${graded.size ? needChips(needed, newAtRelease, graded) : chips(needed, newAtRelease)}
          ${graded.size ? `<p class="cs-mut cs-gradenote">${graded.size} of these ${graded.size === 1 ? "is" : "are"}
            <span class="cs-chip is-graded">checkable</span>: a graded check reads a table it writes, so leaving it out
            moves the score. The other ${needed.length - graded.size} only read, or write outside the tables these
            checks look at, so skipping them cannot cost a point however much the prompt asked for them.</p>` : ""}</div>
        ${newAtRelease.size ? `<div class="cs-k">Of those, v${c[C.REL]} introduced</div>
          <div class="cs-v">${chips(Array.from(newAtRelease), newAtRelease)}</div>` : ""}
        ${mountRows}
        ${younger.length ? `<div class="cs-k">Younger than the task itself (${younger.length})</div>
          <div class="cs-v">${listBlock(younger, newAtRelease, unit)}</div>` : ""}
      </div>

      <h4 class="cs-h4">What each system did</h4>
      <p class="cs-mut cs-syslead">The middle column is the selection itself &mdash; every
        ${esc(unit === "sub-agents" ? "sub-agent" : unit.replace(/s$/, ""))} the system ${esc(verb)}, split into the ones
        this task needs (<span class="cs-chip is-hit">required</span>) and the rest
        (<span class="cs-chip is-spare">not required</span>); a chip in
        <span class="cs-chip is-new">blue</span> is newer than the task itself.
        Read it against <em>The task needs</em> above.${
        graded.size ? ` Under <em>missed</em>, a <span class="cs-chip is-miss">red</span> chip is one this task's checks
        can see being skipped and a <span class="cs-chip is-miss-soft">grey</span> one is not, so a system can miss the
        grey ones and still score 100.` : ""}${inferred ? ` Some rows are inferred: the sandbox keeps no call log
        naming the harness, so the selection was recovered from the transcript.` : ""}</p>
      <div class="cs-tblwrap"><table class="cs-tbl">
        <thead><tr><th>system</th><th>score</th><th>passed</th><th>what it ${esc(verb)}</th>
          <th title="required but never touched">missed</th><th>calls/run</th><th>tokens/run</th></tr></thead>
        <tbody>${sysRows}</tbody>
      </table></div>`;
  }

  function open(i) {
    S.active = i;
    Array.from(el("[data-cs-list]").children).forEach((li, k) =>
      li.classList.toggle("is-active", k === i));
    el("[data-cs-detail]").innerHTML = renderDetail(S.rows[i]);
    el("[data-cs-detail]").scrollTop = 0;
  }

  // -- facets and wiring --------------------------------------------------- //

  function fill(sel, values, anyLabel) {
    const cur = sel.value;
    sel.innerHTML = (anyLabel ? `<option value="">${anyLabel}</option>` : "")
      + values.map((v) => `<option value="${esc(v)}">${esc(v)}</option>`).join("");
    if (values.indexOf(cur) >= 0) sel.value = cur;
    else if (anyLabel) sel.value = "";
  }

  /* Domains and systems are per track: an agents-axis system is not on the tools list. */
  function refreshTrackFacets() {
    const t = S.d.tracks.indexOf(S.f.track);
    const ds = new Set();
    const sys = new Set();
    S.d.cases.forEach((c) => {
      if (c[C.TRACK] !== t) return;
      ds.add(S.d.datasets[c[C.DS]]);
      c[C.SYS].forEach((s) => sys.add(S.d.systems[s[A.SYS]]));
    });
    fill(el('[data-f="dataset"]'), Array.from(ds).sort(), "all");
    fill(el('[data-f="system"]'), Array.from(sys).sort(), "any");
    S.f.dataset = el('[data-f="dataset"]').value;
    S.f.system = el('[data-f="system"]').value;
  }

  function wire() {
    let debounce = null;
    el("[data-cs-toolbar]").addEventListener("input", (e) => {
      const t = e.target.closest("[data-f]");
      if (!t) return;
      const key = t.dataset.f;
      S.f[key] = t.type === "checkbox" ? t.checked : t.value;
      if (key === "track") refreshTrackFacets();
      if (key === "q") {
        clearTimeout(debounce);
        debounce = setTimeout(() => renderList(), 220);
        return;
      }
      renderList();
    });
    el("[data-cs-list]").addEventListener("click", (e) => {
      if (e.target.closest("[data-more]")) { renderList(true); return; }
      const li = e.target.closest("li[data-i]");
      if (li) open(Number(li.dataset.i));
    });
  }

  async function load() {
    if (S.loading || S.d) return;
    S.loading = true;
    let d;
    try {
      const r = await fetch("static/cases.json");
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      d = await r.json();
    } catch (err) {
      el("[data-cs-count]").textContent = "unavailable";
      el("[data-cs-detail]").innerHTML = `<p class="cs-none">The case table could not be
        loaded (${esc(err.message || err)}). It is fetched at runtime, so this page has to
        be served over HTTP rather than opened from the filesystem.</p>`;
      return;
    }
    S.d = d;
    const stages = Array.from(new Set(d.cases.map((c) => c[C.TRAIN]))).sort((a, b) => a - b);
    fill(el('[data-f="track"]'), d.tracks.slice().sort(), null);
    el('[data-f="track"]').value = d.tracks.indexOf("tools") >= 0 ? "tools" : d.tracks[0];
    S.f.track = el('[data-f="track"]').value;
    fill(el('[data-f="cell"]'), d.cellTypes.slice().sort(), "all");
    fill(el('[data-f="stage"]'), stages.map((v) => "v" + v), "all");
    refreshTrackFacets();
    el("[data-cs-toolbar]").hidden = false;
    wire();
    renderList();
  }

  function init() {
    const root = document.getElementById("cases");
    if (!root) return;
    /* 2.3 MB of case table is not worth downloading for a visitor who never scrolls
     * this far, so it waits until the section is in sight. Observing only once the
     * page has finished loading: the stepper and figures above expand after script
     * time, and before they do this section still sits inside the viewport. */
    const observe = () => {
      if (!("IntersectionObserver" in window)) { load(); return; }
      const io = new IntersectionObserver((es) => {
        if (es.some((e) => e.isIntersecting)) { io.disconnect(); load(); }
      }, { rootMargin: "400px" });
      io.observe(root);
    };
    if (document.readyState === "complete") observe();
    else window.addEventListener("load", observe, { once: true });
  }
  return { init, load };
})();

function initHubNav() {
  const bind = (id, sel) => {
    const root = document.getElementById(id);
    if (!root) return;
    root.querySelector(sel)?.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = !root.classList.contains("is-open");
      $$(".hub-nav, .fab-hub-nav").forEach((n) => n.classList.remove("is-open"));
      root.classList.toggle("is-open", open);
      const btn = root.querySelector("[aria-expanded]");
      if (btn) btn.setAttribute("aria-expanded", String(open));
    });
    root.querySelector(".hub-nav-dropdown, .fab-hub-dropdown")?.addEventListener("click", (e) => e.stopPropagation());
  };
  bind("hubNav", ".hub-nav-trigger");
  bind("fabHubNav", ".fab-hub-trigger");
  document.addEventListener("click", () => {
    $$(".hub-nav, .fab-hub-nav").forEach((n) => n.classList.remove("is-open"));
  });
}

const SV = (() => {
  const KW = /^(?:and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield|None|True|False)$/;
  const BUILTIN = /^(?:bool|dict|enumerate|float|int|len|list|next|open|print|range|round|set|sorted|str|sum|tuple|type|zip)$/;

  /* One left-to-right pass, so a quote inside a comment (or a #, keyword or
     apostrophe inside a string) is consumed by the token that opened first. */
  const TOKEN = new RegExp(
    [
      "(#[^\\n]*)",
      "((?:[rbuf]{1,2})?(?:\"\"\"[\\s\\S]*?\"\"\"|'''[\\s\\S]*?'''|\"(?:[^\"\\\\\\n]|\\\\.)*\"|'(?:[^'\\\\\\n]|\\\\.)*'))",
      "\\b([A-Za-z_]\\w*)\\b",
      "\\b(\\d+(?:\\.\\d+)?)\\b",
    ].join("|"),
    "g",
  );

  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  function paint(src) {
    let out = "";
    let last = 0;
    let m;
    TOKEN.lastIndex = 0;
    while ((m = TOKEN.exec(src)) !== null) {
      const [tok, comment, str, word, num] = m;
      out += esc(src.slice(last, m.index));
      if (comment) out += `<span class="t-c">${esc(comment)}</span>`;
      else if (str) out += `<span class="t-s">${esc(str)}</span>`;
      else if (word) out += KW.test(word) ? `<span class="t-k">${word}</span>`
        : BUILTIN.test(word) ? `<span class="t-b">${word}</span>` : word;
      else out += `<span class="t-n">${num}</span>`;
      last = m.index + tok.length;
    }
    return out + esc(src.slice(last));
  }

  /* Several strips of these are on the page now -- the service quickstart, and the steps,
   * axes and seeds of the construction recipe -- and they switch independently, so a strip
   * is scoped to the container that owns it. Unscoped, a click in one would blank another's
   * panels, which is invisible on the strip you are looking at and obvious on the one you
   * are not. */
  function show(key, scope) {
    $$(".sv-tab", scope).forEach((t) => {
      const on = t.dataset.sv === key;
      t.classList.toggle("is-active", on);
      t.setAttribute("aria-selected", String(on));
    });
    $$(".sv-panel", scope).forEach((p) => p.classList.toggle("is-active", p.dataset.svPanel === key));
  }

  /* Which execution environment the reader is being shown: the hosted service or running it
   * locally. Separate from the quickstart tabs below it, which only apply to the service. */
  function showEnv(key) {
    $$(".ev-tab").forEach((t) => {
      const on = t.dataset.ev === key;
      t.classList.toggle("is-active", on);
      t.setAttribute("aria-selected", String(on));
    });
    $$(".ev-panel").forEach((p) => p.classList.toggle("is-active", p.dataset.evPanel === key));
  }

  function init() {
    const tabs = $$(".sv-tab");
    if (!tabs.length) return;

    $$(".sv-code code").forEach((el) => { el.innerHTML = paint(el.textContent || ""); });

    const envs = $$(".ev-panel");
    if (envs.length) {
      envs.forEach((p) => {
        p.id = `ev-panel-${p.dataset.evPanel}`;
        p.setAttribute("role", "tabpanel");
      });
      /* Any [data-ev] switches, so a link out of one panel into the other works too. */
      $$("[data-ev]").forEach((t) => {
        if (t.classList.contains("ev-tab")) t.setAttribute("aria-controls", `ev-panel-${t.dataset.ev}`);
        t.addEventListener("click", () => showEnv(t.dataset.ev));
      });
      showEnv($$(".ev-tab")[0]?.dataset.ev || "api");
    }

    /* A strip's scope is the nearest container that owns it: an explicit [data-sv-group]
     * where one view runs more than one strip, and otherwise the view itself. */
    const scopes = [];
    tabs.forEach((t) => {
      const scope = t.closest("[data-sv-group], .pv-view");
      if (scope && !scopes.includes(scope)) scopes.push(scope);
    });
    scopes.forEach((scope) => {
      /* Panel keys repeat across groups, so the ARIA ids are namespaced by the group. */
      const ns = scope.dataset.svGroup || scope.dataset.pvView || "sv";
      $$(".sv-panel", scope).forEach((p) => {
        p.id = `${ns}-panel-${p.dataset.svPanel}`;
        p.setAttribute("role", "tabpanel");
        p.setAttribute("aria-labelledby", `${ns}-tab-${p.dataset.svPanel}`);
      });
      $$(".sv-tab", scope).forEach((t) => {
        t.id = `${ns}-tab-${t.dataset.sv}`;
        t.setAttribute("aria-controls", `${ns}-panel-${t.dataset.sv}`);
        t.addEventListener("click", () => show(t.dataset.sv, scope));
      });
      show($$(".sv-tab", scope)[0].dataset.sv, scope);
    });

    $$(".sv-copy").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const code = btn.parentElement?.querySelector("code");
        try {
          await navigator.clipboard.writeText(code?.textContent || "");
          btn.textContent = "Copied";
          btn.classList.add("is-done");
          setTimeout(() => { btn.textContent = "Copy"; btn.classList.remove("is-done"); }, 1400);
        } catch (_) {}
      });
    });
  }

  return { init };
})();

/* Task gallery: the benchmark corpus itself, rather than anything a system did with it.
 *
 * The corpus on disk is 438 MB of JSONL. What ships is the test split of the domains the
 * paper reports -- 1,061 tasks across all stages -- interned by build_tasks.py the same
 * way the case table is, since a domain's system prompt repeats near-verbatim across
 * every task in it. Fetched on first sight of the section. */
const TG = (() => {
  const PAGE = 36;
  /* Field offsets into the interned task tuples (see build_tasks.py). */
  const T = { TRACK: 0, ENV: 1, DOM: 2, CAT: 3, SUB: 4, TSPLIT: 5, STAGE: 6, TID: 7,
              TITLE: 8, SUM: 9, SYS: 10, PROMPT: 11, ORACLE: 12, CUM: 13, SEL: 14,
              SOFT: 15, VER: 16, FILES: 17, MUST: 18, GYM: 19 };

  /* Opens on the illustrated tasks: the gallery is worth browsing for the figures, and
   * sorting by domain buries them behind whichever domain happens to sort first. Must
   * stay in step with the first <option> of the sort select, which is what the control
   * shows before anyone touches it. */
  const S = { d: null, rows: [], shown: 0, loading: false, open: null,
              f: { track: "", env: "", domain: "", stage: "", tsplit: "", fig: "",
                   q: "", sort: "fig" } };

  const el = (sel) => document.querySelector(sel);
  const esc = (v) => String(v == null ? "" : v).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const opt = (pool, i) => (i >= 0 ? S.d[pool][i] : "");
  const names = (i) => (i >= 0 ? S.d.lists[i].map((j) => S.d.names[j]) : []);
  const vers = (t) => (t[T.VER] >= 0 ? S.d.verifiers[t[T.VER]] : []);
  const files = (t) => (t[T.FILES] >= 0 ? S.d.files[t[T.FILES]] : []);
  const track = (t) => S.d.tracks[t[T.TRACK]];
  const env = (t) => S.d.envs[t[T.ENV]];
  const domain = (t) => S.d.domains[t[T.DOM]];
  const prompt = (t) => S.d.prompts[t[T.PROMPT]];

  const PRETTY = { ale: "ALE", eog: "EOG", csm: "CSM", hr: "HR", itsm: "ITSM" };
  const label = (s) => PRETTY[s] || s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

  /* EOG tasks carry no title, so the card leads with the request's own opening clause
   * rather than a label this page invented. */
  function heading(t) {
    if (t[T.TITLE] >= 0) return S.d.titles[t[T.TITLE]];
    const first = prompt(t).split("\n").find((l) => l.trim()) || "";
    const clipped = first.trim().replace(/\s+/g, " ");
    return clipped.length > 96 ? clipped.slice(0, 95).replace(/[\s,;.]+\S*$/, "") + "\u2026" : clipped;
  }

  function body(t) {
    if (t[T.SUM] >= 0) return S.d.summaries[t[T.SUM]];
    const p = prompt(t).trim().replace(/\s+/g, " ");
    return t[T.TITLE] >= 0 ? p : p.slice(heading(t).length - 1);
  }

  const UNIT = { tools: "tools", skills: "skills", agents: "agents" };
  /* Which documentation an axis's chips resolve against. */
  const AXIS_KIND = { tools: "tool", skills: "skill", agents: "agent" };
  /* The pools are interned in file order; the paper reads tools, skills, agents. */
  const AXES = ["tools", "skills", "agents"];
  const axisOrder = (list) => AXES.filter((a) => list.includes(a))
    .concat(list.filter((a) => !AXES.includes(a)));

  // -- figures -------------------------------------------------------------- //

  /* The two environments illustrate themselves differently, so the figures come
   * from two manifests. An ALE task ships its own artifacts — the drawing to
   * model, the slide to score, the clip to match — so its figures are keyed by
   * task. An EOG task acts on a gym, but on its own seeded copy of one: two
   * tasks in the same domain start from different rows, so `taskEnvs` points
   * each task at the environment it actually begins in. A hybrid task touches
   * more than one gym and so carries one figure per gym. */
  const ALE_DIR = "static/images/ale/";
  const ENV_DIR = "static/images/env/";

  const envsOf = (t) => (S.d.taskEnvs || {})[t[T.TID]] || [];

  /* Cheap enough to run over the whole corpus on every filter change. */
  const hasFig = (t) => (env(t) === "ale"
    ? !!(S.d.aleFigures || {})[t[T.TID]]
    : envsOf(t).some((e) => (S.d.envFigures || {})[e]));

  function figures(t) {
    if (env(t) === "ale") {
      return ((S.d.aleFigures || {})[t[T.TID]] || []).map((f) => ({
        dir: ALE_DIR, file: f.file, thumb: f.thumb, clip: f.clip, kind: f.kind,
        w: f.w, h: f.h, caption: f.caption, note: f.src,
      }));
    }
    return envsOf(t).map((id) => {
      const e = (S.d.envFigures || {})[id];
      if (!e) return null;
      return {
        dir: ENV_DIR, file: e.file, thumb: e.thumb, kind: "image",
        w: e.w, h: e.h,
        caption: `${e.label} \u00b7 the environment this task starts from`,
        note: e.caption,
      };
    }).filter(Boolean);
  }

  // -- filtering ----------------------------------------------------------- //

  function haystack(t) {
    if (t._h == null) {
      t._h = [t[T.TID], heading(t), prompt(t), opt("summaries", t[T.SUM]),
              opt("categories", t[T.CAT]), opt("subdomains", t[T.SUB]),
              names(t[T.ORACLE]).join(" "), names(t[T.SOFT]).join(" "),
              vers(t).map((v) => v[0]).join(" "),
              files(t).map((f) => f[0]).join(" ")].join(" \u0001 ").toLowerCase();
    }
    return t._h;
  }

  function applyFilters() {
    const f = S.f;
    const q = f.q.trim().toLowerCase();
    const rows = S.d.tasks.filter((t) => {
      if (f.track && track(t) !== f.track) return false;
      if (f.env && env(t) !== f.env) return false;
      if (f.domain && domain(t) !== f.domain) return false;
      if (f.stage && t[T.STAGE] !== Number(f.stage)) return false;
      if (f.tsplit && opt("taskSplits", t[T.TSPLIT]) !== f.tsplit) return false;
      if (f.fig && !hasFig(t)) return false;
      if (q && !haystack(t).includes(q)) return false;
      return true;
    });
    const by = {
      domain: (a, b) => domain(a).localeCompare(domain(b)) || a[T.STAGE] - b[T.STAGE]
        || a[T.TID].localeCompare(b[T.TID]),
      stage: (a, b) => a[T.STAGE] - b[T.STAGE] || domain(a).localeCompare(domain(b))
        || a[T.TID].localeCompare(b[T.TID]),
      checks: (a, b) => vers(b).length - vers(a).length || a[T.TID].localeCompare(b[T.TID]),
      harness: (a, b) => names(b[T.CUM]).length - names(a[T.CUM]).length
        || a[T.TID].localeCompare(b[T.TID]),
      /* Illustrated first, then the most figures, so the richest cards lead.
       * Ties fall back to the default order rather than to task id, which would
       * otherwise scatter each domain through the grid. */
      fig: (a, b) => (hasFig(b) ? 1 : 0) - (hasFig(a) ? 1 : 0)
        || figures(b).length - figures(a).length
        || domain(a).localeCompare(domain(b)) || a[T.STAGE] - b[T.STAGE]
        || a[T.TID].localeCompare(b[T.TID]),
      id: (a, b) => a[T.TID].localeCompare(b[T.TID]),
    };
    rows.sort(by[f.sort] || by.domain);
    S.rows = rows;
    S.shown = 0;
  }

  // -- rendering ----------------------------------------------------------- //

  function card(t, i) {
    const tr = track(t);
    const dom = env(t) === "ale" ? label(opt("categories", t[T.CAT])) : label(domain(t));
    const nv = vers(t).length;
    const nf = files(t).length;
    const figs = figures(t);
    const shot = figs.length
      ? `<span class="tg-shot">
          <img src="${esc(figs[0].dir + figs[0].thumb)}" alt="" loading="lazy" decoding="async">
          ${figs[0].kind === "video" ? '<span class="tg-play" aria-hidden="true"></span>' : ""}
        </span>`
      : "";
    return `<button class="tg-card${figs.length ? " has-shot" : ""}" type="button" data-i="${i}">
      ${shot}
      <span class="tg-badges">
        <span class="tg-b is-${tr}">${esc(tr)}</span>
        <span class="tg-b is-env">${esc(label(env(t)))}</span>
        <span class="tg-b is-env">${esc(dom)}</span>
        <span class="tg-b is-stage">stage ${t[T.STAGE]}</span>
      </span>
      <span class="tg-ttl">${esc(heading(t))}</span>
      <span class="tg-ex">${esc(body(t))}</span>
      <span class="tg-meta">
        <span>${names(t[T.ORACLE]).length} oracle ${esc(UNIT[tr])}</span>
        <span>${names(t[T.CUM]).length} in pool</span>
        ${nv ? `<span>${nv} check${nv === 1 ? "" : "s"}</span>` : ""}
        ${nf ? `<span>${nf} staged file${nf === 1 ? "" : "s"}</span>` : ""}
      </span>
    </button>`;
  }

  function render(append) {
    const grid = el("[data-tg-grid]");
    if (!append) { applyFilters(); grid.innerHTML = ""; }
    const next = S.rows.slice(S.shown, S.shown + PAGE);
    grid.insertAdjacentHTML("beforeend", next.map((t, k) => card(t, S.shown + k)).join(""));
    S.shown += next.length;

    const n = S.rows.length;
    el("[data-tg-count]").textContent = n
      ? `${n.toLocaleString()} task${n === 1 ? "" : "s"}${S.shown < n ? ` · ${S.shown} shown` : ""}`
      : "no tasks match these filters";
    if (!n) grid.innerHTML = '<p class="tg-none">Nothing matches. Widen a filter or clear the search.</p>';
    el("[data-tg-more]").hidden = S.shown >= n;
    $$(".tg-stat").forEach((s) => s.classList.toggle("is-active",
      s.dataset.track === S.f.track && s.dataset.env === S.f.env));
  }

  const chips = (items, cls) => (items.length
    ? `<div class="tg-chips">${items.map((x) =>
        `<span class="tg-chip${cls ? " " + cls : ""}">${esc(x)}</span>`).join("")}</div>`
    : '<p class="tg-sub">none</p>');

  /* What each chip on a task actually is, fetched on first use.
   *
   * A name on its own does not say what `find_contact_by_portal_user` takes, what
   * `3-1-registering-a-customer-case` teaches, or which records the `case_knowledge`
   * specialist is allowed to touch. The corpus rows carry bare name lists, because the
   * definitions live where the agent reads them: tool descriptions in the gyms, which
   * tools/dump_tool_docs.py asks over MCP, and skills, agents and ALE software on disk in
   * the environment repo, which tools/dump_axis_docs.py reads.
   *
   * Two payloads rather than one, so opening a piece of software does not drag in 424 KB
   * of gym schemas. Neither is in the gallery's own load: this tab already fetches four
   * megabytes of corpus, and only a reader who opens a chip needs either. */
  const DOCS = {
    tool: { url: "static/tool_docs.json", data: null, want: null },
    axis: { url: "static/axis_docs.json", data: null, want: null },
  };
  const SRC = { tool: "tool", gym: "tool", skill: "axis", agent: "axis", software: "axis" };
  const loaded = (kind) => DOCS[SRC[kind]].data;

  function loadDocs(kind) {
    const src = DOCS[SRC[kind]];
    if (src.data) return Promise.resolve(src.data);
    if (!src.want) {
      src.want = fetch(src.url)
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status}`))))
        .then((d) => (src.data = d))
        .catch(() => (src.data = { failed: true }));
    }
    return src.want;
  }

  /* A tool is documented by the gym that serves it, and 29 names are served by more than
   * one gym with a different meaning in each: `list_users` filters employees on HR and
   * returns Graph objects on Teams. So the task's own servers answer first.
   *
   * They cannot answer everything. A fifth of what a task is offered comes from another
   * domain's gym, which is the cumulative harness working as intended -- the pool grows
   * across stages, so a CSM task ends up carrying calendar and drive tools it has no use
   * for. Those still have a description; it just belongs to the gym that serves them, so
   * the panel says whose it is. Where several gyms disagree and the task's own is not
   * among them, the answer is one of theirs and the panel admits the rest exist. */
  function toolDoc(t, name) {
    const docs = loaded("tool");
    if (!docs) return null;
    for (const server of names(t[T.GYM])) {
      const gym = (docs.servers || {})[server];
      const entry = gym && (docs.gyms[gym] || {})[name];
      if (entry) return { gym, own: true, ...entry };
    }
    const others = Object.keys(docs.gyms || {}).filter((g) => docs.gyms[g][name]);
    if (!others.length) return null;
    return { gym: others[0], own: false, alts: others.slice(1), ...docs.gyms[others[0]][name] };
  }

  /* Skills, agents and ALE software are defined in files, and every name the corpus uses
   * has one. The two kinds the gyms answer for are the exception: a description exists only
   * where a gym serves it, so a row that declares no server has nothing to open. */
  const GYM_BACKED = { tool: 1, gym: 1 };
  const inspectable = (t, kind) => !GYM_BACKED[kind] || hasGyms(t);
  const hasGyms = (t) => names(t[T.GYM]).some((s) => (loaded("tool")?.servers || SERVERS)[s]);
  /* Server names as of the harvest, so the chips can be live before the docs arrive. */
  const SERVERS = { "gym-calendar": 1, "gym-email-mcp": 1, "sn-hr-internal": 1,
                    "gym-itsm-mcp": 1, "gym-teams-mcp": 1, "sn-csm-server": 1,
                    "gym-google-drive-mcp": 1 };

  /* Chips that each open their own description, whatever the axis. The panel rides with the
   * group so a long pool does not push its answer off the end of the modal. */
  const docChips = (items, t, kind, cls) => {
    if (!items.length) return '<p class="tg-sub">none</p>';
    if (!inspectable(t, kind)) return chips(items, cls);
    return `<div class="tg-docgrp" data-kind="${kind}">
      <div class="tg-chips">${items.map((x) =>
        `<button type="button" class="tg-chip is-doc${cls ? " " + cls : ""}"
          data-doc="${esc(x)}">${esc(x)}</button>`).join("")}</div>
      <div class="tg-doc" data-tg-doc hidden></div>
    </div>`;
  };

  const GYM_LABEL = { calendar: "Calendar", csm: "CSM", drive: "Drive", email: "Email",
                      hr: "HR", itsm: "ITSM", teams: "Teams",
                      enterprise_tri_hybrid: "tri-domain hybrid", hybrid: "tri-domain hybrid" };
  const libLabel = (d) => esc(GYM_LABEL[d] || label(d));

  /* The briefs are markdown, and their code spans and emphasis carry meaning: a field name
   * is not prose about a field. Escape first, then let those two through. */
  const md = (s) => esc(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");

  const docHead = (name, title, note) => `<div class="tg-doc-head">
      <code class="tg-doc-name">${esc(name)}</code>
      ${title && title !== name ? `<span class="tg-doc-title">${esc(title)}</span>` : ""}
      ${note ? `<span class="tg-doc-gym">${note}</span>` : ""}
    </div>`;

  const NOUN = { tool: "tool", gym: "server", skill: "skill", agent: "specialist",
                 software: "label" };
  const docMissing = (kind, name) =>
    `<p class="tg-doc-none"><code>${esc(name)}</code> &mdash; ${(loaded(kind) || {}).failed
      ? "the descriptions could not be loaded."
      : kind === "tool"
        ? `the gym no longer exposes this tool, so it has no description to read. The corpus
           still offers it at this stage, which is what the chip reflects.`
        : `the environment carries no definition for this ${NOUN[kind]}, so there is nothing
           to read beyond the name the corpus uses.`}</p>`;

  /* A brief as tools/dump_axis_docs.py leaves it: paragraphs, lists and tables that each
   * carry the count of whatever was trimmed off the end, and subheadings between them. */
  function docBlocks(list) {
    return (list || []).map((b) => {
      if (b[0] === "p") return `<p class="tg-doc-p">${md(b[1])}</p>`;
      if (b[0] === "h") return `<p class="tg-doc-sub">${md(b[1])}</p>`;
      if (b[0] === "ul" || b[0] === "ol") {
        return `<${b[0]} class="tg-doc-list">${b[1].map((i) => `<li>${md(i)}</li>`).join("")}${
          b[2] ? `<li class="tg-doc-more">and ${b[2]} more</li>` : ""}</${b[0]}>`;
      }
      if (b[0] === "t") {
        return `<table class="tg-doc-args"><thead><tr>${
          b[1].map((h) => `<th>${md(h)}</th>`).join("")}</tr></thead><tbody>${
          b[2].map((r) => `<tr>${r.map((c) => `<td>${md(c)}</td>`).join("")}</tr>`).join("")
        }</tbody></table>${b[3] ? `<p class="tg-doc-more">and ${b[3]} more</p>` : ""}`;
      }
      return "";
    }).join("");
  }

  const docSections = (secs) => (secs || []).map(([head, blocks, abridged]) =>
    `<h5 class="tg-doc-sec">${esc(head)}${abridged
      ? ' <span class="tg-doc-abr">(by heading)</span>' : ""}</h5>${docBlocks(blocks)}`).join("");

  const codes = (list) => list.map((x) => `<code>${esc(x)}</code>`).join(" ");

  /* A skill is the same wherever it is staged, so one definition answers for every task
   * that carries it. */
  function skillDoc(t, name) {
    const d = loaded("skill");
    return d ? ((d.skills || {})[env(t)] || {})[name] || null : null;
  }

  /* A specialist is not. `user_group` owns four different tool sets across CSM, HR, ITSM
   * and the hybrid, and `knowledge` reads four different ways, so the task's own domain
   * answers first -- and where a later stage has offered it a specialist from another
   * domain, the panel says which library that definition belongs to. */
  function agentDoc(t, name) {
    const d = loaded("agent");
    if (!d) return null;
    const roster = d.agents || {};
    if (env(t) === "ale") {
      const own = (roster.ale || {})[name];
      return own ? { own: true, ...own } : null;
    }
    const byDom = roster.eog || {};
    const dom = domain(t);
    if ((byDom[dom] || {})[name]) return { dom, own: true, ...byDom[dom][name] };
    const others = Object.keys(byDom).filter((k) => byDom[k][name]);
    if (!others.length) return null;
    /* The union library is the widest reading of a name, so it speaks for the rest. */
    const pick = others.includes("enterprise_tri_hybrid") ? "enterprise_tri_hybrid" : others[0];
    return { dom: pick, own: false, alts: others.filter((k) => k !== pick), ...byDom[pick][name] };
  }

  /* One label reaches a chip in more spellings than one: the tools axis lowercases to
   * `anndata`, the software list keeps the card's `AnnData`, and a few carry a version or
   * a wrapper script with them. The harvest recorded every literal, so this is a lookup. */
  function softDoc(t, name) {
    const d = loaded("software");
    if (!d) return null;
    const sw = d.software || {};
    const canon = (sw.alias || {})[name] || name.toLowerCase();
    const entry = (sw.items || {})[canon];
    return entry ? { canon, ...entry } : null;
  }

  function toolPanel(t, name) {
    const d = toolDoc(t, name);
    if (!d) return docMissing("tool", name);
    const args = d.a || [];
    const rets = d.o || [];
    const alts = (d.alts || []).map((g) => GYM_LABEL[g] || g);
    return `${docHead(name, "", `as the ${libLabel(d.gym)} gym describes it${d.own ? ""
        : `, which serves it into this task's pool${alts.length
          ? ` &mdash; ${esc(alts.join(" and "))} define a tool of this name differently` : ""}`}`)}
      ${d.d ? `<p class="tg-doc-d">${esc(d.d)}</p>` : ""}
      ${args.length ? `<table class="tg-doc-args">
        <thead><tr><th>Argument</th><th>Type</th><th>What it is</th></tr></thead>
        <tbody>${args.map(([an, ty, req, gloss]) => `<tr>
          <td><code>${esc(an)}</code>${req ? '<span class="tg-doc-req">required</span>' : ""}</td>
          <td class="tg-doc-ty">${esc(ty || "\u2014")}</td>
          <td>${esc(gloss || "\u2014")}</td>
        </tr>`).join("")}</tbody></table>`
        : '<p class="tg-sub">Takes no arguments.</p>'}
      ${rets.length ? `<p class="tg-doc-o"><b>Returns</b> ${
        rets.map((f) => `<code>${esc(f)}</code>`).join(" ")}</p>` : ""}`;
  }

  function skillPanel(t, name) {
    const d = skillDoc(t, name);
    if (!d) return docMissing("skill", name);
    const note = env(t) === "ale"
      ? `a ${esc(d.tr || "capability")} skill mined from the ALE corpus`
      : `an oracle skill from the ${libLabel(domain(t))} library`;
    return `${docHead(name, d.t, note)}
      ${d.d ? `<p class="tg-doc-d">${md(d.d)}</p>` : ""}
      <dl class="tg-doc-facts">
        ${d.tb ? `<dt>Records it writes or reads</dt><dd>${codes(d.tb)}</dd>` : ""}
        ${d.n ? `<dt>Recurs in</dt><dd>${d.n} ALE tasks</dd>` : ""}
      </dl>
      ${docSections(d.s)}`;
  }

  function agentPanel(t, name) {
    const d = agentDoc(t, name);
    if (!d) return docMissing("agent", name);
    const isAle = env(t) === "ale";
    const alts = (d.alts || []).map((x) => GYM_LABEL[x] || label(x));
    const note = isAle
      ? "a specialist on the ALE roster"
      : `as the ${libLabel(d.dom)} library defines it${d.own ? ""
        : `, which is where this task's pool takes it from${alts.length
          ? ` &mdash; ${esc(alts.join(" and "))} define a specialist of this name differently`
          : ""}`}`;
    const owns = d.w || [];
    const unit = isAle
      ? `piece${owns.length === 1 ? "" : "s"} of software`
      : `tool${owns.length === 1 ? "" : "s"}`;
    return `${docHead(name, d.t, note)}
      ${d.d ? `<p class="tg-doc-d">${md(d.d)}</p>` : ""}
      ${owns.length ? `<dl class="tg-doc-facts">
        <dt>Owns ${owns.length} ${unit}</dt><dd>${codes(owns)}</dd>
      </dl>` : ""}
      ${docSections(d.s)}`;
  }

  /* ALE software is off the shelf. Nothing in the environment says what Blender is, and
   * inventing a sentence would be worse than admitting it -- what the repo does record is
   * how a run reaches the software and which specialist owns it, so that is what this
   * shows. */
  function softPanel(t, name) {
    const d = softDoc(t, name);
    if (!d) return docMissing("software", name);
    const reach = [];
    if (d.m) reach.push(`imports as ${codes(d.m)}`);
    if (d.b) reach.push(`runs as ${codes(d.b)}`);
    if (d.r) reach.push(`loads the R namespace ${codes(d.r)}`);
    const facts = [
      d.canon !== name.toLowerCase() ? ["Canonically", `<code>${esc(d.canon)}</code>`] : null,
      reach.length ? ["In the sandbox", reach.join(", ")] : null,
      ["Held to the stage", d.e
        ? "by a guard, which refuses the import or the executable until the stage that grants it"
        : d.k
          ? "by the prompt's allowlist alone, which is as far as a guard reaches for this kind"
          : `by the prompt's allowlist alone: the registry carries no import or executable for
             this label to guard`],
      d.ft ? ["Owned by", `the <code>${esc(d.f)}</code> specialist, ${esc(d.ft)}`] : null,
      d.l ? ["Written in the corpus as", codes(d.l)] : null,
      d.n ? ["Needed by", `${d.n} task${d.n === 1 ? "" : "s"}${d.q
        ? `, offered to ${d.q}` : ""}`] : null,
    ].filter(Boolean);
    return `${docHead(name, d.k || "", "third-party software, as the harness provisions it")}
      <dl class="tg-doc-facts">${facts.map(([k, v]) =>
        `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>`;
  }

  /* The last chips on a task are not tools but the servers behind them, and the same
   * payload knows which gym answers for each. */
  function gymPanel(t, name) {
    const docs = loaded("gym");
    const gym = docs && (docs.servers || {})[name];
    if (!gym) return docMissing("gym", name);
    const served = docs.gyms[gym] || {};
    const offered = new Set([...names(t[T.ORACLE]), ...names(t[T.CUM]), ...names(t[T.SEL])]);
    const mine = [...offered].filter((x) => served[x]).length;
    return `${docHead(name, `${libLabel(gym)} gym`,
      "the MCP server this task's tools are served from")}
      <dl class="tg-doc-facts">
        <dt>Serves</dt><dd>${Object.keys(served).length} tools that tasks in this corpus
          reach for</dd>
        ${mine ? `<dt>Offered to this task</dt><dd>${mine} of them</dd>` : ""}
      </dl>`;
  }

  const PANEL = { tool: toolPanel, gym: gymPanel, skill: skillPanel, agent: agentPanel,
                  software: softPanel };

  /* Fill the panel that belongs to the clicked chip's own group, and let a second click on
   * the same chip close it again. */
  function openDoc(btn) {
    const grp = btn.closest(".tg-docgrp");
    const panel = grp && grp.querySelector("[data-tg-doc]");
    if (!panel) return;
    const kind = grp.dataset.kind in PANEL ? grp.dataset.kind : "tool";
    const was = btn.classList.contains("is-open");
    grp.querySelectorAll(".tg-chip.is-open").forEach((c) => c.classList.remove("is-open"));
    if (was) { panel.hidden = true; return; }
    btn.classList.add("is-open");
    panel.hidden = false;
    const name = btn.dataset.doc;
    if (loaded(kind)) { panel.innerHTML = PANEL[kind](S.open, name); return; }
    panel.innerHTML = '<p class="tg-sub">Reading the description\u2026</p>';
    loadDocs(kind).then(() => {
      /* The reader may have moved on, or closed the modal, while this was in flight. */
      if (btn.classList.contains("is-open") && btn.dataset.doc === name) {
        panel.innerHTML = PANEL[kind](S.open, name);
      }
    });
  }

  /* Figures in the detail view. Each is a button so it can open full size, and
   * the caption keeps the provenance of the file it came from. */
  function figBlock(t) {
    const figs = figures(t);
    if (!figs.length) return "";
    const isAle = env(t) === "ale";
    const head = isAle
      ? "What the task hands the agent"
      : `The environment it runs against${figs.length > 1 ? " (one per gym)" : ""}`;
    const lede = isAle
      ? "Staged artifacts and reference results, straight from the task directory."
      : "A live sandbox, seeded for this task and captured before the agent touches it.";
    return `<h4 class="tg-h4">${head}</h4>
      <p class="tg-sub">${lede}</p>
      <div class="tg-figs">${figs.map((f, k) => `<figure class="tg-fig">
        <button class="tg-figbtn" type="button" data-fig="${k}"
          title="${esc(f.note || "")}" aria-label="Open ${esc(f.caption)} full size">
          <img src="${esc(f.dir + f.file)}" alt="${esc(f.caption)}" loading="lazy" decoding="async">
          ${f.kind === "video" ? '<span class="tg-play" aria-hidden="true"></span>' : ""}
        </button>
        <figcaption>${esc(f.caption)}${f.kind === "video"
          ? ' <span class="tg-figtag">video</span>' : ""}</figcaption>
      </figure>`).join("")}</div>`;
  }

  function detail(t) {
    const tr = track(t);
    const isAle = env(t) === "ale";
    /* An ALE row's tools axis is installed software, not a gym's function tools, so it
     * reads from the other payload. */
    const kind = isAle && tr === "tools" ? "software" : AXIS_KIND[tr];
    const oracle = names(t[T.ORACLE]);
    const cum = names(t[T.CUM]);
    const extra = cum.filter((x) => !oracle.includes(x));
    const vs = vers(t);
    const fs = files(t);
    const must = names(t[T.MUST]);
    const soft = names(t[T.SOFT]);
    const sel = names(t[T.SEL]);
    const gym = names(t[T.GYM]);

    const facets = [
      isAle ? label(opt("categories", t[T.CAT])) : label(domain(t)),
      isAle ? opt("subdomains", t[T.SUB]) : null,
      isAle ? opt("taskSplits", t[T.TSPLIT]) : null,
    ].filter(Boolean);

    return `<div class="tg-dhead">
      <span class="tg-badges">
        <span class="tg-b is-${tr}">${esc(tr)}</span>
        <span class="tg-b is-env">${esc(label(env(t)))}</span>
        ${facets.map((f) => `<span class="tg-b is-env">${esc(f)}</span>`).join("")}
        <span class="tg-b is-stage">stage ${t[T.STAGE]}</span>
      </span>
      <h3 class="tg-dtitle">${esc(heading(t))}</h3>
      <p class="tg-did"><code>${esc(t[T.TID])}</code></p>
    </div>

    ${t[T.SUM] >= 0 ? `<p class="tg-sub">${esc(S.d.summaries[t[T.SUM]])}</p>` : ""}

    ${figBlock(t)}

    <h4 class="tg-h4">The request, as the agent received it</h4>
    <pre class="tg-pre">${esc(prompt(t))}</pre>

    <h4 class="tg-h4">Oracle ${esc(UNIT[tr])} &middot; what this task needs</h4>
    ${inspectable(t, kind)
      ? '<p class="tg-sub">Open any chip for what it is, and what it expects.</p>' : ""}
    ${docChips(oracle, t, kind)}
    <h4 class="tg-h4">Also in the pool at this stage${extra.length ? ` &middot; ${extra.length} more` : ""}</h4>
    ${extra.length
      ? `<p class="tg-sub">Offered alongside the oracle set, and not needed here.</p>${
        docChips(extra, t, kind, "is-extra")}`
      : '<p class="tg-sub">Nothing beyond the oracle set.</p>'}

    ${sel.length ? `<h4 class="tg-h4">Tools mounted for it (${sel.length})</h4>${
      docChips(sel, t, "tool", "is-extra")}` : ""}
    ${soft.length ? `<h4 class="tg-h4">Software</h4>${docChips(soft, t, "software", "is-extra")}` : ""}

    ${vs.length ? `<h4 class="tg-h4">Graded on ${vs.length} check${vs.length === 1 ? "" : "s"}</h4>
      <p class="tg-sub">Each reads the environment after the run. The agent never sees these.</p>
      ${vs.map((v) => `<div class="tg-vf">
        <div class="tg-vf-top">
          <span class="tg-vf-name">${esc(v[0] || "check")}</span>
          ${v[2] ? `<span class="tg-vf-kind">${esc(v[2].replace(/_/g, " "))}</span>` : ""}
          ${v[4] ? `<span class="tg-vf-exp">expects <b>${esc(v[4])}</b>${
            v[5] ? ` (${esc(v[5].replace(/_/g, " "))})` : ""}</span>` : ""}
        </div>
        ${v[1] && v[1] !== v[0] ? `<p class="tg-sub" style="margin:5px 0 0">${esc(v[1])}</p>` : ""}
        ${v[3] ? `<pre class="tg-sql">${esc(v[3])}</pre>` : ""}
      </div>`).join("")}` : ""}

    ${fs.length ? `<h4 class="tg-h4">Staged input files (${fs.length})</h4>
      <table class="tg-files"><thead><tr><th>File</th><th>Format</th><th>What it holds</th></tr></thead>
      <tbody>${fs.map((f) => `<tr>
        <td><code>${esc(f[2] || f[0])}</code></td>
        <td>${esc(f[1] || "\u2014")}</td>
        <td>${esc(f[3] || "\u2014")}</td>
      </tr>`).join("")}</tbody></table>` : ""}

    ${must.length ? `<h4 class="tg-h4">Required steps (${must.length})</h4>
      <ol class="tg-steps">${must.map((m) => `<li>${esc(m)}</li>`).join("")}</ol>` : ""}

    ${gym.length ? `<h4 class="tg-h4">Gym servers</h4>${
      docChips(gym, t, "gym", "is-extra")}` : ""}

    ${t[T.SYS] >= 0 ? `<h4 class="tg-h4">Operating policy given to the agent</h4>
      <pre class="tg-pre">${esc(S.d.sys[t[T.SYS]])}</pre>` : ""}`;
  }

  function open(i) {
    const t = S.rows[i];
    if (!t) return;
    S.open = t;
    el("[data-tg-detail]").innerHTML = detail(t);
    el("[data-tg-detail]").scrollTop = 0;
    const dlg = el("[data-tg-modal]");
    if (typeof dlg.showModal === "function") dlg.showModal();
    else dlg.setAttribute("open", "");
  }

  /* Full size view, stacked over the detail dialog. Video figures play the
   * short clip; stills load the full render. */
  function zoom(k) {
    if (!S.open) return;
    const f = figures(S.open)[k];
    if (!f) return;
    const media = f.clip
      ? `<video class="tg-lmedia" src="${esc(f.dir + f.clip)}"
           poster="${esc(f.dir + f.file)}" controls autoplay loop muted playsinline></video>`
      : `<img class="tg-lmedia" src="${esc(f.dir + f.file)}" alt="${esc(f.caption)}">`;
    const body = el("[data-tg-lbody]");
    body.innerHTML = `${media}
      <p class="tg-lcap">${esc(f.caption)}${f.note
        ? ` <span class="tg-lsrc">${esc(f.note)}</span>` : ""}</p>`;
    /* Size the frame to the picture's fitted box. Letting the dialog take its
     * intrinsic width instead would leave a tall figure — a whole-slide scan
     * is 1:2.3 — floating in a frame twice as wide as the image inside it. */
    const pad = 22;
    const maxW = Math.min(window.innerWidth * 0.96, 1240) - pad;
    const maxH = window.innerHeight * 0.82;
    const scale = f.w && f.h ? Math.min(maxW / f.w, maxH / f.h, 1) : 1;
    body.style.width = `${Math.round((f.w ? f.w * scale : maxW) + pad)}px`;

    const dlg = el("[data-tg-lbox]");
    if (typeof dlg.showModal === "function") dlg.showModal();
    else dlg.setAttribute("open", "");
  }

  // -- facets and wiring --------------------------------------------------- //

  function fill(sel, values, anyLabel, text) {
    const cur = sel.value;
    sel.innerHTML = `<option value="">${anyLabel}</option>`
      + values.map((v) => `<option value="${esc(v)}">${esc(text ? text(v) : v)}</option>`).join("");
    sel.value = values.map(String).indexOf(cur) >= 0 ? cur : "";
  }

  /* Domains are per environment: an ALE category is not an EOG domain. */
  function refreshFacets() {
    const doms = new Set();
    S.d.tasks.forEach((t) => {
      if (S.f.track && track(t) !== S.f.track) return;
      if (S.f.env && env(t) !== S.f.env) return;
      doms.add(domain(t));
    });
    fill(el('[data-f="domain"]'), Array.from(doms).sort(), "all", label);
    S.f.domain = el('[data-f="domain"]').value;
    /* The ALE tier only exists on ALE tasks. */
    const aleOnly = el('[data-f="tsplit"]').closest(".cs-fl");
    if (aleOnly) aleOnly.hidden = S.f.env === "eog";
  }

  function wire() {
    let debounce = null;
    el("[data-tg-toolbar]").addEventListener("input", (e) => {
      const t = e.target.closest("[data-f]");
      if (!t) return;
      S.f[t.dataset.f] = t.value;
      if (t.dataset.f === "track" || t.dataset.f === "env") refreshFacets();
      if (t.dataset.f === "q") {
        clearTimeout(debounce);
        debounce = setTimeout(() => render(), 220);
        return;
      }
      render();
    });
    el("[data-tg-grid]").addEventListener("click", (e) => {
      const c = e.target.closest(".tg-card[data-i]");
      if (c) open(Number(c.dataset.i));
    });
    el("[data-tg-more]").addEventListener("click", () => render(true));
    el("[data-tg-stats]").addEventListener("click", (e) => {
      const s = e.target.closest(".tg-stat");
      if (!s) return;
      const on = s.classList.contains("is-active");
      S.f.track = on ? "" : s.dataset.track;
      S.f.env = on ? "" : s.dataset.env;
      el('[data-f="track"]').value = S.f.track;
      el('[data-f="env"]').value = S.f.env;
      refreshFacets();
      render();
    });

    const dlg = el("[data-tg-modal]");
    el("[data-tg-close]").addEventListener("click", () => dlg.close());
    dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
    el("[data-tg-detail]").addEventListener("click", (e) => {
      const b = e.target.closest("[data-fig]");
      if (b) { zoom(Number(b.dataset.fig)); return; }
      const chip = e.target.closest(".tg-chip.is-doc");
      if (chip) openDoc(chip);
    });

    /* Stop the clip on close so audio-less playback doesn't keep decoding. */
    const lb = el("[data-tg-lbox]");
    const shut = () => lb.close();
    el("[data-tg-lclose]").addEventListener("click", shut);
    lb.addEventListener("click", (e) => { if (e.target === lb) shut(); });
    lb.addEventListener("close", () => { el("[data-tg-lbody]").innerHTML = ""; });
  }

  function stats() {
    const per = new Map();
    S.d.tasks.forEach((t) => {
      const k = `${track(t)}\u0001${env(t)}`;
      per.set(k, (per.get(k) || 0) + 1);
    });
    const order = [];
    axisOrder(S.d.tracks).forEach((tr) => ["eog", "ale"].forEach((ev) => {
      const n = per.get(`${tr}\u0001${ev}`);
      if (n) order.push([tr, ev, n]);
    }));
    el("[data-tg-stats]").innerHTML = order.map(([tr, ev, n]) =>
      `<button class="tg-stat" type="button" data-track="${esc(tr)}" data-env="${esc(ev)}"
        title="Show only ${esc(tr)} tasks on ${esc(label(ev))}">
        <b>${n}</b><i>${esc(tr)} &middot; ${esc(label(ev))}</i>
      </button>`).join("");
  }

  async function load() {
    if (S.loading || S.d) return;
    S.loading = true;
    let d;
    try {
      const r = await fetch("static/tasks.json");
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      d = await r.json();
    } catch (err) {
      el("[data-tg-count]").textContent = "unavailable";
      el("[data-tg-grid]").innerHTML = `<p class="tg-none">The task corpus could not be
        loaded (${esc(err.message || err)}). It is fetched at runtime, so this page has to be
        served over HTTP rather than opened from the filesystem.</p>`;
      return;
    }
    S.d = d;
    const stages = Array.from(new Set(d.tasks.map((t) => t[T.STAGE]))).sort((a, b) => a - b);
    fill(el('[data-f="track"]'), axisOrder(d.tracks), "all axes");
    fill(el('[data-f="env"]'), ["eog", "ale"].filter((e) => d.envs.includes(e)), "both", label);
    fill(el('[data-f="stage"]'), stages, "all", (v) => "stage " + v);
    fill(el('[data-f="tsplit"]'), d.taskSplits.slice().sort(), "any");
    /* No manifests (page rebuilt without the corpus or the gyms) — drop the
     * control rather than offer a filter that matches nothing. */
    const figCtl = el('[data-f="fig"]').closest(".cs-fl");
    if (figCtl && !Object.keys(d.envFigures || {}).length
        && !Object.keys(d.aleFigures || {}).length) figCtl.hidden = true;
    refreshFacets();
    stats();
    el("[data-tg-toolbar]").hidden = false;
    wire();
    render();
  }

  function init() {
    const root = document.getElementById("tasks");
    if (!root) return;
    const observe = () => {
      if (!("IntersectionObserver" in window)) { load(); return; }
      const io = new IntersectionObserver((es) => {
        if (es.some((e) => e.isIntersecting)) { io.disconnect(); load(); }
      }, { rootMargin: "400px" });
      io.observe(root);
    };
    if (document.readyState === "complete") observe();
    else window.addEventListener("load", observe, { once: true });
  }
  return { init, load };
})();

/* Leaderboard: the paper's main-results tables plus the appendix rows, ranked and plotted.
 *
 * Three views over the same rows. `Ranking` is the table itself, sortable, because the
 * paper orders rows by method family rather than by score. `Strict vs partial` puts Pass
 * beside Score so the partial-credit gap is visible -- on tools the leader passes 38.6% of
 * tasks outright while averaging 68.9% of the checks, which is the difference between
 * finishing a workflow and getting most of it right. `Efficiency` plots score against what
 * it cost in tokens and in agent-hours, since two systems within a point of each other can
 * be an order of magnitude apart on spend.
 *
 * Every row is ranked in one field, including the appendix systems, so each one states its
 * backbone model and scaffold and the facets are filterable. That puts the burden on the
 * reader to notice when a comparison is not controlled -- a Sonnet-4.6 row next to a GPT-5
 * one -- rather than hiding those rows in a separate table, but it does make the mixture
 * visible instead of implicit. */
const LB = (() => {
  const AXES = ["tools", "skills", "agents"];
  const FACETS = ["llm", "harness", "cat", "agency"];
  const S = {
    axis: "tools", view: "rank", env: "eog", sort: "overall", asc: false,
    f: { llm: "", harness: "", cat: "", agency: "" },
  };

  const el = (sel) => document.querySelector(sel);
  const esc = (v) => String(v == null ? "" : v).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const n1 = (v) => (v == null ? null : Number(v));
  /* Keep the paper's own precision: it prints 148.0 and 150.8, but whole millions once
   * the agents axis runs into the hundreds. */
  const tok = (v) => (v == null ? "\u2014"
    : Number.isInteger(v) && v >= 150 ? String(v) : v.toFixed(1));

  const CAT = {
    ref: { c: "#94a3b8", label: "Task-specific reference" },
    deploy: { c: "#4e54c8", label: "Frontier deployment" },
    memory: { c: "#d97706", label: "Memory-based" },
    prompt: { c: "#0f766e", label: "Prompt-based" },
    code: { c: "#c2410c", label: "Code-based" },
    skill: { c: "#be185d", label: "Skill learning" },
  };
  const col = (r) => (CAT[r.cat] || CAT.ref).c;

  const AGENCY = { sas: "Single-agent", mas: "Multi-agent" };
  /* A row names only what it changes; everything else comes from its axis. */
  const facet = (r, k, axis) => (k === "agency"
    ? r.agency || (r.mas ? "mas" : RESULTS[axis || S.axis].agency)
    : r[k] || RESULTS[axis || S.axis][k]);
  const facetLabel = (k, v) => (k === "cat" ? (CAT[v] || {}).label || v
    : k === "agency" ? AGENCY[v] || v : v);

  /* The whole field for an axis: the paper's main table plus its appendix rows. */
  const allRows = (axis) =>
    RESULTS[axis].rows.filter((r) => !r.sec).concat(RESULTS[axis].more || []);

  const systems = (axis) => allRows(axis).filter((r) =>
    FACETS.every((k) => !S.f[k] || facet(r, k, axis) === S.f[k]));

  /* Distinct values for a facet, in the order the rows introduce them. */
  function options(axis, k) {
    const out = [];
    allRows(axis).forEach((r) => {
      const v = facet(r, k, axis);
      if (v && !out.includes(v)) out.push(v);
    });
    return out;
  }

  const ENV = { eog: "EOG", ale: "ALE" };
  const K = {
    eog: { pass: "eog", sd: "eogSd", score: "eogScore", scoreSd: "eogScoreSd", h: "eogH", t: "eogTok" },
    ale: { pass: "ale", sd: "aleSd", score: "aleScore", scoreSd: "aleScoreSd", h: "aleH", t: "aleTok" },
  };

  // -- ranked table -------------------------------------------------------- //

  const COLS = [
    { k: "eog", lab: "Pass %", grp: "eog", sd: "eogSd", pct: true },
    { k: "eogScore", lab: "Score", grp: "eog", sd: "eogScoreSd" },
    { k: "eogH", lab: "Hours", grp: "eog" },
    { k: "eogTok", lab: "Tok. (M)", grp: "eog", tok: true },
    { k: "ale", lab: "Pass %", grp: "ale", sd: "aleSd", pct: true },
    { k: "aleScore", lab: "Score", grp: "ale", sd: "aleScoreSd" },
    { k: "aleH", lab: "Hours", grp: "ale" },
    { k: "aleTok", lab: "Tok. (M)", grp: "ale", tok: true },
    { k: "overall", lab: "Overall", grp: "ov" },
  ];

  function ranked(axis) {
    const rows = systems(axis).slice();
    const key = S.sort;
    rows.sort((a, b) => {
      const x = n1(a[key]);
      const y = n1(b[key]);
      if (x == null && y == null) return 0;
      if (x == null) return 1;                       /* unfinished runs sort last either way */
      if (y == null) return -1;
      return S.asc ? x - y : y - x;
    });
    return rows;
  }

  function rankTable(axis) {
    const rows = ranked(axis);
    const spec = RESULTS[axis];
    /* Best per column, so the eye can find it without reading every cell. Measured over
     * the competing systems only: the control often holds an extreme -- it is handed just
     * the tools its task needs, so of course it spends the fewest tokens -- and letting it
     * win a column would leave that column with no mark at all. */
    const best = {};
    COLS.forEach((c) => {
      const vals = systems(axis).filter((r) => !r.ref).map((r) => n1(r[c.k])).filter((v) => v != null);
      if (vals.length) best[c.k] = c.tok || c.k.endsWith("H") ? Math.min(...vals) : Math.max(...vals);
    });
    const rankOf = new Map();
    systems(axis).slice().sort((a, b) => (n1(b.overall) ?? -1) - (n1(a.overall) ?? -1))
      .forEach((r, i) => rankOf.set(r, n1(r.overall) == null ? null : i + 1));

    /* On the agents axis every row is a native MAS, so a tag on all of them would carry
     * no information; the axis note says it once instead. */
    const mixedAgency = options(axis, "agency").length > 1;

    const th = (c) => `<th class="${S.sort === c.k ? "is-sorted" + (S.asc ? " is-asc" : "") : ""}"
      data-sort="${c.k}" title="Sort by ${esc(c.lab)}">${esc(c.lab)}</th>`;

    return `<div class="lb-wrap"><table class="lb">
      <thead>
        <tr class="lb-grp">
          <th colspan="4"></th>
          <th class="lb-eog" colspan="4">EvoHarnessBench-EOG &middot; ${spec.tasks.eog} tasks</th>
          <th class="lb-ale" colspan="4">EvoHarnessBench-ALE &middot; ${spec.tasks.ale} tasks</th>
          <th></th>
        </tr>
        <tr>
          <th data-sort="overall" title="Rank by overall pass rate">#</th>
          <th data-sort="name">System</th>
          <th>LLM</th>
          <th>Harness</th>
          ${COLS.map(th).join("")}
        </tr>
      </thead>
      <tbody>${rows.map((r) => {
        const rk = rankOf.get(r);
        const cls = [r.ref ? "is-ref" : "", rk && rk <= 3 && !r.ref ? "is-top" : ""].join(" ").trim();
        const llm = facet(r, "llm", axis);
        const cell = (c) => {
          const v = n1(r[c.k]);
          if (v == null) return `<td class="${c.k === "overall" ? "lb-ov" : ""}"><span class="lb-dash">\u2014</span></td>`;
          const hi = best[c.k] != null && Math.abs(v - best[c.k]) < 1e-9 && !r.ref;
          const sd = c.sd ? n1(r[c.sd]) : null;
          const txt = c.tok ? tok(v) : v.toFixed(1);
          return `<td class="${c.k === "overall" ? "lb-ov " : ""}${hi ? "lb-hi" : ""}">${txt}${
            sd != null ? `<span class="lb-sd">\u00b1${sd.toFixed(1)}</span>` : ""}</td>`;
        };
        return `<tr class="${cls}">
          <td><span class="lb-rk is-${rk}">${rk ?? "\u2014"}</span></td>
          <td><span class="lb-nm">${esc(r.name)}</span>${
            r.ref ? '<span class="lb-tag is-ref">control</span>' : ""}${
            mixedAgency && facet(r, "agency", axis) === "mas"
              ? '<span class="lb-tag is-mas">multi-agent</span>' : ""}
            <br><span class="lb-cat">${esc((CAT[r.cat] || CAT.ref).label)}</span></td>
          <td class="lb-meta"><span class="lb-llm${
            llm === spec.llm ? "" : " is-alt"}">${esc(llm)}</span></td>
          <td class="lb-meta">${esc(facet(r, "harness", axis))}</td>
          ${COLS.map(cell).join("")}
        </tr>`;
      }).join("")}</tbody>
    </table></div>
    <p class="lb-cap">Click a column to sort. Bold indigo marks the best value in a column
      &mdash; highest for pass and score, lowest for hours and tokens, measured over whatever
      the filters leave in view. The control rows are task-specific harnesses, which are
      reference conditions rather than competing systems.
      <b>The LLM and Harness columns decide which comparisons hold.</b> The backbone is held at
      ${esc(spec.llm)} across the controlled systems, so a difference down a column between two
      of them is a difference in method.${rows.some((r) => facet(r, "llm", axis) !== spec.llm)
        ? ` A highlighted model marks a row that changes the backbone as well, which makes it a
           controlled comparison only against rows sharing its model and harness &mdash; filter
           to one of each to get that comparison on its own.` : ""}${
        rows.some((r) => r.cat === "skill")
        ? ` The skill-learning rows are an EOG-only ablation, so their ALE columns and overall
           rate are empty rather than imputed, and with no overall rate they take no rank in the
           # column &mdash; sort by EOG Pass to order them.` : ""}</p>`;
  }

  // -- shared SVG helpers -------------------------------------------------- //

  const svg = (w, h, body) =>
    `<svg viewBox="0 0 ${w} ${h}" role="img" preserveAspectRatio="xMidYMid meet">${body}</svg>`;

  /* Two lines at most; system names are short but "Reasoning Bank" needs the break. */
  function wrap(name, at) {
    if (name.length <= at) return [name];
    const i = name.lastIndexOf(" ", at + 3);
    return i <= 0 ? [name] : [name.slice(0, i), name.slice(i + 1)];
  }

  const legend = (items) => `<div class="lb-legend">${items.map((i) =>
    `<span><i style="background:${i.c};${i.o ? `opacity:${i.o}` : ""}"></i>${esc(i.lab)}</span>`).join("")}</div>`;

  /* Both chart views are per-environment, so both need the EOG/ALE switch. */
  const envBtns = () => `<div class="lb-seg is-ghost" data-lb-env style="margin:0 auto 12px;display:table">
    ${Object.keys(ENV).map((e) => `<button class="lb-segb${e === S.env ? " is-active" : ""}"
      type="button" data-env2="${e}">${ENV[e]}</button>`).join("")}</div>`;

  // -- strict vs partial --------------------------------------------------- //

  function gapChart(axis) {
    const k = K[S.env];
    const rows = systems(axis).filter((r) => n1(r[k.pass]) != null);
    const W = 1000;
    if (!rows.length) {
      return `${envBtns()}<p class="lb-cap">No system in view reports ${ENV[S.env]} results
        &mdash; the skill-learning ablation was run on EOG only.</p>`;
    }
    /* Past a dozen groups the names stop fitting on two stacked lines, so they tilt and
     * the plot grows a deeper gutter to hold them. */
    const crowded = rows.length > 12;
    const H = crowded ? 520 : 440;
    const L = 44;
    const R = 12;
    const T = 24;
    const B = crowded ? 150 : 72;
    const pw = W - L - R;
    const ph = H - T - B;
    /* ALE tops out near 35 and EOG near 69, so a fixed 0-100 would flatten one of them. */
    const peak = Math.max(...rows.flatMap((r) =>
      [(n1(r[k.pass]) || 0) + (n1(r[k.sd]) || 0), (n1(r[k.score]) || 0) + (n1(r[k.scoreSd]) || 0)]));
    const top = Math.max(20, Math.ceil((peak + 4) / 10) * 10);
    const y = (v) => T + ph - (v / top) * ph;
    const gw = pw / rows.length;
    const bw = Math.min(38, gw * 0.30);

    let g = "";
    for (let i = 0; i <= 5; i++) {
      const v = (top / 5) * i;
      g += `<line class="lb-gl" x1="${L}" y1="${y(v)}" x2="${W - R}" y2="${y(v)}"/>
        <text class="lb-ax" x="${L - 8}" y="${y(v) + 4}" text-anchor="end">${v % 1 ? v.toFixed(1) : v}</text>`;
    }
    g += `<line class="lb-zl" x1="${L}" y1="${y(0)}" x2="${W - R}" y2="${y(0)}"/>`;
    g += `<text class="lb-axt" transform="translate(13,${T + ph / 2}) rotate(-90)" text-anchor="middle">Percent</text>`;

    rows.forEach((r, i) => {
      const cx = L + gw * (i + 0.5);
      const c = col(r);
      const pair = [
        { v: n1(r[k.pass]), sd: n1(r[k.sd]), o: 0.4, dx: -bw * 0.56 },
        { v: n1(r[k.score]), sd: n1(r[k.scoreSd]), o: 1, dx: bw * 0.56 },
      ];
      pair.forEach((p) => {
        if (p.v == null) return;
        const x = cx + p.dx - bw / 2;
        g += `<rect x="${x.toFixed(1)}" y="${y(p.v).toFixed(1)}" width="${bw.toFixed(1)}"
          height="${(y(0) - y(p.v)).toFixed(1)}" rx="2" fill="${c}" fill-opacity="${p.o}"/>`;
        const top = p.sd ? y(p.v + p.sd) : y(p.v);
        if (p.sd) {
          const cxb = x + bw / 2;
          const lo = y(Math.max(0, p.v - p.sd));
          g += `<path class="lb-wh" d="M${cxb} ${top} V${lo} M${cxb - 4} ${top} H${cxb + 4} M${cxb - 4} ${lo} H${cxb + 4}"/>`;
        }
        g += `<text class="lb-vl" x="${(x + bw / 2).toFixed(1)}" y="${(top - 6).toFixed(1)}"
          text-anchor="middle">${p.v.toFixed(1)}</text>`;
      });
      /* Colour carries the method family; a caption per group would collide at this width. */
      const ly = y(0) + 16;
      g += crowded
        ? `<text class="lb-ax" x="${cx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="end"
            transform="rotate(-40 ${cx.toFixed(1)} ${ly.toFixed(1)})">${esc(r.name)}</text>`
        : wrap(r.name, 12).map((ln, j) =>
            `<text class="lb-ax" x="${cx.toFixed(1)}" y="${y(0) + 18 + j * 13}" text-anchor="middle">${esc(ln)}</text>`
          ).join("");
    });


    /* Two different reasons for a missing bar, and they must not be conflated: the
     * skill-learning ablation has no ALE arm at all, whereas a handful of MAS runs were
     * attempted and could not be finished. */
    const gone = systems(axis).filter((r) => n1(r[k.pass]) == null);
    const list = (rs) => rs.map((r) => esc(r.name)).join(", ").replace(/, ([^,]*)$/, " and $1");
    const noArm = gone.filter((r) => r.cat === "skill");
    const unfinished = gone.filter((r) => r.cat !== "skill");
    const missing = [
      noArm.length ? `${list(noArm)} are an EOG-only ablation with no ${ENV[S.env]} arm` : "",
      unfinished.length ? `${list(unfinished)} could not complete ${ENV[S.env]} within a
        comparable compute budget` : "",
    ].filter(Boolean).join("; ");
    return `${envBtns()}
    <div class="lb-fig">
      <p class="lb-figh">Strict pass rate against partial credit &mdash; ${ENV[S.env]}, ${axis}</p>
      <p class="lb-figs">Left bar of each pair is Pass (%): every verifier on the task passed.
        Right bar is Score: the mean fraction of verifiers that passed. Whiskers are &plusmn;1
        population standard deviation over 3 runs.</p>
      ${legend([{ c: "#64748b", lab: "Pass (%) — all checks", o: 0.4 },
                { c: "#64748b", lab: "Score — mean checks passed" }].concat(
        Array.from(new Set(rows.map((r) => r.cat))).map((c) => ({ c: CAT[c].c, lab: CAT[c].label }))))}
      ${svg(W, H, g)}
    </div>
    <p class="lb-cap">The two bars answer different questions. A tall right bar with a short left
      one is a system that gets most of a workflow right and rarely finishes it &mdash; which is
      the shape of nearly every row here.${missing ? ` Not plotted: ${missing}.` : ""}</p>`;
  }

  // -- efficiency ---------------------------------------------------------- //

  /* Nice 1-2-5 ticks across the decades the data actually spans. */
  function logTicks(lo, hi) {
    const out = [];
    for (let d = Math.floor(Math.log10(lo)); d <= Math.ceil(Math.log10(hi)); d++) {
      [1, 2, 5].forEach((m) => {
        const v = m * Math.pow(10, d);
        if (v >= lo * 0.95 && v <= hi * 1.05) out.push(v);
      });
    }
    return out;
  }

  /* A 1-2-5 step that lands 4-6 ticks on the range, so axes read in round numbers. */
  function niceScale(lo, hi) {
    const span = hi - lo || 1;
    const raw = span / 5;
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) || 10 * mag;
    let from = Math.floor(lo / step) * step;
    let to = Math.ceil(hi / step) * step;
    /* Filtering down to a single system leaves lo === hi, and if that value sits on a step
     * boundary the rounding above collapses the range to nothing -- which divides by zero
     * in every coordinate derived from it. Give a lone point an axis to sit on instead. */
    if (to - from < step / 2) { from -= step; to += step; }
    const ticks = [];
    for (let v = from; v <= to + step / 2; v += step) ticks.push(Number(v.toFixed(6)));
    return { from, to, ticks };
  }

  function scatter(axis, xKey, xLab, title, sub, useLog) {
    const k = K[S.env];
    const rows = systems(axis).filter((r) => n1(r[k.pass]) != null && n1(r[xKey]) != null);
    /* The appendix rows report no cost, so a filter can leave this plot with nothing to
     * draw. Say that, rather than framing an empty pair of axes. */
    if (!rows.length) {
      return `<div class="lb-fig">
        <p class="lb-figh">${esc(title)}</p>
        <p class="lb-figs">${sub}</p>
        <p class="lb-none">No ${ENV[S.env]} cost figures for the systems in view.</p>
      </div>`;
    }
    /* Labels are laid out in viewBox units, so a fuller field needs a larger canvas
     * rather than a larger container: stretching the SVG scales the collisions up with
     * everything else. Room in these units is what lets a name sit beside its point. */
    const many = rows.length > 12;
    const W = many ? 760 : 500;
    const H = many ? 470 : 360;
    const L = 42;
    const R = 14;
    const T = 16;
    const B = 46;
    const pw = W - L - R;
    const ph = H - T - B;

    const xs = rows.map((r) => n1(r[xKey]));
    const ys = rows.map((r) => n1(r[k.pass]));
    const xlo = Math.min(...xs);
    const xhi = Math.max(...xs);
    /* Scores cluster in a narrow band, so the y axis follows the data instead of
     * starting at zero -- otherwise every point piles into the top third and the
     * labels have nowhere to go. */
    const yr = niceScale(Math.min(...ys), Math.max(...ys));
    const sx = useLog
      ? (v) => L + (Math.log10(v) - Math.log10(xlo * 0.8)) /
          (Math.log10(xhi * 1.25) - Math.log10(xlo * 0.8)) * pw
      : (v) => L + (v / (xhi * 1.12)) * pw;
    const sy = (v) => T + ph - ((v - yr.from) / (yr.to - yr.from)) * ph;

    let g = "";
    yr.ticks.forEach((v) => {
      g += `<line class="lb-gl" x1="${L}" y1="${sy(v)}" x2="${W - R}" y2="${sy(v)}"/>
        <text class="lb-ax" x="${L - 7}" y="${sy(v) + 4}" text-anchor="end">${
          v % 1 ? v.toFixed(1) : v}</text>`;
    });
    (useLog ? logTicks(xlo * 0.8, xhi * 1.25) : niceScale(0, xhi * 1.12).ticks)
      .forEach((v) => {
        if (v <= 0 && useLog) return;
        const x = sx(v);
        if (x < L - 1 || x > W - R + 1) return;
        g += `<text class="lb-ax" x="${x.toFixed(1)}" y="${T + ph + 15}" text-anchor="middle">${
          v >= 1000 ? (v / 1000) + "k" : v}</text>`;
      });
    g += `<line class="lb-zl" x1="${L}" y1="${T + ph}" x2="${W - R}" y2="${T + ph}"/>`;
    g += `<text class="lb-axt" x="${L + pw / 2}" y="${H - 8}" text-anchor="middle">${esc(xLab)}</text>`;
    g += `<text class="lb-axt" transform="translate(12,${T + ph / 2}) rotate(-90)" text-anchor="middle">Pass (%)</text>`;

    /* Side is chosen per point so the right edge does not run off, then labels on the
     * same side are pushed apart and joined to their point by a leader line. */
    const pts = rows.map((r) => ({
      r, x: sx(n1(r[xKey])), y: sy(n1(r[k.pass])),
      right: sx(n1(r[xKey])) < L + pw * 0.66,
    }));
    /* One pass over every label, not per side: two labels pointing at each other from
     * opposite sides still collide in the middle, and only distinct vertical bands
     * rule that out for good. */
    let last = -Infinity;
    pts.slice().sort((a, b) => a.y - b.y).forEach((p) => {
      p.ly = Math.max(p.y + 3.5, last + 15);   /* rendered line box, not the font size */
      last = p.ly;
    });
    /* Recentre the stack on the cloud it came from, so it does not drift downward. */
    const drift = (last - (T + ph)) > 0 ? last - (T + ph) : 0;
    if (drift) pts.forEach((p) => { p.ly -= drift; });
    /* Clearing the other labels is not enough: a name can still come to rest on top of
     * somebody else's point, which reads as if that system were unlabelled. Text is not
     * measurable while the string is still being built, so estimate the box from the
     * character count at 10.5px bold, then take whichever side and offset covers the
     * fewest points -- nearest and on the original side when they tie. */
    const lw = (name) => name.length * 5.7 + 3;
    const boxOf = (lx, ly, name, right) => {
      const x0 = right ? lx : lx - lw(name);
      return { x0, x1: x0 + lw(name), y0: ly - 8.5, y1: ly + 2.5 };
    };
    const covered = (b) => pts.filter((q) => {
      const cx = Math.max(b.x0, Math.min(q.x, b.x1));
      const cy = Math.max(b.y0, Math.min(q.y, b.y1));
      return (q.x - cx) ** 2 + (q.y - cy) ** 2 < 6.5 ** 2;   /* marker plus its white ring */
    }).length;
    pts.forEach((p) => {
      const tries = [];
      [p.right, !p.right].forEach((side) => [10, 17, 26].forEach((off) => {
        const lx = p.x + (side ? off : -off);
        const b = boxOf(lx, p.ly, p.r.name, side);
        if (b.x0 < L - 1 || b.x1 > W - R + 1) return;        /* stays inside the plot */
        tries.push({ side, lx, n: covered(b), off, home: side === p.right ? 0 : 1 });
      }));
      const pick = tries.sort((a, b) => a.n - b.n || a.home - b.home || a.off - b.off)[0];
      if (pick) { p.right = pick.side; p.lx = pick.lx; }
      else p.lx = p.x + (p.right ? 10 : -10);
    });
    pts.forEach((p) => {
      const c = col(p.r);
      const lx = p.lx;
      g += `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="5" fill="${c}"
        stroke="#fff" stroke-width="1.5"/>`;
      if (p.ly - p.y - 3.5 > 2) {
        g += `<line x1="${p.x.toFixed(1)}" y1="${(p.y + (p.ly > p.y ? 5 : -5)).toFixed(1)}"
          x2="${lx.toFixed(1)}" y2="${(p.ly - 3.5).toFixed(1)}"
          stroke="${c}" stroke-width=".8" opacity=".4"/>`;
      }
      g += `<text class="lb-pt-l" x="${lx.toFixed(1)}"
        y="${p.ly.toFixed(1)}" text-anchor="${p.right ? "start" : "end"}" fill="${c}">${esc(p.r.name)}</text>`;
    });

    return `<div class="lb-fig">
      <p class="lb-figh">${esc(title)}</p>
      <p class="lb-figs">${sub}</p>
      ${svg(W, H, g)}
    </div>`;
  }

  function effView(axis) {
    const k = K[S.env];
    /* Cost is the one thing the appendix tables do not report, so the legend follows the
     * points that exist rather than the rows on the axis -- otherwise it advertises a
     * family with nothing plotted under it. */
    const plotted = systems(axis).filter((r) =>
      n1(r[k.pass]) != null && (n1(r[k.t]) != null || n1(r[k.h]) != null));
    const gone = systems(axis).filter((r) => !plotted.includes(r));
    /* Same two reasons the bars distinguish, and the same care: a row can be absent because
     * the ablation never ran this environment, or because it ran and the cost was not
     * recorded. Most of the skill-learning field reports cost, so the family it belongs to
     * no longer says which case a row is. */
    const list = (rs) => rs.map((r) => esc(r.name)).join(", ").replace(/, ([^,]*)$/, " and $1");
    const noArm = gone.filter((r) => n1(r[k.pass]) == null);
    const noCost = gone.filter((r) => n1(r[k.pass]) != null);
    const missing = [
      noArm.length ? `${list(noArm)} report no ${ENV[S.env]} results at all` : "",
      noCost.length ? `the record keeps no ${ENV[S.env]} tokens or duration for ${
        list(noCost)}` : "",
    ].filter(Boolean).join("; ");
    return `${envBtns()}
    <div class="lb-effgrid${plotted.length > 12 ? " is-roomy" : ""}">
      ${scatter(axis, k.t, "Tokens per sweep (millions, log scale)",
        `Score against tokens \u2014 ${ENV[S.env]}`,
        "Input plus output over the sweep, on a log scale. Up and to the left is better.", true)}
      ${scatter(axis, k.h, "Agent-hours per sweep",
        `Score against time \u2014 ${ENV[S.env]}`,
        "Summed agent duration rather than wall clock. Up and to the left is better.", false)}
    </div>
    ${legend(Array.from(new Set(plotted.map((r) => r.cat)))
      .map((c) => ({ c: CAT[c].c, lab: CAT[c].label })))}
    <p class="lb-cap">The vertical axis is cropped to the range the systems occupy, since they sit in
      a narrow band. Nothing here is a dollar figure &mdash; the record keeps tokens and duration,
      not price.${missing ? ` Not plotted: ${missing}.` : ""}</p>`;
  }

  // -- wiring -------------------------------------------------------------- //

  /* Options are rebuilt per axis, since the facets an axis actually varies differ: only
   * tools mixes single- and multi-agent, and only skills carries a second backbone. A
   * facet with one value is dropped rather than shown as a select that cannot do
   * anything. Selections that the new axis cannot honour are cleared. */
  function paintFilters(axis) {
    FACETS.forEach((k) => {
      const sel = el(`[data-lbf="${k}"]`);
      if (!sel) return;
      const opts = options(axis, k);
      if (S.f[k] && !opts.includes(S.f[k])) S.f[k] = "";
      sel.closest(".cs-fl").hidden = opts.length < 2;
      sel.innerHTML = `<option value="">All</option>${opts.map((v) =>
        `<option value="${esc(v)}"${v === S.f[k] ? " selected" : ""}>${esc(facetLabel(k, v))}</option>`
      ).join("")}`;
    });
    const on = FACETS.filter((k) => S.f[k]);
    const total = allRows(axis).length;
    const shown = systems(axis).length;
    const reset = el("[data-lb-reset]");
    if (reset) reset.hidden = !on.length;
    const count = el("[data-lb-count]");
    if (count) {
      count.textContent = on.length
        ? `${shown} of ${total} systems`
        : `${total} systems`;
    }
  }

  function paint() {
    const axis = S.axis;
    paintFilters(axis);

    const spec = RESULTS[axis];
    const empty = !systems(axis).length;
    el("[data-lb-note]").innerHTML = `Evolving <b>${axis}</b> &middot; ${spec.tasks.eog} EOG and
      ${spec.tasks.ale} ALE evaluation tasks &middot; ${esc(spec.host)}.`;
    const blank = `<p class="lb-cap">No system on this axis matches every filter.</p>`;
    el("[data-lb-rank]").innerHTML = S.view !== "rank" ? "" : empty ? blank : rankTable(axis);
    el("[data-lb-gap]").innerHTML = S.view !== "gap" ? "" : empty ? blank : gapChart(axis);
    el("[data-lb-eff]").innerHTML = S.view !== "eff" ? "" : empty ? blank : effView(axis);
    document.querySelectorAll("[data-lb-panel]").forEach((p) =>
      p.classList.toggle("is-active", p.dataset.lbPanel === S.view));
    document.querySelectorAll("[data-lb-axis] .lb-segb").forEach((b) =>
      b.classList.toggle("is-active", b.dataset.axis === S.axis));
    document.querySelectorAll("[data-lb-view] .lb-segb").forEach((b) =>
      b.classList.toggle("is-active", b.dataset.view === S.view));
  }

  function init() {
    const root = document.getElementById("leaderboard");
    if (!root) return;
    root.addEventListener("change", (e) => {
      const sel = e.target.closest("[data-lbf]");
      if (!sel) return;
      S.f[sel.dataset.lbf] = sel.value;
      paint();
    });
    root.addEventListener("click", (e) => {
      const ax = e.target.closest("[data-lb-axis] .lb-segb");
      if (ax) { S.axis = ax.dataset.axis; paint(); return; }
      const vw = e.target.closest("[data-lb-view] .lb-segb");
      if (vw) { S.view = vw.dataset.view; paint(); return; }
      const ev = e.target.closest("[data-env2]");
      if (ev) { S.env = ev.dataset.env2; paint(); return; }
      if (e.target.closest("[data-lb-reset]")) {
        FACETS.forEach((k) => { S.f[k] = ""; });
        paint();
        return;
      }
      const th = e.target.closest("th[data-sort]");
      if (th) {
        const k = th.dataset.sort;
        if (k === "name") return;
        S.asc = S.sort === k ? !S.asc : false;
        S.sort = k;
        paint();
      }
    });
    paint();
  }
  return { init };
})();

/* Page-level tabs. Each .pv-view owns the sections inside it, so an existing
   in-page link like #results keeps working: it opens the owning view first. */
const PV = (() => {
  const owner = new Map();   // section id (and view key) -> view key
  const keys = [];
  let cur = "";

  function activate(key) {
    if (!owner.has(key) || key === cur) return key === cur;
    cur = key;
    $$(".pv-view").forEach((v) => v.classList.toggle("is-active", v.dataset.pvView === key));
    $$(".pv-tab").forEach((t) => {
      const on = t.dataset.pv === key;
      t.classList.toggle("is-active", on);
      t.setAttribute("aria-selected", String(on));
    });

    /* The full hero belongs to the first view; the rest get the slim bar. */
    const sub = key !== keys[0];
    document.getElementById("hero")?.classList.toggle("is-hidden", sub);
    const slim = $("[data-pv-slim]");
    if (slim) slim.hidden = !sub;

    alignFeedbackLoop();   // was unmeasurable while the view was display:none
    alignFwCycle();
    return true;
  }

  /* Keep the sticky bar in view, but never scroll away from the hero. */
  function settle() {
    const bar = $(".pv-bar");
    if (bar && window.scrollY > bar.offsetTop) {
      window.scrollTo({ top: bar.offsetTop, behavior: "instant" });
    }
  }

  function open(id, { push = true } = {}) {
    const key = owner.get(id);
    if (!key) return false;
    activate(key);
    const isView = key === id;
    if (push) history.replaceState(null, "", isView && key === keys[0] ? location.pathname : `#${id}`);
    if (isView) settle();
    else requestAnimationFrame(() => document.getElementById(id)?.scrollIntoView({ block: "start" }));
    return true;
  }

  function init() {
    const views = $$(".pv-view");
    if (!views.length) return;
    views.forEach((v) => {
      const key = v.dataset.pvView;
      keys.push(key);
      owner.set(key, key);
      $$("section[id]", v).forEach((s) => owner.set(s.id, key));
    });

    $$(".pv-tab").forEach((t) => {
      t.setAttribute("role", "tab");
      t.addEventListener("click", () => open(t.dataset.pv));
    });

    document.addEventListener("click", (e) => {
      const a = e.target.closest('a[href^="#"]');
      if (!a) return;
      const id = a.getAttribute("href").slice(1);
      if (!owner.has(id)) return;
      e.preventDefault();
      open(id);
    });

    window.addEventListener("hashchange", () => open(location.hash.slice(1), { push: false }));

    cur = "";
    if (!open(location.hash.slice(1), { push: false })) activate(keys[0]);
  }

  return { init, open };
})();

MQ.init();
SIM.init();
LP.init();
initResults();
initNav();
initLandingCards();
initHubNav();
FW.init();
CS.init();
SV.init();
TG.init();
LB.init();
PV.init();
