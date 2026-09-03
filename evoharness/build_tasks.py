"""Rebuild static/tasks.json from the benchmark's task corpus.

    python build_tasks.py [path/to/mas_evovle_enviroment/data]

The corpus on disk is 438 MB of JSONL across 224 files, laid out as
`<dataset>/<eog/<domain>|ale>/v<stage>/<split>.jsonl` (domain directories are
symlinks into `eog/`, so paths are de-duplicated by realpath here).

Two things are dropped to make a shippable bundle:

* `enterprise_tri_hybrid`, a 7,737-record generated pool that is not one of the
  paper's domains. Excluding it makes the remaining counts land exactly on the
  paper's: 148 skills / 148 agents EOG eval tasks.
* the `train` (adaptation) split, since the gallery shows what is evaluated.

That leaves the 1,061 evaluation tasks. System prompts are the bulk of the text
and repeat almost verbatim across every task in a domain, so they intern down to
a handful of entries; the same goes for capability lists, verifier sets, staged
input files and required-step lists.

Field offsets in the emitted tuples are mirrored by `T` in app.js; changing the
order here means changing them there.
"""
import glob
import gzip
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SRC = Path("/export/xgen-finance/meta_agent/mas_evovle_enviroment/data")
OUT = HERE / "static" / "tasks.json"

SKIP_DOMAINS = {"enterprise_tri_hybrid"}
SPLIT = "test"

# Figure manifests, built separately because they need the ALE corpus and the
# running gym containers respectively (see tools/build_ale_figures.py and
# tools/shoot_eog_envs.py). Folded in here so the gallery needs one fetch.
#
# The environment manifest carries both halves of the mapping: `envs` describes
# each seeded environment's picture, and `taskEnvs` says which environments a
# given task starts from. An EOG task is keyed to its own seeded state rather
# than to its domain, so two tasks in the same gym generally get different
# pictures; a `hybrid` task lists one per gym it touches.
ALE_FIGURES = HERE / "static" / "images" / "ale" / "index.json"
ENV_FIGURES = HERE / "static" / "images" / "env" / "index.json"

# Frontend needs the picture and its caption; `shot` is the shooter's own
# dedup bookkeeping and would just pad the bundle.
ENV_FIELDS = ("file", "thumb", "w", "h", "gym", "label", "caption", "rows")

# Per dataset: the track name, and the fields holding its oracle / cumulative harness.
TRACKS = {
    "evovling_tools": ("tools", "oracle_tools", "cummulative_tools"),
    "evovling_skills": ("skills", "oracle_skills", "cummulative_oracle_skills"),
    "evovling_agents": ("agents", "oracle_agents", "cumulative_agents"),
}


class Pool:
    """Intern any hashable into a dense index."""

    def __init__(self):
        self.items, self._idx = [], {}

    def __call__(self, value):
        i = self._idx.get(value)
        if i is None:
            i = self._idx[value] = len(self.items)
            self.items.append(value)
        return i

    def opt(self, value):
        """-1 for absent or empty, so the frontend can test one sentinel."""
        return -1 if not value else self(value)


def jload(v):
    """Several fields are a JSON string in one dataset and a real list in another."""
    if isinstance(v, str):
        try:
            return json.loads(v) if v.strip() else []
        except json.JSONDecodeError:
            return []
    return v or []


def stage_of(v):
    return int(str(v).lstrip("vV") or 0)


