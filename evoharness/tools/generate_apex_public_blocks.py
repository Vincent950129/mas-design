#!/usr/bin/env python3
"""Render the exact public APEX-Agents construction blocks for the page and skill."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
from pathlib import Path


PUBLIC_SERVICE = "https://educator-marrow-cultural.ngrok-free.dev"
DELIMITER = "__EVOHARNESS_APEX_FILE__"
APEX_REPOSITORY = "mercor/apex-agents"
APEX_URL = "https://huggingface.co/datasets/mercor/apex-agents"
APEX_COMMIT = "92c86856cf1b11f9833a8a076b3a45a63afa3929"
ARCHIPELAGO_REPOSITORY = "https://github.com/Mercor-Intelligence/archipelago.git"
ARCHIPELAGO_COMMIT = "bcacc2d1e99aa917bbe7f6f663c1551dc6ec7400"
HUGGINGFACE_HUB_VERSION = "0.26.2"
TOMLI_VERSION = "2.0.1"
EXPECTED_HASH = "8ef9f9aaf2ea5f53447cb90e5a5716a7a0063d9450c5c488e3ac4f13714e088c"
SOURCE_FILES = {
    "metadata.json": "24584749c6307602944739262a2f3ddd59e8e0ecc9f151dc3459adf84ab934ea",
    "world_descriptions.json": "3836f308d122b7204a463ce43d23ec63fb27460f36f6bd5ac32d724183a3fdd8",
    "tasks_and_rubrics.json": "94a85655bb983bb8bfff693182026f05f1df41ff17b2cd4589dd42a071531cb6",
    "eval.yaml": "231993cb91ab18596fb6c24c9fbb33fba2975dcea605de5696cf4c4245ec8151",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def writer_body(relative: str, body: str, *, append: bool = False) -> str:
    if not body.endswith("\n"):
        raise RuntimeError(f"public source chunk must end with a newline: {relative}")
    if f"\n{DELIMITER}\n" in f"\n{body}\n":
        raise RuntimeError(f"heredoc delimiter occurs in {relative}")
    redirect = ">>" if append else ">"
    return (
        f'mkdir -p "$EVOLVE_APEX_WORKDIR/{Path(relative).parent.as_posix()}"\n'
        f'cat {redirect} "$EVOLVE_APEX_WORKDIR/{relative}" <<\'{DELIMITER}\'\n'
        f"{body}{DELIMITER}\n"
    )


def writer(relative: str, source: Path, *, append: bool = False) -> str:
    return writer_body(relative, source.read_text(encoding="utf-8"), append=append)


def builder_chunks(source: Path) -> tuple[str, str, str]:
    """Split the implementation at the paper's annotation/release/write boundaries."""
    body = source.read_text(encoding="utf-8")
    step_2 = body.index("def _axis_constraints(")
    steps_3_4 = body.index("def _common(")
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
    builder = source_root / "data_dry_run/apex_builder/builder.py"
    return {
        "skills-annotate": {
            "label": "python · exact prompt-matching function in builder.py",
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
            "label": "python · exact operation-owner partition in builder.py",
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
    source_files = json.dumps(SOURCE_FILES, sort_keys=True)
    return f'''export EVOLVE_APEX_SERVICE="${{EVOLVE_APEX_SERVICE:-{PUBLIC_SERVICE}}}"
export EVOLVE_APEX_WORKDIR="${{EVOLVE_APEX_WORKDIR:-$PWD/evoharnessbench-apex-agents}}"

if [ -e "$EVOLVE_APEX_WORKDIR" ]; then
  echo "Refusing to overwrite existing path: $EVOLVE_APEX_WORKDIR" >&2
  exit 1
fi
mkdir -p "$EVOLVE_APEX_WORKDIR/data_dry_run/apex_builder/cache/seed"
python -m venv "$EVOLVE_APEX_WORKDIR/.venv"
export EVOLVE_APEX_PYTHON="$EVOLVE_APEX_WORKDIR/.venv/bin/python"
"$EVOLVE_APEX_PYTHON" -m pip install --disable-pip-version-check \
  "huggingface-hub=={HUGGINGFACE_HUB_VERSION}" "tomli=={TOMLI_VERSION}"

if [ -z "${{HF_TOKEN:-}}" ] && [ -z "${{HUGGING_FACE_HUB_TOKEN:-}}" ]; then
  read -rsp "Hugging Face token (after accepting APEX-Agents access): " HF_TOKEN
  echo
  export HF_TOKEN
fi

"$EVOLVE_APEX_PYTHON" - <<'PY'
import hashlib, json, os, pathlib
from huggingface_hub import HfApi, hf_hub_download

repo_id = {json.dumps(APEX_REPOSITORY)}
revision = {json.dumps(APEX_COMMIT)}
files = {source_files}
root = pathlib.Path(os.environ["EVOLVE_APEX_WORKDIR"])
seed = root / "data_dry_run/apex_builder/cache/seed"
token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
if not token:
    raise RuntimeError("HF_TOKEN is required after accepting APEX-Agents access")
for name, expected in sorted(files.items()):
    path = pathlib.Path(hf_hub_download(
        repo_id=repo_id, repo_type="dataset", revision=revision,
        filename=name, local_dir=str(seed), token=token,
    ))
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError(f"seed checksum mismatch for {{name}}: {{actual}}")
info = HfApi(token=token).dataset_info(repo_id, revision=revision, files_metadata=True)
if info.sha != revision:
    raise RuntimeError(f"APEX source pin mismatch: {{info.sha}}")
manifest = {{
    "files": sorted(
        ({{"path": item.rfilename, "size": item.size}} for item in info.siblings),
        key=lambda item: item["path"],
    ),
    "repository_url": {json.dumps(APEX_URL)},
    "source_commit": revision,
}}
(seed / "repo_files.json").write_text(
    json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\\n",
    encoding="utf-8",
)
print(f"Downloaded {{len(files)}} pinned APEX-Agents metadata files")
PY

archipelago="$EVOLVE_APEX_WORKDIR/data_dry_run/apex_builder/cache/archipelago"
git clone --filter=blob:none --no-checkout {ARCHIPELAGO_REPOSITORY} "$archipelago"
git -C "$archipelago" fetch --force origin {ARCHIPELAGO_COMMIT}
git -C "$archipelago" checkout --detach {ARCHIPELAGO_COMMIT}
test "$(git -C "$archipelago" rev-parse HEAD)" = "{ARCHIPELAGO_COMMIT}"
printf 'Downloaded APEX-Agents seed metadata at %.8s; large world archives were not downloaded\\n' \
  "{APEX_COMMIT}"'''


def catalog_download(public_name: str, expected: str, local_name: str) -> str:
    return f'''import hashlib, json, os, pathlib, urllib.request

base = os.environ.get("EVOLVE_APEX_SERVICE", "{PUBLIC_SERVICE}").rstrip("/")
root = pathlib.Path(os.environ["EVOLVE_APEX_WORKDIR"])
eval_key = os.environ.get("EVAL_SERVICE_API_KEY", "").strip()
if not eval_key:
    raise RuntimeError("EVAL_SERVICE_API_KEY is required to download the closed catalog")
public_name = {json.dumps(public_name)}
expected = {json.dumps(expected)}
url = base + "/resources/evolve-benchmark/references/apex/v1/" + public_name
request = urllib.request.Request(url, headers={{
    "Authorization": f"Bearer {{eval_key}}",
    "ngrok-skip-browser-warning": "true",
}})
with urllib.request.urlopen(request) as response:
    content = response.read()
actual = hashlib.sha256(content).hexdigest()
if actual != expected:
    raise RuntimeError(f"checksum mismatch for {{public_name}}: {{actual}}")
target = root / "data_dry_run" / "apex_builder" / {json.dumps(local_name)}
target.parent.mkdir(parents=True, exist_ok=True)
temporary = target.with_name(target.name + ".download")
temporary.write_bytes(content)
temporary.replace(target)
'''


def tools_check(tool_sha: str) -> str:
    return '"$EVOLVE_APEX_PYTHON" - <<\'PY\'\n' + catalog_download(
        "tool-catalog.json", tool_sha, "catalog.json"
    ) + '''
catalog = json.loads((root / "data_dry_run/apex_builder/catalog.json").read_text())
required = {"name", "owner", "description", "source_path"}
names = [item["name"] for item in catalog]
if len(catalog) != 33 or len(names) != len(set(names)):
    raise RuntimeError("the pinned operation catalog must contain 33 unique operations")
if any(required - set(item) for item in catalog):
    raise RuntimeError("invalid operation-catalog schema")
if any(not any(item.get(field) for field in ("patterns", "expected_outputs", "input_extensions"))
       for item in catalog):
    raise RuntimeError("every operation needs at least one deterministic evidence rule")
if any(not item["name"].startswith(item["owner"] + ".") for item in catalog):
    raise RuntimeError("every operation must belong to its namespace owner")
print("Tools catalog: 33 exact Archipelago MCP operations with one owner each")
PY'''


def skills_check(skill_sha: str, source_root: Path) -> str:
    return '"$EVOLVE_APEX_PYTHON" - <<\'PY\'\n' + catalog_download(
        "skill-catalog.json", skill_sha, "skills.json"
    ) + '''
skills = json.loads((root / "data_dry_run/apex_builder/skills.json").read_text())
required = {"name", "title", "description", "tier", "domains", "patterns", "tools",
            "expected_outputs", "procedure", "notes", "see_also"}
names = [item["name"] for item in skills]
if len(skills) != 20 or len(names) != len(set(names)):
    raise RuntimeError("the pinned skill catalog must contain 20 unique procedural atoms")
if any(required - set(item) for item in skills):
    raise RuntimeError("invalid skill-catalog schema")
print("Skills catalog: 20 fixed procedural atoms ready for deterministic matching")
PY\n''' + writer(
        "evovle_skills/builder/sequencer.py",
        source_root / "evovle_skills/builder/sequencer.py",
    ) + "\n" + writer(
        "evovle_skills/builder/shared/paths.py",
        source_root / "evovle_skills/builder/shared/paths.py",
    )


def agents_check() -> str:
    return '''"$EVOLVE_APEX_PYTHON" - <<'PY'
import collections, json, os, pathlib

root = pathlib.Path(os.environ["EVOLVE_APEX_WORKDIR"])
catalog = json.loads((root / "data_dry_run/apex_builder/catalog.json").read_text())
owners = collections.defaultdict(list)
for item in catalog:
    owner = item.get("owner", "").strip()
    if not owner or not item["name"].startswith(owner + "."):
        raise RuntimeError(f"invalid owner for {item['name']}")
    owners[owner].append(item["name"])
owned = [tool for tools in owners.values() for tool in tools]
if len(owned) != len(set(owned)) or len(owned) != len(catalog):
    raise RuntimeError("operation ownership is not an exact partition")
print(f"Agents catalog: {len(owners)} application owners partition all MCP operations")
PY'''


def blocks(source_root: Path) -> list[tuple[str, str, str]]:
    apex = source_root / "data_dry_run/apex_builder"
    annotation, release, materialize = builder_chunks(apex / "builder.py")
    return [
        ("setup", "bash · download pinned APEX-Agents seed metadata", setup_block()),
        ("tools", "bash · download and validate the MCP-operation catalog",
         tools_check(sha256(apex / "catalog.json"))),
        ("annotate", "bash · shared task discovery and capability annotation",
         writer_body("data_dry_run/apex_builder/builder.py", annotation)),
        ("release", "bash · shared frequency-ranked release scheduler",
         writer_body("data_dry_run/apex_builder/builder.py", release, append=True) + "\n" +
         writer("evolve_tools/builder/frequency_config.py",
                source_root / "evolve_tools/builder/frequency_config.py")),
        ("package", "bash · shared accumulation, materialization, and validation",
         writer_body("data_dry_run/apex_builder/builder.py", materialize, append=True)),
        ("skills", "bash · download and validate the procedural-skill catalog",
         skills_check(sha256(apex / "skills.json"), source_root)),
        ("agents", "bash · validate the exact operation-owner partition", agents_check()),
        ("terminal", "bash · pinned CLI, double build, validation, and preflight",
         writer("data_dry_run/apex_builder/config.py", apex / "config.py") + "\n" +
         writer("data_dry_run/apex_builder/__init__.py", apex / "__init__.py") + "\n" +
         writer("data_dry_run/apex_builder/__main__.py", apex / "__main__.py") +
         '''\ncd "$EVOLVE_APEX_WORKDIR/data_dry_run"
"$EVOLVE_APEX_PYTHON" -m apex_builder all'''),
    ]


def render_javascript(items: list[tuple[str, str, str]],
                      guides: dict[str, dict[str, str]]) -> str:
    payload = {key: {"label": label, "code": code} for key, label, code in items}
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    guide_data = json.dumps(guides, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f'''/* Generated by tools/generate_apex_public_blocks.py. */
window.EVOHARNESS_APEX_BLOCKS = {data};
window.EVOHARNESS_APEX_GUIDES = {guide_data};
(function renderExactApexBlocks() {{
  document.querySelectorAll("[data-apex-exact]").forEach((host) => {{
    const item = window.EVOHARNESS_APEX_BLOCKS[host.dataset.apexExact];
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
    pre.dataset.apexExecutable = host.dataset.apexExact;
    const code = document.createElement("code");
    code.textContent = item.code;
    pre.appendChild(code);
    wrap.append(label, copy, pre);
    host.replaceChildren(wrap);
  }});
}})();

(function renderApexGuideBlocks() {{
  document.querySelectorAll("[data-apex-guide]").forEach((host) => {{
    const item = window.EVOHARNESS_APEX_GUIDES[host.dataset.apexGuide];
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
    pre.dataset.guideSnippet = host.dataset.apexGuide;
    const code = document.createElement("code");
    code.textContent = item.code;
    pre.appendChild(code);
    wrap.append(label, copy, pre);
    host.replaceChildren(wrap);
  }});
}})();
'''


def render_reference(items: list[tuple[str, str, str]]) -> str:
    intro = f'''# APEX-Agents construction path

Use these blocks in order for APEX-Agents at the pinned source snapshot. They are
generated from the same source as the rendered EvoHarnessBench construction page.
Do not substitute application names for tools: tools are exact Archipelago MCP
operations, while applications are availability guards and agent owners.

- APEX-Agents: `{APEX_COMMIT}`
- Archipelago: `{ARCHIPELAGO_COMMIT}`
- huggingface-hub `{HUGGINGFACE_HUB_VERSION}`, tomli `{TOMLI_VERSION}`, seed `42`
- Expected: 480 discovered; tools 392/22/4 stages, skills 470/19/6 stages,
  agents 392/10/3 stages
- Expected tree hash: `{EXPECTED_HASH}`

The seed is gated. The first block securely prompts for the user's own `HF_TOKEN`
after they accept access, downloads only four small metadata files, and never writes
the token. The 33 world archives are not downloaded. Tools are annotated from prompt,
world description, expected-output type, input-file type, and world availability.
Skills use fixed procedural atoms matched against the prompt, world description,
output type, and tool anchors. Neither annotation reads rubrics or gold answers.

The last check is a four-task source/gold integrity preflight. It does not execute an
agent or judge and does not claim task rewards.
'''
    labels = {
        "setup": "Download seed data · APEX-Agents",
        "tools": "Tools · Step 1 operation catalog",
        "annotate": "Tools · Step 1 shared annotation implementation",
        "release": "Tools · Step 2 shared release implementation",
        "package": "Tools · Steps 3 and 4 shared accumulation and writer",
        "skills": "Skills · Step 1 mine the prompts",
        "agents": "Agents · Step 1 partition the tools",
        "terminal": "Expected output · build, validate, and preflight",
    }
    sections = [intro.rstrip()]
    for key, _, code in items:
        sections.extend((f"## {labels[key]}", "```bash\n" + code.rstrip() + "\n```"))
    return "\n\n".join(sections) + "\n"


def expected() -> dict:
    return {
        "agents": {"capabilities": 10, "retained_tasks": 392, "versions": 3},
        "archipelago_commit": ARCHIPELAGO_COMMIT,
        "content_hash": EXPECTED_HASH,
        "discovered_tasks": 480,
        "huggingface_hub": HUGGINGFACE_HUB_VERSION,
        "seed": 42,
        "skills": {"capabilities": 19, "retained_tasks": 470, "versions": 6},
        "source_commit": APEX_COMMIT,
        "tomli": TOMLI_VERSION,
        "tools": {"capabilities": 22, "retained_tasks": 392, "versions": 4},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--javascript", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--public-root", type=Path, required=True)
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    items = blocks(source_root)
    guides = guide_blocks(source_root)
    args.javascript.write_text(render_javascript(items, guides), encoding="utf-8")
    args.reference.parent.mkdir(parents=True, exist_ok=True)
    args.reference.write_text(render_reference(items), encoding="utf-8")
    args.public_root.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        source_root / "data_dry_run/apex_builder/catalog.json",
        args.public_root / "tool-catalog.json",
    )
    shutil.copyfile(
        source_root / "data_dry_run/apex_builder/skills.json",
        args.public_root / "skill-catalog.json",
    )
    (args.public_root / "expected.json").write_text(
        json.dumps(expected(), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"rendered {len(items)} exact APEX-Agents blocks and {len(guides)} track guides")


if __name__ == "__main__":
    main()
