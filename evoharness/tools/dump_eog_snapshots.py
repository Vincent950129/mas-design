"""Dump one sandbox snapshot per distinct EnterpriseOps-Gym environment.

    /tmp/eogvenv/bin/python tools/dump_eog_snapshots.py [out_dir]

An EOG task does not act on "the calendar gym" in the abstract: it acts on a
specific seeded database, and two tasks in the same domain usually start from
different rows. So the unit here is the *environment* — one (gym, seed SQL)
pair — not the domain. Across the 503 evaluation tasks the corpus names only 72
of them, so the figures stay cheap while still being per-task truthful.

Seeds and server names come straight from each task's ``gym_servers_config`` in
the corpus, which is the same thing the harness feeds the gym at run time. That
makes this independent of the demo's own task loader, whose ids cover only part
of the shipped corpus.

For each environment: seed a throwaway database in the gym container, read the
curated tables back, drop the database. Raw per-seed payloads land in ``raw/``;
they are then keyed by the *contents* of the visible tables and deduplicated,
because a fair number of seeds differ only outside the snapshot's window and
would otherwise ship as byte-identical pictures. That takes 72 seeds down to
about 51 figures.

Writes ``<figure>.json`` (the payload the demo frontend's ``SandboxPanel``
consumes) plus an ``index.json`` mapping every task id to the figures it uses.
Feeds ``tools/shoot_eog_envs.py``.

Requires the ``gym-*`` containers to be up; ``docker inspect`` supplies their
addresses. Resumable — a seed already present under ``raw/`` is skipped unless
``--fresh`` is passed.
"""
import asyncio
import glob
import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path

BACKEND = Path("/export/xgen-finance/meta_agent/mas-orchestra-demo/backend")
GYM_ROOT = Path("/export/xgen-finance/meta_agent/mas_evovle_enviroment/reference/EnterpriseOps-Gym")
CORPUS = Path("/export/xgen-finance/meta_agent/mas_evovle_enviroment/data")

# Corpus rows name the MCP server; the gym behind it owns the seeded database.
SERVER_GYM = {
    "gym-calendar": "calendar",
    "gym-email-mcp": "email",
    "sn-hr-internal": "hr",
    "gym-itsm-mcp": "itsm",
    "gym-teams-mcp": "teams",
    "sn-csm-server": "csm",
    "gym-google-drive-mcp": "drive",
}
# `enterprise_tri_hybrid` is excluded from the shipped bundle, so skip it here too.
SKIP_DOMAINS = {"enterprise_tri_hybrid"}
SPLIT = "test"


