"""Dump what each EnterpriseOps-Gym tool actually is, for the Task Gallery.

    /tmp/eogvenv/bin/python tools/dump_tool_docs.py [out.json]

A task detail lists the tools it was handed by name -- `find_account`,
`create_new_case`, and often seventy more in the pool alongside them. The names
are all a reader gets, and they are not self-explanatory: nothing distinguishes
`find_user` from `find_contact_by_portal_user`, or says what either one takes.

The corpus cannot answer that. Its rows carry bare name lists, because the
descriptions live where the agent reads them -- in the gyms, which answer
`tools/list` with a description and an argument schema per tool. So this asks
the gyms directly, the same way the harness would.

Keyed by gym, not by name: 37 names are exposed by more than one gym and every
one of them carries a different description. `list_users` on the HR gym filters
and paginates over employees; on Teams it returns Microsoft Graph user objects.
Serving one for the other would be worse than serving nothing, so a task
resolves its tools through the servers its own row declares.

Descriptions are kept whole. Argument and return fields are flattened to what a
reader needs -- name, type, whether it is required, and the schema's own gloss --
which is a third of the raw payload. Only tools some task mentions are kept.

Requires the `gym-*` containers to be up. Writes `static/tool_docs.json`.
"""
import asyncio
import importlib.util
import json
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = Path("/export/xgen-finance/meta_agent/mas-orchestra-demo/backend")
TASKS = HERE.parent / "static/tasks.json"
OUT = HERE.parent / "static/tool_docs.json"

# Corpus rows name the MCP server; these are the gyms behind them. Same mapping
# as tools/dump_eog_snapshots.py, and the page needs it to resolve a chip, so it
# ships in the payload rather than being hardcoded in two places.
SERVER_GYM = {
    "gym-calendar": "calendar",
    "gym-email-mcp": "email",
    "sn-hr-internal": "hr",
    "gym-itsm-mcp": "itsm",
    "gym-teams-mcp": "teams",
    "sn-csm-server": "csm",
    "gym-google-drive-mcp": "drive",
}


def _load(mod_name: str, rel: str):
    """Import a backend module by path under a synthetic package name."""
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
            _load("app.enterprise.mcp_client", "app/enterprise/mcp_client.py"))


GYM_CONFIG, MCP_CLIENT = _bootstrap()


def wanted() -> set[str]:
    """The names the page interns, so docs for tools no task mentions stay out."""
    return set(json.loads(TASKS.read_text())["names"])


def fields(schema: dict | None) -> list[list]:
    """Flatten one JSON schema to [name, type, required, gloss] rows."""
    schema = schema or {}
    required = set(schema.get("required") or [])
    out = []
    for name, spec in (schema.get("properties") or {}).items():
        spec = spec or {}
        kind = spec.get("type") or ""
        if isinstance(kind, list):                    # nullable columns arrive as ["string","null"]
            kind = "/".join(k for k in kind if k != "null") or ""
        if kind == "array":
            inner = (spec.get("items") or {}).get("type")
            if isinstance(inner, str):
                kind = f"{inner}[]"
        enum = spec.get("enum")
        gloss = (spec.get("description") or "").strip()
        if enum and len(json.dumps(enum)) < 120:
            one_of = ", ".join(str(e) for e in enum)
            gloss = f"{gloss} One of: {one_of}." if gloss else f"One of: {one_of}."
        out.append([name, kind, 1 if name in required else 0, gloss])
    return out


async def harvest(gym: str) -> list[dict]:
    client = MCP_CLIENT.MCPClient(GYM_CONFIG.get_gym(gym).url)
    try:
        return await client.list_tools()
    finally:
        await client.close()


async def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    keep = wanted()
    gyms: dict[str, dict] = {}
    skipped = 0
    for gym in sorted(set(SERVER_GYM.values())):
        try:
            tools = await harvest(gym)
        except Exception as exc:
            print(f"  {gym}: FAILED {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        doc = {}
        for tool in tools:
            name = tool.get("name")
            if not name:
                continue
            if name not in keep:
                skipped += 1
                continue
            entry = {"d": (tool.get("description") or "").strip()}
            args = fields(tool.get("inputSchema"))
            if args:
                entry["a"] = args
            # Return fields are named only. A reader wants to know a lookup hands
            # back an email and a role; the nested shape of each one is the gym's
            # business, and carrying it would double the file.
            rets = [f[0] for f in fields(tool.get("outputSchema"))]
            if rets:
                entry["o"] = rets
            doc[name] = entry
        gyms[gym] = doc
        print(f"  {gym:<9} {len(doc):>3} tools documented")

    payload = {"servers": SERVER_GYM, "gyms": gyms}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, separators=(",", ":")))
    total = sum(len(d) for d in gyms.values())
    shared = {}
    for gym, doc in gyms.items():
        for name in doc:
            shared.setdefault(name, []).append(gym)
    multi = sum(1 for v in shared.values() if len(v) > 1)
    print(f"\n{total} descriptors over {len(gyms)} gyms, {len(shared)} distinct names")
    print(f"{multi} name(s) exposed by more than one gym, kept per gym")
    print(f"{skipped} tool(s) no task mentions, left out")
    print(f"wrote {out_path} ({out_path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
