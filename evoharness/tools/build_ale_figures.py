"""Turn ALE tasks' staged media into web figures for the Tasks tab.

    python tools/build_ale_figures.py [path/to/agents-last-exam]

Many ALE tasks hand the agent real artifacts — a scanned bridge drawing, a
whole-slide histology tile, a multi-view render of a character to rebuild, a
routine to score frame by frame. Those files ARE the task, so the gallery shows
them next to the prompt, the way the ALE demo does.

Two roles are kept and labelled separately, because they answer different
questions:

* ``input``     — staged under the task's `input/`, i.e. what the agent is
  handed at t=0.
* ``reference`` — staged under `reference/`, i.e. the expected result the
  graders compare against.

Everything else in a task directory is skipped: `software/` holds installers
and AppImages, and vendored `node_modules` / `.venv` trees are full of library
demo images that have nothing to do with the task.

Stills become WebP (a full size for the lightbox, a thumbnail for the card).
Videos get a poster frame plus a short muted clip, so a motion task reads as
motion. Writes `static/images/ale/` and an `index.json` manifest keyed by
task_id, which `build_tasks.py` folds into the bundle.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

# Whole-slide histology is legitimately gigapixel (one slide here is 97792 x
# 221184). The guard fires on the header before we get a chance to pick a
# smaller pyramid level, and these are local files from a known corpus, so it
# is off; `open_still` is what actually keeps decode bounded.
Image.MAX_IMAGE_PIXELS = None

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "static" / "images" / "ale"
BUNDLE = HERE.parent / "static" / "tasks.json"
DEFAULT_ALE = Path("/export/xgen-finance/meta_agent/mas_evovle_enviroment/reference/agents-last-exam")

STILL_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv"}
# Vendored dependency trees, task scaffolding and installers. Anything under
# these is somebody else's artwork, not the task's.
SKIP_DIRS = {
    "software", "node_modules", ".venv", "venv", "__pycache__", ".git",
    "site-packages", "dist-packages", ".cache", "build", "dist", ".ipynb_checkpoints",
}
# Decoding a pyramidal whole-slide TIFF costs GBs of RAM for a picture we then
# shrink to 1100px, so read stills only up to this size.
MAX_STILL_BYTES = 90 * 1024 * 1024
MAX_VIDEO_BYTES = 600 * 1024 * 1024
# Below this an image is almost certainly UI chrome (a spinner, a logo).
MIN_STILL_BYTES = 3 * 1024
MIN_DIM = 80

FULL_W, FULL_Q = 1100, 78
THUMB_W, THUMB_Q = 460, 70
# Clips are encoded at the stills' width so the lightbox shows every figure at
# one size without upscaling a small clip into a blurry one.
CLIP_SECONDS, CLIP_W, CLIP_FPS = 6, FULL_W, 24
PER_TASK = 3


def ffmpeg_exe() -> str:
    """An ffmpeg that can actually encode H.264.

    The conda ffmpeg on this box ships without libx264 and with a mismatched
    libopenh264, so it can read the source videos but not write a clip a
    browser will play. imageio-ffmpeg bundles a static build that can.
    """
    override = os.environ.get("FFMPEG")
    if override:
        return override
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


FFMPEG = ffmpeg_exe()


def ale_task_ids() -> list[str]:
    b = json.loads(BUNDLE.read_text())
    envs = b["envs"]
    return sorted({t[7] for t in b["tasks"] if envs[t[1]] == "ale"})


def role_of(rel: Path) -> str | None:
    """`input` / `reference` from the first matching path segment, else None."""
    for part in rel.parts:
        if part == "input":
            return "input"
        if part.startswith("reference") or part == "expected_output":
            return "reference"
    return None


def scan(task_dir: Path) -> list[tuple[Path, str, Path]]:
    """Every candidate (path, role, key) under one staged task directory.

    ``key`` is the path relative to the task directory. A task is often staged
    under both `task-data/` and `data/tasks/`, so the relative path is what
    identifies a file — keying on the absolute path would emit the same picture
    twice.
    """
    found = []
    stack = [task_dir]
    while stack:
        d = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for e in entries:
            if e.is_symlink() and e.is_dir():
                continue  # seed data is symlink-heavy; don't chase into it
            if e.is_dir():
                if e.name not in SKIP_DIRS:
                    stack.append(e)
                continue
            ext = e.suffix.lower()
            if ext not in STILL_EXT and ext not in VIDEO_EXT:
                continue
            rel = e.relative_to(task_dir)
            role = role_of(rel)
            if role is None:
                continue
            found.append((e, role, rel))
    return found


def rank(item: tuple[Path, str, Path]) -> tuple:
    """Inputs first, then bigger files (a richer picture) before smaller."""
    path, role, key = item
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    return (0 if role == "input" else 1, -size, str(key))


def caption_for(path: Path, role: str) -> str:
    stem = path.stem.replace("_", " ").replace("-", " ").strip()
    stem = " ".join(w for w in stem.split() if w)
    label = "Staged input" if role == "input" else "Reference output"
    return f"{label} · {stem}" if stem else label


def signature(path: Path) -> tuple:
    """Cheap content fingerprint: size plus a hash of the head and tail.

    Some tasks stage the same picture at several paths (a render sweep copied
    per variant, or a file duplicated across staging roots under different
    names). Hashing whole multi-hundred-MB files to notice that is wasteful,
    and the edges are more than enough to separate distinct images.
    """
    size = path.stat().st_size
    h = hashlib.md5()
    span = 256 * 1024
    with path.open("rb") as fh:
        h.update(fh.read(span))
        if size > 2 * span:
            fh.seek(-span, 2)
            h.update(fh.read(span))
    return (size, h.hexdigest())


def open_still(src: Path) -> Image.Image | None:
    """Decode a still, using a pyramid level for slides too big to read whole.

    Whole-slide histology is stored as a multi-resolution TIFF whose base level
    is gigabytes. Every level is a separate frame, so seeking to the smallest
    one that still exceeds our output width yields the same picture for a
    thousandth of the memory.
    """
    size = src.stat().st_size
    if size < MIN_STILL_BYTES:
        return None
    im = Image.open(src)
    if size > MAX_STILL_BYTES:
        levels = getattr(im, "n_frames", 1)
        if levels <= 1:
            return None
        best = None
        for i in range(levels):
            im.seek(i)
            w, h = im.size
            if w >= FULL_W and (best is None or w < best[1]):
                best = (i, w)
        if best is None:  # every level is smaller than our target; take the largest
            best = (0, 0)
            for i in range(levels):
                im.seek(i)
                if im.size[0] > best[1]:
                    best = (i, im.size[0])
        im.seek(best[0])
    im.load()
    return im


def save_still(src: Path, base: str) -> dict | None:
    try:
        im = open_still(src)
        if im is None:
            return None
    except Exception as e:
        print(f"    skip {src.name}: {type(e).__name__}: {e}", file=sys.stderr)
        return None
    w, h = im.size
    if w < MIN_DIM or h < MIN_DIM:
        return None
    if im.mode in ("P", "LA", "RGBA"):
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
        im = bg
    elif im.mode != "RGB":
        im = im.convert("RGB")
    out = {"w": w, "h": h}
    for suffix, width, q in (("", FULL_W, FULL_Q), (".t", THUMB_W, THUMB_Q)):
        target = im if width >= w else im.resize((width, max(1, round(h * width / w))), Image.LANCZOS)
        p = OUT / f"{base}{suffix}.webp"
        target.save(p, "WEBP", quality=q, method=5)
        out["file" if suffix == "" else "thumb"] = p.name
    return out


def save_video(src: Path, base: str) -> dict | None:
    """Poster frame + a short muted clip, both scaled down."""
    try:
        if src.stat().st_size > MAX_VIDEO_BYTES:
            return None
    except OSError:
        return None
    poster_png = OUT / f"{base}.poster.png"
    r = subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-ss", "0.5", "-i", str(src),
         "-frames:v", "1", "-vf", f"scale={FULL_W}:-2", str(poster_png)],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not poster_png.exists() or poster_png.stat().st_size == 0:
        print(f"    skip video {src.name}: poster failed — {r.stderr.strip()[:160]}", file=sys.stderr)
        return None
    im = Image.open(poster_png).convert("RGB")
    w, h = im.size
    out = {"w": w, "h": h, "kind": "video"}
    im.save(OUT / f"{base}.webp", "WEBP", quality=FULL_Q, method=5)
    im.resize((THUMB_W, max(1, round(h * THUMB_W / w))), Image.LANCZOS).save(
        OUT / f"{base}.t.webp", "WEBP", quality=THUMB_Q, method=5)
    poster_png.unlink()
    out["file"], out["thumb"] = f"{base}.webp", f"{base}.t.webp"

    clip = OUT / f"{base}.mp4"
    r = subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-t", str(CLIP_SECONDS), "-i", str(src),
         "-an", "-vf", f"scale={CLIP_W}:-2,fps={CLIP_FPS}", "-c:v", "libx264",
         "-preset", "slow", "-crf", "30", "-movflags", "+faststart",
         "-pix_fmt", "yuv420p", str(clip)],
        capture_output=True, text=True,
    )
    if r.returncode == 0 and clip.exists() and clip.stat().st_size > 0:
        out["clip"] = clip.name
    else:
        clip.unlink(missing_ok=True)
        print(f"    {src.name}: poster only, clip failed — {r.stderr.strip()[:160]}", file=sys.stderr)
    return out


def main() -> int:
    positional = [a for a in sys.argv[1:] if not a.startswith("-")]
    ale = Path(positional[0]) if positional else DEFAULT_ALE
    roots = [ale / "task-data", ale / "data" / "tasks"]
    roots = [r for r in roots if r.exists()]
    if not roots:
        print(f"no staged data under {ale}", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)

    # Resumable: scanning and decoding the staged trees takes minutes, so an
    # interrupted run picks up where it left off. Pass --fresh to rebuild all.
    index_path = OUT / "index.json"
    fresh = "--fresh" in sys.argv
    manifest: dict[str, list[dict]] = {}
    done: set[str] = set()
    if index_path.exists() and not fresh:
        manifest = json.loads(index_path.read_text())
        done = set(manifest.get("__done__", []))
        manifest.pop("__done__", None)

    task_ids = ale_task_ids()
    print(f"{len(task_ids)} ALE tasks ({len(done)} already done), "
          f"roots: {[str(r) for r in roots]}\n", flush=True)

    for n, tid in enumerate(task_ids, 1):
        if tid in done:
            continue
        t0 = time.time()
        candidates: list[tuple[Path, str, Path]] = []
        for root in roots:
            d = root / tid
            if d.is_dir():
                candidates += scan(d)
        # Collapse the same relative path staged under several roots.
        by_key: dict[Path, tuple[Path, str, Path]] = {}
        for item in candidates:
            by_key.setdefault(item[2], item)
        candidates = sorted(by_key.values(), key=rank)

        # One figure per source directory keeps a task from showing three
        # near-identical frames out of the same render sweep, and the content
        # signature catches the same picture staged under two names.
        figs, seen_dirs, seen_sigs = [], set(), set()
        for path, role, key in candidates:
            if len(figs) >= PER_TASK:
                break
            dkey = (key.parent, role)
            if dkey in seen_dirs:
                continue
            try:
                sig = signature(path)
            except OSError:
                continue
            if sig in seen_sigs:
                continue
            base = f"{tid.replace('/', '__')}__{len(figs)}"
            rec = (save_video if path.suffix.lower() in VIDEO_EXT else save_still)(path, base)
            if rec is None:
                continue
            rec.setdefault("kind", "image")
            rec["caption"] = caption_for(path, role)
            rec["role"] = role
            rec["src"] = str(path.relative_to(ale))  # provenance, shown on hover
            figs.append(rec)
            seen_dirs.add(dkey)
            seen_sigs.add(sig)

        # Same filename in sibling directories (reference_renders_v1 / _v2)
        # would otherwise produce identical captions; qualify with the folder.
        counts: dict[str, int] = {}
        for f in figs:
            counts[f["caption"]] = counts.get(f["caption"], 0) + 1
        for f in figs:
            if counts[f["caption"]] > 1:
                folder = Path(f["src"]).parent.name
                if folder:
                    f["caption"] = f"{f['caption']} ({folder})"
        done.add(tid)
        if figs:
            manifest[tid] = figs
            print(f"  [{n}/{len(task_ids)}] {tid}: {len(figs)} figure(s), "
                  f"{time.time() - t0:.1f}s — {', '.join(f['caption'] for f in figs)}", flush=True)
        elif candidates:
            print(f"  [{n}/{len(task_ids)}] {tid}: {len(candidates)} candidate(s), "
                  f"none usable, {time.time() - t0:.1f}s", flush=True)
        index_path.write_text(json.dumps({**manifest, "__done__": sorted(done)},
                                         indent=2, sort_keys=True))

    index_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    total = sum(p.stat().st_size for p in OUT.iterdir() if p.is_file())
    n_fig = sum(len(v) for v in manifest.values())
    print(f"\n{len(manifest)}/{len(task_ids)} ALE tasks illustrated, {n_fig} figures, "
          f"{total / 1e6:.2f} MB -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
