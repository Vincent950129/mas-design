"""Dump what each skill, agent, and piece of ALE software is, for the Task Gallery.

    python tools/dump_axis_docs.py [out.json]

Companion to tools/dump_tool_docs.py, which asks the live gyms what their tools
are. The other three axes need no server: their definitions are files in the
environment repo, staged into CODEX_HOME at run time, and this reads them there.

What each source gives:

  skills   `_oracle/skills/<name>/SKILL.md` -- a frontmatter description, an H1
           title, and a body whose sections are the skill itself: what it is
           for, the fields a run must write, the procedure, the caveats. Kept
           section by section, so the page can render it as documentation
           rather than as a wall of markdown.
  agents   `_agents/manifest.json` for the roster -- title, routing description,
           and the tools or software the specialist owns -- plus that agent's
           own `agent_skills/<name>/SKILL.md` for its brief.
  software an ALE label is off-the-shelf third-party software. Nothing in the
           repo knows what Blender is, and guessing would be worse than
           silence. What the registry in evolve_tools does know is how the
           harness provisions and polices each one -- kind, import name,
           executable, whether the guard can enforce it -- and the roster knows
           which specialist owns it. That is what the panel shows, and it says
           so rather than pretending to describe the product.

EOG agents are keyed by domain. 37 of the 38 names mean something different
depending on which system they belong to: `user_group` owns four different tool
sets across CSM, HR, ITSM and the hybrid, and `knowledge` carries four
descriptions. So a task resolves its agents through its own domain first, the
same way a tool resolves through its own gym. Skills, by contrast, are identical
wherever they appear, so one entry per name is the whole truth.

Long verbatim sections -- an agent's operating rules, a specialist's inherited
capabilities -- are kept by heading only. They run to pages of policy that the
orchestrator prompt already carries, and the panel marks them as abridged.

Reads the environment repo and static/tasks.json. Writes static/axis_docs.json.
"""
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENV_ROOT = Path("/export/xgen-finance/meta_agent/mas_evovle_enviroment")
DATA = ENV_ROOT / "data"
SOFTWARE_MOD = ENV_ROOT / "evolve_tools/src/ale_software.py"
TASKS = HERE.parent / "static/tasks.json"
OUT = HERE.parent / "static/axis_docs.json"

# The union library first: it carries all 29 skills, and the per-domain copies
# agree with it. For agents this is only a fallback chain -- a task resolves its
# own domain before any of these.
EOG_DOMAINS = ("enterprise_tri_hybrid", "csm", "hr", "itsm")

LIST_CAP = 8        # bullets kept per section, remainder counted
ROW_CAP = 12        # table rows kept, remainder counted
LABEL_CAP = 6       # spellings shown for one piece of software
ABRIDGE = {"Operating rules", "Capabilities"}   # kept by subheading only
DROP = {"Evidence (mined)"}                     # how the skill was mined, not what it is

FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)
COMMENT = re.compile(r"<!--.*?-->", re.S)
BULLET = re.compile(r"\A(?:[-*]|(\d+)\.)\s+(.*)\Z")
LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")      # references/ links go nowhere on the page
# A whole line in italics, which the page has no rule for. Bold and code spans it keeps,
# because a field name and prose about a field are not the same thing; this is decoration.
ITALIC = re.compile(r"\A_(.+)_\Z|\A\*(?!\*)(.+?)(?<!\*)\*\Z", re.S)


def frontmatter(text: str) -> tuple[dict, str]:
    m = FRONT.match(text)
    if not m:
        return {}, text
    fm = {}
    for key in ("name", "description"):
        g = re.search(rf'^{key}:\s*"?(.*?)"?\s*$', m.group(1), re.M)
        if g:
            fm[key] = g.group(1).strip()
    return fm, text[m.end():]


def plain(s: str) -> str:
    """Drop a whole-line italic wrapper, which the panel has no rule for."""
    m = ITALIC.match(s)
    return (m.group(1) or m.group(2)).strip() if m else s