def _load(mod_name: str, rel: str):
    """Import a backend module by path under a synthetic package name.

    The modules use intra-package relative imports, so they are registered as
    ``app.enterprise.*`` submodules of stub parent packages rather than loaded
    standalone.
    """
    spec = importlib.util.spec_from_file_location(mod_name, BACKEND / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _bootstrap():
    for pkg, path in (("app", BACKEND / "app"),
                      ("app.enterprise", BACKEND / "app" / "enterprise")):
        if pkg not in sys.modules:
            m = types.ModuleType(pkg)
            m.__path__ = [str(path)]
            sys.modules[pkg] = m
    return (_load("app.enterprise.gym_config", "app/enterprise/gym_config.py"),
            _load("app.enterprise.mcp_client", "app/enterprise/mcp_client.py"),
            _load("app.enterprise.sandbox", "app/enterprise/sandbox.py"))


GYM_CONFIG, MCP_CLIENT, SANDBOX = _bootstrap()


def seed_id(gym: str, seed_rel: str) -> str:
    """Stable, filesystem-safe name for one (gym, seed SQL) pair."""
    digest = hashlib.sha1((GYM_ROOT / seed_rel).read_bytes()).hexdigest()[:10]
    return f"{gym}-{digest}"


def figure_id(gym: str, payload: dict) -> str:
    """Name one environment by what it actually looks like.

    Two seeds can differ only in rows the snapshot never shows, in which case
    they are the same picture and deserve one file rather than two identical
    ones. Hashing the visible tables is what makes that collapse safe.
    """
    blob = json.dumps(payload.get("tables"), sort_keys=True, separators=(",", ":"))
    return f"{gym}-{hashlib.sha1(blob.encode()).hexdigest()[:10]}"


def scan_corpus() -> tuple[dict[str, dict], dict[str, list[str]]]:
    """Walk the corpus once: which seeds exist, and who uses them.

    Returns ``(seeds, task_seeds)`` where ``seeds[seed_id]`` carries the gym and
    seed path to replay, and ``task_seeds[task_id]`` lists that task's seeds in
    the order its servers are declared.
    """
    seeds: dict[str, dict] = {}
    task_seeds: dict[str, list[str]] = {}
    paths = sorted({str(Path(p).resolve()) for p in
                    glob.glob(str(CORPUS / "evovling_*/eog/*/v*/*.jsonl"), recursive=True)})
    for path in paths:
        if Path(path).stem != SPLIT:
            continue
        domain = path.split("/eog/")[1].split("/")[0]
        if domain in SKIP_DOMAINS:
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                row = json.loads(line)
                raw = row.get("gym_servers_config")
                servers = json.loads(raw) if isinstance(raw, str) else (raw or [])
                ids = []
                for s in servers:
                    gym = SERVER_GYM.get(s.get("mcp_server_name"))
                    seed = s.get("seed_database_file")
                    if not gym or not seed or not (GYM_ROOT / seed).exists():
                        continue
                    sid = seed_id(gym, seed)
                    seeds.setdefault(sid, {"gym": gym, "seed": seed})
                    if sid not in ids:
                        ids.append(sid)
                if ids:
                    # A task id recurs across tracks and stages with the same
                    # servers; first writer wins.
                    task_seeds.setdefault(row["task_id"], ids)
    return seeds, task_seeds


async def dump_seed(sid: str, spec: dict, raw_dir: Path) -> bool:
    gym_name = spec["gym"]
    try:
        gym = GYM_CONFIG.get_gym(gym_name)
    except KeyError:
        print(f"  {sid}: no such gym {gym_name}", file=sys.stderr)
        return False
    sql = (GYM_ROOT / spec["seed"]).read_text(encoding="utf-8", errors="replace")
    mcp = MCP_CLIENT.MCPClient(gym.url)
    try:
        await mcp.seed_database(sql, description=f"figure seed={sid}")
        snap = await SANDBOX.take_snapshot(mcp, gym_name)
        payload = {**snap.to_payload(), "phase": "preview"}
        tables = payload.get("tables") or []
        rows = sum(len(t.get("rows") or []) for t in tables)
        (raw_dir / f"{sid}.json").write_text(json.dumps(payload, separators=(",", ":")))
        print(f"  {sid}: {rows} rows across {len(tables)} tables")
        return True
    except Exception as e:
        print(f"  {sid}: FAILED {type(e).__name__}: {e}", file=sys.stderr)
        return False
    finally:
        try:
            await mcp.delete_database()
        finally:
            await mcp.close()


def consolidate(seeds: dict, task_seeds: dict, raw_dir: Path, out_dir: Path) -> dict:
    """Collapse raw per-seed dumps onto distinct pictures and write the index."""
    fig_of: dict[str, str] = {}          # seed id -> figure id
    figures: dict[str, dict] = {}
    for sid, spec in sorted(seeds.items()):
        raw = raw_dir / f"{sid}.json"
        if not raw.exists():
            continue
        payload = json.loads(raw.read_text())
        fid = figure_id(spec["gym"], payload)
        fig_of[sid] = fid
        if fid not in figures:
            tables = payload.get("tables") or []
            # Kept as a list so the demo's figure harness can load it with the
            # same `pick()` path it uses for composite fixtures.
            (out_dir / f"{fid}.json").write_text(
                json.dumps([payload], separators=(",", ":")))
            figures[fid] = {
                "gym": spec["gym"],
                "rows": sum(len(t.get("rows") or []) for t in tables),
                "tables": len(tables),
                "seeds": [],
            }
        figures[fid]["seeds"].append(spec["seed"])

    task_figs = {}
    partial = 0
    for tid, sids in task_seeds.items():
        fids = []
        for sid in sids:
            fid = fig_of.get(sid)
            # Two seeds of one task can land on the same picture; that is a real
            # collapse, not a gap, so dedupe without counting it as missing.
            if fid and fid not in fids:
                fids.append(fid)
        if not fids:
            continue
        if any(sid not in fig_of for sid in sids):
            partial += 1
        task_figs[tid] = fids
    if partial:
        print(f"note: {partial} tasks resolved only some of their environments",
              file=sys.stderr)

    index = {"envs": figures, "taskEnvs": task_figs}
    (out_dir / "index.json").write_text(json.dumps(index, indent=2, sort_keys=True))
    return index


async def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    fresh = "--fresh" in sys.argv
    out_dir = Path(args[0]) if args else Path(__file__).resolve().parent / "eog_snapshots"
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    seeds, task_seeds = scan_corpus()
    print(f"{len(task_seeds)} tasks over {len(seeds)} distinct seeds")

    todo = [(s, spec) for s, spec in sorted(seeds.items())
            if fresh or not (raw_dir / f"{s}.json").exists()]
    if len(todo) < len(seeds):
        print(f"resuming: {len(seeds) - len(todo)} seeds already dumped")

    failed = 0
    for sid, spec in todo:
        if not await dump_seed(sid, spec, raw_dir):
            failed += 1

    have = sum(1 for s in seeds if (raw_dir / f"{s}.json").exists())
    for stale in out_dir.glob("*.json"):
        stale.unlink()
    index = consolidate(seeds, task_seeds, raw_dir, out_dir)

    print(f"\n{have}/{len(seeds)} seeds dumped ({failed} failed) -> "
          f"{len(index['envs'])} distinct environments")
    print(f"{len(index['taskEnvs'])}/{len(task_seeds)} tasks have an environment "
          f"-> {out_dir}")
    return 0 if have == len(seeds) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
