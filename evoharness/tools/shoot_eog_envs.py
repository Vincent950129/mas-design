"""Screenshot each distinct EnterpriseOps-Gym environment for the Tasks tab.

    # 1. dump snapshots from the live gym containers
    /tmp/eogvenv/bin/python tools/dump_eog_snapshots.py
    # 2. serve the demo's figure harness (fixtures are staged automatically)
    cd ../../../mas-orchestra-demo/frontend && npx vite --port 3011 --host 127.0.0.1
    # 3. shoot
    python tools/shoot_eog_envs.py [base_url]

One capture per environment, of the ``app`` view only: the environment as a
person would see it, which is the picture a reader wants next to a task prompt.
The relational ``graph`` view answers a different question (how a task is
graded) and is not shot here.

Because ``dump_eog_snapshots.py`` keys environments by seeded contents rather
than by domain, every task points at the environment it actually starts from.

Captures are then deduplicated on the rendered pixels, and a good number of
them collapse. That is a fact about the view rather than a shortcut: each app
view renders a curated slice — a couple of tables, the first screenful of rows
— and many seeds differ only in timestamps, in rows below the fold, or in
tables this view never shows. Widening or lengthening the capture was tried and
recovers almost nothing. So environments that look the same share one file, and
the manifest still keys them separately so per-task mapping stays exact.

Writes ``static/images/env/<env>.webp`` plus a card thumbnail, and an
``index.json`` manifest consumed by ``build_tasks.py``. Captures are taken at 2x
and downscaled, so text stays legible in the lightbox without shipping
megabytes of PNG. Resumable — an environment already emitted is skipped unless
``--fresh`` is passed.
"""
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "static" / "images" / "env"
SNAPS = HERE / "eog_snapshots"
ARGS = [a for a in sys.argv[1:] if not a.startswith("-")]
FRESH = "--fresh" in sys.argv
BASE = ARGS[0] if ARGS else "http://127.0.0.1:3011"

# Panel header label per gym, matching the demo's own gym_config labels.
LABELS = {
    "calendar": "Calendar",
    "email": "Email",
    "hr": "HR",
    "itsm": "ITSM",
    "teams": "Teams",
    "csm": "CSM",
    "drive": "Drive",
}
# One line on what kind of system the reader is looking at. The rows on screen
# are this task's own starting state, so the caption stays about the system.
CAPTIONS = {
    "calendar": "Google-Calendar-style sandbox: calendars, events, ACLs and attendees.",
    "email": "Gmail-style sandbox: threads, messages, labels and drafts.",
    "hr": "HR case management sandbox: services, cases, approvals and employee records.",
    "itsm": "ITSM sandbox: incidents, changes, services and assignment groups.",
    "teams": "Teams-style sandbox: teams, channels, messages and memberships.",
    "csm": "Customer service sandbox: accounts, contacts, cases and entitlements.",
    "drive": "Drive-style sandbox: folders, files, revisions and permissions.",
}
VIEWPORT = {"width": 1280, "height": 800}
# 2x so the figure stays crisp when a reader opens it full-size.
SCALE = 2
FULL_W, FULL_Q = 1400, 80
THUMB_W, THUMB_Q = 460, 70


def emit(png: Path, env: str) -> dict:
    """Downscale one raw capture into the shipped full + thumbnail WebP pair."""
    im = Image.open(png).convert("RGB")
    w, h = im.size
    rec = {}
    for suffix, width, q, key in ((".webp", FULL_W, FULL_Q, "file"),
                                  (".t.webp", THUMB_W, THUMB_Q, "thumb")):
        scaled = im.resize((width, max(1, round(h * width / w))), Image.LANCZOS)
        p = OUT / f"{env}{suffix}"
        scaled.save(p, "WEBP", quality=q, method=5)
        rec[key] = p.name
        if key == "file":
            rec["w"], rec["h"] = scaled.size
    return rec


