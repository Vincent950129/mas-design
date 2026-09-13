#!/usr/bin/env python3
"""Render the exact public TB2 construction blocks for the page and skill."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path


PUBLIC_SERVICE = "https://educator-marrow-cultural.ngrok-free.dev"
DELIMITER = "__EVOHARNESS_TB2_FILE__"
TB2_REPOSITORY = "https://github.com/harbor-framework/terminal-bench-2.git"
TB2_COMMIT = "2fd12b88aafdd04a52c298e3940bcb189f9766d6"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def writer_body(relative: str, body: str, *, append: bool = False) -> str:
    if not body.endswith("\n"):
        raise RuntimeError(f"public source chunk must end with a newline: {relative}")
    if f"\n{DELIMITER}\n" in f"\n{body}\n":
        raise RuntimeError(f"heredoc delimiter occurs in {relative}")
    redirect = ">>" if append else ">"
    return (
        f'mkdir -p "$EVOLVE_TB2_WORKDIR/{Path(relative).parent.as_posix()}"\n'
        f'cat {redirect} "$EVOLVE_TB2_WORKDIR/{relative}" <<\'{DELIMITER}\'\n'
        f"{body}{DELIMITER}\n"
    )


def writer(relative: str, source: Path, *, append: bool = False) -> str:
    return writer_body(relative, source.read_text(encoding="utf-8"), append=append)


def builder_chunks(source: Path) -> tuple[str, str, str]:
    """Split the monolithic implementation at its paper-aligned pipeline boundaries."""
    body = source.read_text(encoding="utf-8")
    step_2 = body.index("def _stage_ok(")
    steps_3_4 = body.index("def _input_files(")
    return body[:step_2], body[step_2:steps_3_4], body[steps_3_4:]


def function_source(source: Path, *names: str) -> str:
    """Lift exact functions for the explanatory track tabs without hand-copy drift."""
    body = source.read_text(encoding="utf-8")
    lines = body.splitlines(keepends=True)
    found = {node.name: node for node in ast.parse(body).body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    missing = [name for name in names if name not in found]
    if missing:
        raise RuntimeError(f"builder functions missing for guide: {missing}")
    chunks = []
    for name in names:
        node = found[name]
        start = min([node.lineno, *(d.lineno for d in node.decorator_list)]) - 1
        chunks.append("".join(lines[start:node.end_lineno]).rstrip())
    return "\n\n".join(chunks) + "\n"


def source_slice(source: Path, start: str, end: str) -> str:
    """Lift a small exact call site whose logic lives inside build_into()."""
    body = source.read_text(encoding="utf-8")
    left = body.index(start)
    right = body.index(end, left)
    return body[left:right].strip() + "\n"


def guide_blocks(source_root: Path) -> dict[str, dict[str, str]]:
    """Axis-specific views of code already installed by the executable shared blocks."""
    builder = source_root / "data_dry_run/tb_builder/builder.py"
    return {
        "skills-annotate": {
            "label": "python · exact prompt-mining function in builder.py",
            "code": function_source(builder, "annotate_skills"),
        },
        "skills-release": {
            "label": "python · exact skill sequencer call in builder.py",
            "code": function_source(builder, "_build_skill_curriculum"),
        },
        "skills-write": {
            "label": "python · exact skill rows and held-out library writer",
            "code": function_source(builder, "_skills_rows", "_skill_md", "_write_skill_library"),
        },
        "agents-annotate": {
            "label": "python · exact software-owner partition in builder.py",
            "code": function_source(builder, "_owner_maps"),
        },
        "agents-release": {
            "label": "python · exact independent agent-curriculum call",
            "code": source_slice(builder, "    agent_tasks = {", "    active_owner_tools = {"),
        },
        "agents-write": {
            "label": "python · exact agent rows and specialist materializer",
            "code": function_source(builder, "_agents_rows", "_materialize_agents"),
        },
    }


def setup_block() -> str:
    return f'''export EVOLVE_TB2_SERVICE="${{EVOLVE_TB2_SERVICE:-{PUBLIC_SERVICE}}}"
export EVOLVE_TB2_WORKDIR="${{EVOLVE_TB2_WORKDIR:-$PWD/evoharnessbench-tb2}}"

if [ -e "$EVOLVE_TB2_WORKDIR" ]; then
  echo "Refusing to overwrite existing path: $EVOLVE_TB2_WORKDIR" >&2
  exit 1
fi
source_dir="$EVOLVE_TB2_WORKDIR/data_dry_run/tb_builder/cache/terminal-bench-2"
mkdir -p "$(dirname "$source_dir")"
git clone --filter=blob:none --no-checkout {TB2_REPOSITORY} "$source_dir"
git -C "$source_dir" fetch --force origin {TB2_COMMIT}
git -C "$source_dir" checkout --detach {TB2_COMMIT}
test "$(git -C "$source_dir" rev-parse HEAD)" = "{TB2_COMMIT}"

printf 'Downloaded Terminal-Bench 2 seed data at %.8s into %s\n' \
  "{TB2_COMMIT}" "$source_dir"'''


def catalog_download(public_name: str, expected: str, local_name: str) -> str:
    return f'''import hashlib, json, os, pathlib, urllib.request

base = os.environ.get("EVOLVE_TB2_SERVICE", "{PUBLIC_SERVICE}").rstrip("/")
root = pathlib.Path(os.environ["EVOLVE_TB2_WORKDIR"])
eval_key = os.environ.get("EVAL_SERVICE_API_KEY", "").strip()
if not eval_key:
    raise RuntimeError("EVAL_SERVICE_API_KEY is required to download the closed catalog")
public_name = {json.dumps(public_name)}
expected = {json.dumps(expected)}
url = base + "/resources/evolve-benchmark/references/tb2/v1/" + public_name
request = urllib.request.Request(url, headers={{
    "Authorization": f"Bearer {{eval_key}}",
    "ngrok-skip-browser-warning": "true",
}})
with urllib.request.urlopen(request) as response:
    content = response.read()
actual = hashlib.sha256(content).hexdigest()
if actual != expected:
    raise RuntimeError(f"checksum mismatch for {{public_name}}: {{actual}}")
target = root / "data_dry_run" / "tb_builder" / {json.dumps(local_name)}
target.parent.mkdir(parents=True, exist_ok=True)
temporary = target.with_name(target.name + ".download")
temporary.write_bytes(content)
temporary.replace(target)
'''


def tools_check(software_sha: str) -> str:
    return "python - <<'PY'\n" + catalog_download(
        "software-catalog.json", software_sha, "catalog.json"
    ) + '''
catalog = json.loads((root / "data_dry_run/tb_builder/catalog.json").read_text())
required = {"name", "aliases", "binaries", "imports", "packages", "owner", "baseline"}
names = [item["name"] for item in catalog]
if len(names) != len(set(names)) or any(required - set(item) for item in catalog):
    raise RuntimeError("invalid closed software catalog")
aliases = {}
for item in catalog:
    for value in [item["name"], *item["aliases"], *item["binaries"],
                  *item["imports"], *item["packages"]]:
        key = value.casefold()
        if key in aliases and aliases[key] != item["name"]:
            raise RuntimeError(f"ambiguous software alias: {value}")
        aliases[key] = item["name"]
print(f"Tools catalog: {len(catalog)} canonical entries; aliases are closed and unambiguous")
PY'''


def skills_check(skill_sha: str) -> str:
    return "python - <<'PY'\n" + catalog_download(
        "skill-catalog.json", skill_sha, "skills.json"
    ) + '''
skills = json.loads((root / "data_dry_run/tb_builder/skills.json").read_text())
required = {"name", "title", "tier", "description", "categories", "terms", "tools",
            "procedure", "notes", "see_also"}
names = [item["name"] for item in skills]
if len(skills) != 26 or len(names) != len(set(names)):
    raise RuntimeError("the pinned skill catalog must contain 26 unique skills")
if any(required - set(item) for item in skills):
    raise RuntimeError("invalid skill-catalog schema")
print("Skills catalog: 26 deterministic procedural atoms ready for prompt mining")
PY'''


def agents_check() -> str:
    return '''python - <<'PY'
import collections, json, os, pathlib

root = pathlib.Path(os.environ["EVOLVE_TB2_WORKDIR"])
catalog = json.loads((root / "data_dry_run/tb_builder/catalog.json").read_text())
owners = collections.defaultdict(list)
for item in catalog:
    owner = item.get("owner", "").strip()
    if not owner:
        raise RuntimeError(f"missing owner for {item['name']}")
    owners[owner].append(item["name"])
owned = [tool for tools in owners.values() for tool in tools]
if len(owned) != len(set(owned)) or len(owned) != len(catalog):
    raise RuntimeError("software ownership is not an exact partition")
print(f"Agents catalog: {len(owners)} owner families form an exact software partition")
PY'''


def blocks(source_root: Path) -> list[tuple[str, str, str]]:
    catalog = source_root / "data_dry_run/tb_builder/catalog.json"
    skills = source_root / "data_dry_run/tb_builder/skills.json"
    builder = source_root / "data_dry_run/tb_builder/builder.py"
    annotation, release, materialize = builder_chunks(builder)
    return [
        ("setup", "bash · download Terminal-Bench 2 seed data", setup_block()),
        ("tools", "bash · download and validate the software catalog",
         tools_check(sha256(catalog))),
        ("annotate", "bash · shared task discovery and capability annotation",
         writer_body("data_dry_run/tb_builder/builder.py", annotation)),
        ("release", "bash · shared frequency-ranked release scheduler",
         writer_body("data_dry_run/tb_builder/builder.py", release, append=True) + "\n" +
         writer("evolve_tools/builder/frequency_config.py",
                source_root / "evolve_tools/builder/frequency_config.py")),
        ("package", "bash · shared accumulation, materialization, and validation",
         writer_body("data_dry_run/tb_builder/builder.py", materialize, append=True)),
        ("skills", "bash · download and validate the skill catalog",
         skills_check(sha256(skills)) + "\n" +
         writer("evovle_skills/builder/sequencer.py",
                source_root / "evovle_skills/builder/sequencer.py") + "\n" +
         writer("evovle_skills/builder/shared/paths.py",
                source_root / "evovle_skills/builder/shared/paths.py")),
        ("agents", "bash · validate the exact tool-owner partition", agents_check()),
        ("terminal", "bash · exact pins, CLI, Harbor adapter and full build",
         writer("data_dry_run/tb_builder/config.py",
                source_root / "data_dry_run/tb_builder/config.py") + "\n" +
         writer("data_dry_run/tb_builder/remote_docker.py",
                source_root / "data_dry_run/tb_builder/remote_docker.py") + "\n" +
         writer("data_dry_run/tb_builder/__init__.py",
                source_root / "data_dry_run/tb_builder/__init__.py") + "\n" +
         writer("data_dry_run/tb_builder/__main__.py",
                source_root / "data_dry_run/tb_builder/__main__.py") +
         '''\ncd "$EVOLVE_TB2_WORKDIR/data_dry_run"
python -m tb_builder all'''),
    ]


def render_javascript(items: list[tuple[str, str, str]],
                      guides: dict[str, dict[str, str]]) -> str:
    payload = {key: {"label": label, "code": code} for key, label, code in items}
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    guide_data = json.dumps(guides, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f'''/* Generated by tools/generate_tb2_public_blocks.py. */
window.EVOHARNESS_TB2_BLOCKS = {data};
window.EVOHARNESS_TB2_GUIDES = {guide_data};
(function renderExactTB2Blocks() {{
  document.querySelectorAll("[data-tb2-exact]").forEach((host) => {{
    const item = window.EVOHARNESS_TB2_BLOCKS[host.dataset.tb2Exact];
    if (!item) return;
    const wrap = document.createElement("div");
    wrap.className = "sv-codewrap tb2-exact-wrap";
    const label = document.createElement("span");
    label.className = "sv-lang";
    label.textContent = item.label;
    const copy = document.createElement("button");
    copy.className = "sv-copy";
    copy.type = "button";
    copy.textContent = "Copy";
    const pre = document.createElement("pre");
    pre.className = "sv-code tb2-exact-code";
    pre.dataset.lang = "bash";
    pre.dataset.tb2Executable = host.dataset.tb2Exact;
    const code = document.createElement("code");
    code.textContent = item.code;
    pre.appendChild(code);
    wrap.append(label, copy, pre);
    host.replaceChildren(wrap);
  }});
}})();

(function renderTB2GuideBlocks() {{
  document.querySelectorAll("[data-tb2-guide]").forEach((host) => {{
    const item = window.EVOHARNESS_TB2_GUIDES[host.dataset.tb2Guide];
    if (!item) return;
    const wrap = document.createElement("div");
    wrap.className = "sv-codewrap tb2-guide-wrap";
    const label = document.createElement("span");
    label.className = "sv-lang";
    label.textContent = item.label;
    const copy = document.createElement("button");
    copy.className = "sv-copy";
    copy.type = "button";
    copy.textContent = "Copy";
    const pre = document.createElement("pre");
    pre.className = "sv-code tb2-guide-code";
    pre.dataset.lang = "python";
    pre.dataset.guideSnippet = host.dataset.tb2Guide;
    const code = document.createElement("code");
    code.textContent = item.code;
    pre.appendChild(code);
    wrap.append(label, copy, pre);
    host.replaceChildren(wrap);
  }});
}})();
'''


def render_reference(items: list[tuple[str, str, str]]) -> str:
    intro = '''# Terminal-Bench 2 construction path

Use these blocks in order. They are generated from the same public source as the
rendered EvoHarnessBench construction page. Do not substitute another annotation,
scheduler, schema, or catalog.

- Terminal-Bench 2: `2fd12b88aafdd04a52c298e3940bcb189f9766d6`
- Harbor `0.23.0`: `d8cfe6b6fd463fc1f2a84abf8f1406f46e70c621`
- Python `3.12.12`, uv `0.12.13`, bashlex `0.18`, seed `42`
- Expected: 89 discovered; tools 86/50, skills 89/26, agents 86/17; five stages
- Expected tree hash: `7dd14ca35796ad7a91fdc08a825d53d298aed527cd67497317c78064fbef50a0`

The first block downloads the pinned Terminal-Bench 2 seed snapshot. The tools and
skills blocks later download the two versioned closed catalogs. Every executable
construction function is printed below; no Python builder is downloaded or imported.
The destination must be fresh, and promotion occurs only after two byte-identical builds
and five Harbor oracle rewards of `1.0`.
'''
    labels = {
        "setup": "Download seed data · Terminal-Bench 2",
        "tools": "Tools · Step 1 catalog",
        "annotate": "Tools · Step 1 shared annotation implementation",
        "release": "Tools · Step 2 shared release implementation",
        "package": "Tools · Steps 3 and 4 shared accumulation and writer",
        "skills": "Skills · Step 1 mine the prompts",
        "agents": "Agents · Step 1 partition the tools",
        "terminal": "Expected output · build, validate, and smoke-test",
    }
    sections = [intro.rstrip()]
    for key, _, code in items:
        sections.extend((f"## {labels[key]}", "```bash\n" + code.rstrip() + "\n```"))
    return "\n\n".join(sections) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--javascript", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    items = blocks(source_root)
    guides = guide_blocks(source_root)
    args.javascript.write_text(render_javascript(items, guides), encoding="utf-8")
    args.reference.write_text(render_reference(items), encoding="utf-8")
    print(f"rendered {len(items)} exact blocks and {len(guides)} track guides")


if __name__ == "__main__":
    main()
