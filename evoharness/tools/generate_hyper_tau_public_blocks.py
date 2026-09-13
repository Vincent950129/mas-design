#!/usr/bin/env python3
"""Render the Hyper-Tau-Bench worked-example blocks from the repaired adapter."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


PIN = "6e9f34c685d40fa7a9f5935d8970af6fd9d5f118"
PUBLIC_SERVICE = "https://educator-marrow-cultural.ngrok-free.dev"
DELIMITER = "__EVOHARNESS_HYPER_TAU_FILE__"
PRIVATE_OUTPUT = "/export/xgen-finance/meta_agent/mas_evovle_enviroment/data_dry_run"


def function_source(path: Path, *names: str) -> str:
    body = path.read_text(encoding="utf-8")
    lines = body.splitlines(keepends=True)
    functions = {
        node.name: node
        for node in ast.parse(body).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    missing = [name for name in names if name not in functions]
    if missing:
        raise RuntimeError(f"missing functions in {path}: {missing}")
    chunks: list[str] = []
    for name in names:
        node = functions[name]
        start = min([node.lineno, *(item.lineno for item in node.decorator_list)]) - 1
        chunks.append("".join(lines[start:node.end_lineno]).rstrip())
    return "\n\n".join(chunks) + "\n"


def writer_body(relative: str, body: str) -> str:
    if not body.endswith("\n"):
        body += "\n"
    if DELIMITER in body:
        raise RuntimeError(f"heredoc delimiter occurs in {relative}")
    parent = Path(relative).parent.as_posix()
    return (
        f'mkdir -p "$EVOLVE_HYPER_WORKDIR/{parent}"\n'
        f'cat > "$EVOLVE_HYPER_WORKDIR/{relative}" <<\'{DELIMITER}\'\n'
        f"{body}{DELIMITER}\n"
    )


def setup_block() -> str:
    return f'''export EVOLVE_HYPER_WORKDIR="${{EVOLVE_HYPER_WORKDIR:-$PWD/evoharnessbench-hyper-tau}}"
export EVOLVE_BUILD_SKILL_DIR="${{EVOLVE_BUILD_SKILL_DIR:-${{CODEX_HOME:-$HOME/.codex}}/skills/evolve-benchmark}}"

if [ -e "$EVOLVE_HYPER_WORKDIR" ]; then
  echo "Refusing to overwrite existing path: $EVOLVE_HYPER_WORKDIR" >&2
  exit 1
fi
mkdir -p "$EVOLVE_HYPER_WORKDIR/cache" \
  "$EVOLVE_HYPER_WORKDIR/hyper_tau_annotation_bundle/adapter" \
  "$EVOLVE_HYPER_WORKDIR/hyper_tau_annotation_bundle/reports"

git clone https://github.com/sierra-research/hyper-tau-bench.git \
  "$EVOLVE_HYPER_WORKDIR/cache/hyper-tau-bench"
git -C "$EVOLVE_HYPER_WORKDIR/cache/hyper-tau-bench" checkout --detach {PIN}
test "$(git -C "$EVOLVE_HYPER_WORKDIR/cache/hyper-tau-bench" rev-parse HEAD)" = "{PIN}"

: "${{EVAL_SERVICE_API_KEY:?Required — open MyAuthtoken in the EvoHarness live demo}}"
curl -fsSL -H "Authorization: Bearer $EVAL_SERVICE_API_KEY" \
  {PUBLIC_SERVICE}/resources/evolve-benchmark/install.sh | bash
test -f "$EVOLVE_BUILD_SKILL_DIR/scripts/evolve_core.py"
printf 'Downloaded the 53-task Hyper-Tau-Bench seed at %.8s\n' "{PIN}"'''


def approval_and_plan_block() -> str:
    return '''export BUNDLE="$EVOLVE_HYPER_WORKDIR/hyper_tau_annotation_bundle"
export ENGINE="$EVOLVE_BUILD_SKILL_DIR/scripts/evolve_core.py"

python "$ENGINE" inspect --bundle "$BUNDLE" --report "$BUNDLE/reports/inspect.json"
python - <<'PY'
import json, os, pathlib

bundle = pathlib.Path(os.environ["BUNDLE"])
report = json.loads((bundle / "reports/inspect.json").read_text())
if report["repair_problems"]:
    raise RuntimeError(report["repair_problems"])
approvals = json.loads((bundle / "approvals.json").read_text())
approvals["annotations"] = {
    "approved": True,
    "input_sha256": report["annotation_input_sha256"],
    "basis": "executed the displayed deterministic Hyper-Tau adapter",
}
(bundle / "approvals.json").write_text(
    json.dumps(approvals, indent=2, sort_keys=True) + "\n"
)
PY

python "$ENGINE" plan --bundle "$BUNDLE" --report "$BUNDLE/reports/plan.json"
python - <<'PY'
import json, os, pathlib

bundle = pathlib.Path(os.environ["BUNDLE"])
plan = json.loads((bundle / "reports/plan.json").read_text())
approvals = json.loads((bundle / "approvals.json").read_text())
approvals["staging"] = {
    "approved": True,
    "plan_sha256": plan["plan_sha256"],
    "basis": "executed the displayed frequency-ranked staging plan",
}
(bundle / "approvals.json").write_text(
    json.dumps(approvals, indent=2, sort_keys=True) + "\n"
)
PY'''


def build_block() -> str:
    return '''export BUNDLE="$EVOLVE_HYPER_WORKDIR/hyper_tau_annotation_bundle"
export CANDIDATE="$EVOLVE_HYPER_WORKDIR/hyper_tau_candidate"
export ENGINE="$EVOLVE_BUILD_SKILL_DIR/scripts/evolve_core.py"

# A reproducible static candidate intentionally remains preflight-only until
# the real, credentialed Hyper-Tau verifier succeeds.
set +e
python "$ENGINE" reproduce --bundle "$BUNDLE" --output "$CANDIDATE" \
  --report "$BUNDLE/reports/reproduction.json"
status=$?
set -e
test "$status" -eq 1

python - <<'PY'
import json, os, pathlib

bundle = pathlib.Path(os.environ["BUNDLE"])
report = json.loads((bundle / "reports/reproduction.json").read_text())
assert report["reproducible"] is True
assert report["validation"]["static_passed"] is True
assert report["validation"]["status"] == "preflight-only"
print("Static construction and byte-for-byte reproduction passed:", report["tree_hash"])
PY'''


def validation_block(verifier: str) -> str:
    return writer_body(
        "hyper_tau_annotation_bundle/adapter/run_verifier.py", verifier
    ) + '''
python -m pip install "uv==0.12.13"
uv venv --python 3.12 "$EVOLVE_HYPER_WORKDIR/cache/hyper-tau-venv"
UV_PROJECT_ENVIRONMENT="$EVOLVE_HYPER_WORKDIR/cache/hyper-tau-venv" \
  uv sync --project "$EVOLVE_HYPER_WORKDIR/cache/hyper-tau-bench" --locked

: "${OPENAI_API_KEY:?Required by the official Hyper-Tau developer run}"
: "${OPENROUTER_API_KEY:?Required by the official sealed evaluator}"
python "$EVOLVE_BUILD_SKILL_DIR/scripts/evolve_core.py" validate \
  --bundle "$EVOLVE_HYPER_WORKDIR/hyper_tau_annotation_bundle" \
  --candidate "$EVOLVE_HYPER_WORKDIR/hyper_tau_candidate" \
  --run-smoke \
  --report "$EVOLVE_HYPER_WORKDIR/hyper_tau_annotation_bundle/reports/validation.json"

# Promotion remains a separate, explicit user decision after this report passes.'''


def render_javascript(blocks: dict[str, dict[str, str]], guides: dict[str, dict[str, str]]) -> str:
    block_data = json.dumps(blocks, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    guide_data = json.dumps(guides, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f'''/* Generated by tools/generate_hyper_tau_public_blocks.py. */
window.EVOHARNESS_HYPER_BLOCKS = {block_data};
window.EVOHARNESS_HYPER_GUIDES = {guide_data};

(function renderHyperTauBlocks() {{
  const render = (selector, items, keyName, executable) => {{
    document.querySelectorAll(selector).forEach((host) => {{
      const key = host.dataset[keyName];
      const item = items[key];
      if (!item) return;
      const wrap = document.createElement("div");
      wrap.className = "sv-codewrap " + (executable ? "tb2-exact-wrap" : "tb2-guide-wrap");
      const label = document.createElement("span");
      label.className = "sv-lang";
      label.textContent = item.label;
      const copy = document.createElement("button");
      copy.className = "sv-copy";
      copy.type = "button";
      copy.textContent = "Copy";
      const pre = document.createElement("pre");
      pre.className = "sv-code " + (executable ? "tb2-exact-code" : "tb2-guide-code");
      pre.dataset.lang = item.lang || (executable ? "bash" : "python");
      if (executable) pre.dataset.hyperExecutable = key;
      else pre.dataset.guideSnippet = key;
      const code = document.createElement("code");
      code.textContent = item.code;
      pre.appendChild(code);
      wrap.append(label, copy, pre);
      host.replaceChildren(wrap);
    }});
  }};
  render("[data-hyper-exact]", window.EVOHARNESS_HYPER_BLOCKS, "hyperExact", true);
  render("[data-hyper-guide]", window.EVOHARNESS_HYPER_GUIDES, "hyperGuide", false);
}})();
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--javascript", required=True, type=Path)
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    bundle = source_root / "data_dry_run/hyper_tau_bench_builder/hyper_tau_annotation_bundle"
    adapter = bundle / "adapter/build_annotations.py"
    engine = source_root / "eval_service/skills/evolve-benchmark/scripts/evolve_core.py"
    adapter_body = adapter.read_text(encoding="utf-8").replace(PRIVATE_OUTPUT, ".")
    blocks = {
        "setup": {"label": "bash · download the pinned seed and construction skill", "lang": "bash", "code": setup_block()},
        "annotate": {"label": "bash · install and run the frozen public annotation adapter", "lang": "bash", "code": writer_body("hyper_tau_annotation_bundle/adapter/build_annotations.py", adapter_body) + '\npython "$EVOLVE_HYPER_WORKDIR/hyper_tau_annotation_bundle/adapter/build_annotations.py"'},
        "stage": {"label": "bash · inspect, rank, release, and approve the displayed plan", "lang": "bash", "code": approval_and_plan_block()},
        "build": {"label": "bash · accumulate, write, and reproduce all three tracks", "lang": "bash", "code": build_block()},
        "validate": {"label": "bash · run the official credentialed verifier smoke", "lang": "bash", "code": validation_block((bundle / "adapter/run_verifier.py").read_text(encoding="utf-8"))},
    }
    guides = {
        "tools-annotate": {"label": "python · exact operation extraction and owner mapping", "code": function_source(adapter, "operation_defs", "owner_for", "scope_for_task", "evidence_operation_names")},
        "tools-release": {"label": "python · shared frequency-ranked release scheduler", "code": function_source(engine, "_rank", "_frequency_anchors", "_frequency_plan")},
        "tools-write": {"label": "python · earliest-stage assignment and canonical rows", "code": function_source(engine, "_assign", "_assignments", "_task_row")},
        "skills-annotate": {"label": "python · exact public-prompt construction and evidence", "code": function_source(adapter, "build_public_prompt", "prompt_skill_evidence")},
        "skills-release": {"label": "python · established procedural-skill sequencer", "code": function_source(engine, "_rank", "_skill_plan")},
        "skills-write": {"label": "python · held-out SKILL.md and index materialization", "code": function_source(engine, "_materialize_skills")},
        "agents-annotate": {"label": "python · tools-to-owner agent derivation", "code": function_source(engine, "_axis_capabilities", "_skill_agent_partition")},
        "agents-release": {"label": "python · independent owner-frequency curriculum", "code": function_source(engine, "_rank", "_frequency_plan")},
        "agents-write": {"label": "python · owner skills, agent TOMLs, and manifests", "code": function_source(engine, "_agent_materialization", "_materialize_agents")},
    }
    args.javascript.write_text(render_javascript(blocks, guides), encoding="utf-8")
    print(f"rendered {len(blocks)} Hyper-Tau blocks and {len(guides)} track guides")


if __name__ == "__main__":
    main()