def parse_blocks(lines: list[str]) -> list[list]:
    """One section's lines to renderable blocks.

    ["p", text] a paragraph, ["ul"|"ol", items, more?] a list, ["h", text] a
    subheading, ["t", head, rows, more?] a table.
    """
    out: list[list] = []
    para: list[str] = []
    items: list[str] = []
    rows: list[list[str]] = []
    kind = None

    def flush():
        nonlocal para, items, rows, kind
        if para:
            out.append(["p", " ".join(para)])
            para = []
        if items:
            block = [kind, items[:LIST_CAP]]
            if len(items) > LIST_CAP:
                block.append(len(items) - LIST_CAP)
            out.append(block)
            items, kind = [], None
        if rows:
            # Some of these tables are ragged in the source: a row whose last cell is
            # simply absent ends a column early. Squared off here rather than in the
            # renderer, which would otherwise emit a table the browser has to guess at.
            width = max(len(r) for r in rows)
            square = [r + [""] * (width - len(r)) for r in rows]
            block = ["t", square[0], square[1:1 + ROW_CAP]]
            if len(square) - 1 > ROW_CAP:
                block.append(len(square) - 1 - ROW_CAP)
            out.append(block)
            rows = []

    for raw in lines:
        s = LINK.sub(r"\1", raw.strip())
        if not s or s == "---":
            # A blank line inside a loose list is still that list; these files
            # space their bullets out. Only a paragraph ends here.
            if para:
                out.append(["p", " ".join(para)])
                para = []
            continue
        if s.startswith("|"):
            cells = [plain(c.strip()) for c in s.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):     # |---|---| ruling
                continue
            if not rows:
                flush()
            rows.append(cells)
            continue
        if s.startswith("###"):
            flush()
            out.append(["h", plain(s.lstrip("#").strip())])
            continue
        m = BULLET.match(s)
        if m:
            want = "ol" if m.group(1) else "ul"
            if kind and kind != want:
                flush()
            if para:
                out.append(["p", " ".join(para)])
                para = []
            kind = want
            items.append(plain(m.group(2).strip()))
            continue
        if items or rows:
            flush()
        para.append(plain(s))
    flush()
    return out


def parse_skill_md(path: Path) -> dict:
    """A SKILL.md to {title, description, sections}."""
    fm, body = frontmatter(path.read_text(errors="replace"))
    body = COMMENT.sub("", body)
    title, head, buf = "", None, []
    secs: list[tuple[str, list[str]]] = []
    for line in body.split("\n"):
        if not title and line.startswith("# "):
            title = line[2:].strip()
            continue
        if line.startswith("## "):
            if head:
                secs.append((head, buf))
            head, buf = line[3:].strip(), []
            continue
        buf.append(line)
    if head:
        secs.append((head, buf))

    out = []
    for head, lines in secs:
        if head in DROP:
            continue
        blocks = parse_blocks(lines)
        if head in ABRIDGE:
            subs = [b[1] for b in blocks if b[0] == "h"]
            if subs:
                out.append([head, [["ul", subs[:LIST_CAP]]], 1])
            continue
        if blocks:
            out.append([head, blocks])
    doc = {"t": title, "d": fm.get("description", "")}
    if out:
        doc["s"] = out
    return doc


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------- #
# What the corpus asks for                                                    #
# --------------------------------------------------------------------------- #

T = dict(TRACK=0, ENV=1, DOM=2, ORACLE=12, CUM=13, SEL=14, SOFT=15)