def load_figures(path: Path) -> dict:
    """A figure manifest, or empty if it hasn't been built yet.

    The gallery degrades to text-only rather than failing, so the page can be
    rebuilt without the ALE corpus mounted or the gym containers running.
    """
    if not path.exists():
        print(f"note: no figures at {path.relative_to(HERE)}", file=sys.stderr)
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build(src: Path) -> dict:
    tracks, envs, domains = Pool(), Pool(), Pool()
    cats, subs, tsplits = Pool(), Pool(), Pool()
    names, lists = Pool(), Pool()
    sysp, prompts, titles, summaries = Pool(), Pool(), Pool(), Pool()
    verifiers, files = Pool(), Pool()

    # `names` holds capability names, software, gym servers and required-step
    # sentences alike; every list field indexes into it, so nothing repeats.
    def lst(seq):
        return lists(tuple(names(str(x)) for x in (seq or [])))

    def opt_lst(seq):
        return lists(tuple(names(str(x)) for x in seq)) if seq else -1

    def ver_set(raw):
        out = []
        for v in jload(raw):
            cfg = v.get("validation_config") or {}
            out.append((
                v.get("name") or "",
                v.get("description") or "",
                v.get("verifier_type") or "",
                cfg.get("query") or "",
                json.dumps(cfg.get("expected_value"), ensure_ascii=False)
                if "expected_value" in cfg else "",
                cfg.get("comparison_type") or "",
            ))
        return verifiers.opt(tuple(out))

    def file_set(raw):
        out = [(f.get("name") or "", f.get("format") or "",
                f.get("path") or "", f.get("description") or "")
               for f in jload(raw) if isinstance(f, dict)]
        return files.opt(tuple(out))

    # Domain directories are symlinks into eog/, so every file is reachable by two
    # paths; only the resolved one carries the real <eog>/<domain> layout.
    real_root = src.resolve()
    paths = sorted({os.path.realpath(p) for p in
                    glob.glob(str(src / "evovling_*/**/v*/*.jsonl"), recursive=True)})

    rows = []
    for path in paths:
        parts = Path(path).relative_to(real_root).parts
        dataset = parts[0]
        if dataset not in TRACKS or Path(path).stem != SPLIT:
            continue
        env = "ale" if parts[1] == "ale" else "eog"
        domain = parts[2] if parts[1] == "eog" else "ale"
        if domain in SKIP_DOMAINS:
            continue
        track, ora_f, cum_f = TRACKS[dataset]

        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                gym = [s.get("mcp_server_name") for s in jload(r.get("gym_servers_config"))
                       if isinstance(s, dict) and s.get("mcp_server_name")]
                rows.append([
                    tracks(track), envs(env), domains(domain),
                    cats.opt(r.get("category")), subs.opt(r.get("subdomain")),
                    tsplits.opt(r.get("task_split")),
                    stage_of(r.get("version")), r["task_id"],
                    titles.opt(r.get("title")), summaries.opt(r.get("summary")),
                    sysp.opt(r.get("system_prompt")),
                    prompts(r.get("user_prompt") or r.get("task_prompt") or ""),
                    lst(r.get(ora_f)), lst(r.get(cum_f)),
                    opt_lst(r.get("selected_tools")), opt_lst(r.get("software")),
                    ver_set(r.get("verifiers")), file_set(r.get("input_files")),
                    opt_lst(r.get("agent_must_do")),
                    opt_lst(gym),
                ])

    rows.sort(key=lambda t: (t[0], t[1], domains.items[t[2]], t[6], t[7]))

    # Only ship figures for tasks that survived the filters above.
    live_ale = {t[7] for t in rows if envs.items[t[1]] == "ale"}
    ale_figs = {k: v for k, v in load_figures(ALE_FIGURES).items() if k in live_ale}

    live_eog = {t[7] for t in rows if envs.items[t[1]] == "eog"}
    env_man = load_figures(ENV_FIGURES)
    task_envs = {k: v for k, v in (env_man.get("taskEnvs") or {}).items()
                 if k in live_eog}
    used = {e for v in task_envs.values() for e in v}
    env_figs = {k: {f: v[f] for f in ENV_FIELDS if f in v}
                for k, v in (env_man.get("envs") or {}).items() if k in used}

    return {
        "tracks": tracks.items, "envs": envs.items, "domains": domains.items,
        "categories": cats.items, "subdomains": subs.items, "taskSplits": tsplits.items,
        "names": names.items, "lists": [list(t) for t in lists.items],
        "sys": sysp.items, "prompts": prompts.items,
        "titles": titles.items, "summaries": summaries.items,
        "verifiers": [[list(v) for v in vs] for vs in verifiers.items],
        "files": [[list(f) for f in fs] for fs in files.items],
        "tasks": rows,
        "envFigures": env_figs,
        "taskEnvs": task_envs,
        "aleFigures": ale_figs,
    }


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    if not src.exists():
        print(f"not found: {src}", file=sys.stderr)
        return 1
    b = build(src)
    blob = json.dumps(b, ensure_ascii=False, separators=(",", ":"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(blob, encoding="utf-8")

    per = {}
    for t in b["tasks"]:
        per[(b["tracks"][t[0]], b["envs"][t[1]])] = per.get(
            (b["tracks"][t[0]], b["envs"][t[1]]), 0) + 1
    print(f"{len(b['tasks'])} tasks")
    for k in sorted(per):
        print(f"  {k[0]:7} {k[1]:4} {per[k]:5}")
    print(f"interned: {len(b['sys'])} system prompts, {len(b['prompts'])} prompts, "
          f"{len(b['names'])} names, {len(b['lists'])} lists, "
          f"{len(b['verifiers'])} verifier sets, {len(b['files'])} file sets")

    illustrated = sum(
        1 for t in b["tasks"]
        if (b["envs"][t[1]] == "eog" and t[7] in b["taskEnvs"])
        or (b["envs"][t[1]] == "ale" and t[7] in b["aleFigures"])
    )
    n_ale_fig = sum(len(v) for v in b["aleFigures"].values())
    pics = len({v["file"] for v in b["envFigures"].values()})
    print(f"figures: {len(b['envFigures'])} seeded environments over {len(b['taskEnvs'])} "
          f"EOG tasks ({pics} distinct pictures — environments that render the same "
          f"share one), {n_ale_fig} ALE stills/clips across {len(b['aleFigures'])} tasks "
          f"— {illustrated}/{len(b['tasks'])} task rows illustrated")
    print(f"{OUT} — {OUT.stat().st_size / 1e6:.2f} MB "
          f"({len(gzip.compress(blob.encode())) / 1e3:.0f} KB gzipped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