def stage_fixtures() -> Path | None:
    """Copy the snapshot fixtures where the Vite harness can serve them."""
    pub = Path("/export/xgen-finance/meta_agent/mas-orchestra-demo/frontend/public/figures")
    if not pub.parent.exists():
        return None
    pub.mkdir(parents=True, exist_ok=True)
    for stale in pub.glob("*.json"):
        stale.unlink()
    for src in SNAPS.glob("*.json"):
        shutil.copy2(src, pub / src.name)
    return pub


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    index = json.loads((SNAPS / "index.json").read_text())
    envs: dict[str, dict] = index["envs"]

    staged = stage_fixtures()
    print(f"fixtures -> {staged}" if staged else "note: demo frontend not found; "
          "assuming fixtures are already served", file=sys.stderr)

    man_path = OUT / "index.json"
    if FRESH:
        for f in OUT.iterdir():
            if f.is_file():
                f.unlink()

    def save(m: dict) -> None:
        """Ship the task mapping alongside the pictures, so `build_tasks.py`
        needs only this directory and not the snapshot scratch space."""
        man_path.write_text(json.dumps(
            {"envs": m, "taskEnvs": index["taskEnvs"]}, indent=2, sort_keys=True))

    manifest = {}
    if man_path.exists() and not FRESH:
        prev = (json.loads(man_path.read_text()).get("envs") or {})
        manifest = {k: v for k, v in prev.items()
                    if k in envs and (OUT / v["file"]).exists() and v.get("shot")}
        if manifest:
            print(f"resuming: {len(manifest)} environments already shot")

    # `shot` is the hash of the raw capture, which is what lets a resumed run
    # keep collapsing duplicates instead of re-emitting one file per env.
    owner: dict[str, str] = {}
    for env, rec in manifest.items():
        owner.setdefault(rec["shot"], env)

    todo = [e for e in sorted(envs) if e not in manifest]
    reused = 0
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        browser = p.chromium.launch(
            args=["--force-color-profile=srgb", "--font-render-hinting=none"])
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=SCALE)
        for i, env in enumerate(todo, 1):
            gym = envs[env]["gym"]
            url = (f"{BASE}/figure.html?domain={env}&gym={gym}"
                   f"&view=app&title={LABELS.get(gym, gym)}")
            page.goto(url, wait_until="networkidle")
            try:
                page.wait_for_selector("body[data-figure-ready]", timeout=25_000)
            except Exception:
                print(f"  {env}: ready flag timed out, capturing anyway", file=sys.stderr)
            page.wait_for_timeout(700)   # activity chips animate in
            raw = Path(tmp) / f"{env}.png"
            page.screenshot(path=str(raw), animations="disabled")

            shot = hashlib.sha1(raw.read_bytes()).hexdigest()
            twin = owner.get(shot)
            if twin:
                src = manifest[twin]
                rec = {k: src[k] for k in ("file", "thumb", "w", "h", "shot")}
                reused += 1
                print(f"  [{i}/{len(todo)}] {env}: same picture as {twin}")
            else:
                rec = emit(raw, env)
                rec["shot"] = shot
                owner[shot] = env
                kb = (OUT / rec["file"]).stat().st_size / 1024
                print(f"  [{i}/{len(todo)}] {env}: {kb:.0f} KB -> {rec['file']}")
            rec.update(gym=gym, label=LABELS.get(gym, gym),
                       caption=CAPTIONS.get(gym, ""), rows=envs[env]["rows"])
            manifest[env] = rec
            save(manifest)
        browser.close()

    save(manifest)
    keep = {"index.json"} | {r["file"] for r in manifest.values()} \
        | {r["thumb"] for r in manifest.values()}
    for stale in OUT.iterdir():
        if stale.is_file() and stale.name not in keep:
            stale.unlink()

    pics = len({r["file"] for r in manifest.values()})
    total = sum(f.stat().st_size for f in OUT.iterdir() if f.is_file())
    print(f"\n{len(manifest)}/{len(envs)} environments -> {pics} distinct pictures "
          f"({reused} collapsed onto a twin), {total / 1e6:.2f} MB -> {OUT}")
    per_gym = {}
    for r in manifest.values():
        per_gym.setdefault(r["gym"], set()).add(r["file"])
    print("distinct pictures per gym: "
          + ", ".join(f"{g} {len(v)}" for g, v in sorted(per_gym.items())))
    return 0 if len(manifest) == len(envs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