def read_tasks() -> dict:
    d = json.loads(TASKS.read_text())

    def names(i):
        return [d["names"][j] for j in d["lists"][i]] if i >= 0 else []

    want: dict[tuple[str, str], set[str]] = {}
    ale_rows: list[tuple[set[str], set[str]]] = []
    for t in d["tasks"]:
        env = d["envs"][t[T["ENV"]]]
        track = d["tracks"][t[T["TRACK"]]]
        axis = "software" if (env == "ale" and track == "tools") else track
        oracle, pool = names(t[T["ORACLE"]]), names(t[T["CUM"]])
        want.setdefault((env, axis), set()).update(oracle, pool)
        soft = names(t[T["SOFT"]])
        if soft:
            want.setdefault((env, "software"), set()).update(soft)
        if env == "ale":
            on_axis = axis == "software"
            ale_rows.append((set(soft) | (set(oracle) if on_axis else set()),
                             set(soft) | (set(pool) if on_axis else set())))
    return {"want": want, "ale_rows": ale_rows}


# --------------------------------------------------------------------------- #
# Axes                                                                        #
# --------------------------------------------------------------------------- #

def eog_skills(want: set[str]) -> dict:
    docs = {}
    for name in sorted(want):
        for dom in EOG_DOMAINS:
            base = DATA / f"evovling_skills/eog/{dom}/_oracle/skills/{name}"
            if not (base / "SKILL.md").exists():
                continue
            doc = parse_skill_md(base / "SKILL.md")
            index = base / "index.json"
            if index.exists():
                tables = json.loads(index.read_text()).get("tables") or []
                if tables:
                    doc["tb"] = tables
            docs[name] = doc
            break
    return docs


def ale_skills(want: set[str]) -> dict:
    docs = {}
    for name in sorted(want):
        base = DATA / f"evovling_skills/ale/_oracle/skills/{name}"
        if not (base / "SKILL.md").exists():
            continue
        doc = parse_skill_md(base / "SKILL.md")
        index = base / "index.json"
        if index.exists():
            meta = json.loads(index.read_text())
            if meta.get("tier"):
                doc["tr"] = meta["tier"]
            if meta.get("n_tagged_tasks"):
                doc["n"] = meta["n_tagged_tasks"]
        docs[name] = doc
    return docs


def agent_doc(entry: dict, skill: Path, owns_key: str) -> dict:
    doc = {"t": entry.get("title") or entry["name"], "d": entry.get("description") or ""}
    owns = entry.get(owns_key) or []
    if owns:
        doc["w"] = sorted(owns)
    if skill.exists():
        body = parse_skill_md(skill)
        if body.get("s"):
            doc["s"] = body["s"]
    return doc


def eog_agents(want: set[str]) -> dict:
    """Keyed by domain: the same name is a different specialist in each."""
    out = {}
    for dom in EOG_DOMAINS:
        root = DATA / f"evovling_agents/eog/{dom}/_agents"
        manifest = root / "manifest.json"
        if not manifest.exists():
            continue
        docs = {}
        for entry in json.loads(manifest.read_text())["agents"]:
            name = entry.get("name")
            if name not in want:
                continue
            docs[name] = agent_doc(
                entry, root / f"agent_skills/{name}/SKILL.md", "oracle_tools")
        if docs:
            out[dom] = docs
    return out


def ale_agents(want: set[str]) -> dict:
    root = DATA / "evovling_agents/ale/_agents"
    docs = {}
    for entry in json.loads((root / "agents/manifest.json").read_text())["agents"]:
        name = entry.get("name")
        if name not in want:
            continue
        docs[name] = agent_doc(entry, root / f"agent_skills/{name}/SKILL.md", "software")
    return docs


KIND_WORD = {
    "pylib": "Python library",
    "binary": "command-line program",
    "rlib": "R package",
    "gui": "desktop application",
    "runtime": "base runtime",
}


def software(want: set[str], rows: list[tuple[set[str], set[str]]]) -> dict:
    """Identity and provisioning for each ALE label, plus who owns it.

    Two casings of the same thing reach here -- the tools axis lowercases to
    `anndata`, the software list keeps the card's own `AnnData` -- and versioned
    or scripted variants carry more (`AmberTools 23 via software/run_ambertools.sh`).
    The registry's own normaliser collapses them, and the alias map records every
    literal the corpus interns, so the page resolves a chip by lookup alone.
    """
    reg = load_module(SOFTWARE_MOD, "ale_software")
    specs = {s.canonical: s for s in reg._REGISTRY}
    hard = set(reg.HARD_KINDS)

    owner = {}
    manifest = DATA / "evovling_agents/ale/_agents/agents/manifest.json"
    for entry in json.loads(manifest.read_text())["agents"]:
        for label in entry.get("software") or []:
            owner[reg.canonicalize(label)] = (entry["name"], entry.get("title") or "")

    alias = {name: reg.canonicalize(name) for name in sorted(want)}
    # Per task, not per literal: a row naming both `AnnData` and `anndata` is
    # one task reaching for one library.
    oracle_n: Counter = Counter()
    pool_n: Counter = Counter()
    for oracle, pool in rows:
        oracle_n.update({alias.get(n) or reg.canonicalize(n) for n in oracle})
        pool_n.update({alias.get(n) or reg.canonicalize(n) for n in pool})

    items: dict[str, dict] = {}
    for name, canon in alias.items():
        item = items.setdefault(canon, {"l": {}})
        if name.lower() != canon:
            # The two axes disagree on case for the same spelling. Show the one
            # the task card wrote, not the lowercased index key beside it.
            item["l"].setdefault(name.lower(), name)
            if name != name.lower():
                item["l"][name.lower()] = name
    for canon, item in items.items():
        spec = specs.get(canon)
        if spec:
            item["k"] = KIND_WORD.get(spec.kind, spec.kind)
            item["e"] = 1 if spec.kind in hard else 0
            for key, vals in (("m", spec.py_modules), ("b", spec.binaries),
                              ("r", spec.r_packages)):
                if vals:
                    item[key] = list(vals)
        if canon in owner:
            item["f"], item["ft"] = owner[canon]
        if oracle_n[canon]:
            item["n"] = oracle_n[canon]
        if pool_n[canon]:
            item["q"] = pool_n[canon]
        if item["l"]:
            item["l"] = sorted(item["l"].values())[:LABEL_CAP]
        else:
            del item["l"]
    return {"alias": alias, "items": items}


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    corpus = read_tasks()
    want = corpus["want"]

    skills = {"eog": eog_skills(want.get(("eog", "skills"), set())),
              "ale": ale_skills(want.get(("ale", "skills"), set()))}
    agents = {"eog": eog_agents(want.get(("eog", "agents"), set())),
              "ale": ale_agents(want.get(("ale", "agents"), set()))}
    soft = software(want.get(("ale", "software"), set()), corpus["ale_rows"])

    payload = {"skills": skills, "agents": agents, "software": soft}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, separators=(",", ":")))

    def report(label, asked, got, tail=""):
        miss = sorted(asked - got)
        print(f"  {label:<5} {len(got):>3}/{len(asked):<3} documented{tail}"
              f"{'   MISSING ' + str(miss[:6]) if miss else ''}")

    print("skills")
    for env in ("eog", "ale"):
        report(env, want.get((env, "skills"), set()), set(skills[env]))
    print("agents")
    union = set().union(*[set(d) for d in agents["eog"].values()]) if agents["eog"] else set()
    report("eog", want.get(("eog", "agents"), set()), union,
           f" over {len(agents['eog'])} domains")
    for dom, docs in sorted(agents["eog"].items()):
        print(f"        {dom:<24} {len(docs):>3}")
    report("ale", want.get(("ale", "agents"), set()), set(agents["ale"]))
    print("software")
    items = soft["items"]
    known = [c for c, i in items.items() if i.get("k")]
    owned = [c for c, i in items.items() if i.get("f")]
    print(f"  {len(soft['alias'])} literals collapse to {len(items)} distinct")
    print(f"  {len(known)} carry registry identity, {len(owned)} owned by a specialist")
    bare = sorted(c for c in items if not items[c].get("k") and not items[c].get("f"))
    if bare:
        print(f"  {len(bare)} with neither: {bare[:6]}{' ...' if len(bare) > 6 else ''}")
    print(f"\nwrote {out_path} ({out_path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
