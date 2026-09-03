"""Rebuild static/cases.json from the benchmark's per-task record.

    python build_cases.py [path/to/harness_task_cells.tsv]

The observability app serves that 68 MB table through a FastAPI backend. This page is
static, so the same cases ship as one file: capability names, capability lists, prompts
and check lists repeat heavily across cells, and interning them into shared dictionaries
is what brings the whole table down to something a browser can download (~2.3 MB, ~0.5 MB
over the wire once gzipped). Cases arrive pre-sorted by disagreement, which is the order
the page opens on. Nothing is computed here that the table does not already state.

Field offsets in the emitted tuples are mirrored by `C` and `A` in app.js; changing the
order here means changing them there.
"""
import csv
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SRC = Path("/export/xgen-finance/meta_agent/mas_evovle_enviroment"
                   "/analysis/tables/harness_task_cells.tsv")
OUT = HERE / "static" / "cases.json"

csv.field_size_limit(2**31 - 1)


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


def build(src: Path) -> dict:
    tracks, datasets, cells = Pool(), Pool(), Pool()
    systems, sources, notes = Pool(), Pool(), Pool()
    taskids, queries, checks, names, lists = Pool(), Pool(), Pool(), Pool(), Pool()

    def lst(s):
        return lists(tuple(names(x) for x in s.split(",") if x))

    def num(s):
        return round(float(s), 4) if s not in ("", None) else None

    cases, order = {}, []
    with src.open(newline="") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            key = (r["track"], r["dataset"], r["task_id"],
                   r["train_stage"], r["task_release"])
            c = cases.get(key)
            if c is None:
                c = cases[key] = {
                    "head": [
                        tracks(r["track"]), datasets(r["dataset"]),
                        taskids(r["task_id"]), int(r["train_stage"][1:]),
                        int(r["task_release"][1:]), int(r["test_stage"][1:]),
                        cells(r["cell_type"]), queries(r["query"]),
                        checks(r["groundtruth"]), int(r["n_groundtruth"] or 0),
                        lst(r["oracle_harness"]), lst(r["oracle_gradeable"]),
                        lst(r["new_since_task_release"]),
                        lst(r["oracle_new_at_task_release"]),
                    ],
                    "attempts": [],
                    # The "reached a newer one" filter is a property of the case.
                    "used_new": 0,
                }
                order.append(key)
            if r["used_new"]:
                c["used_new"] = 1
            c["attempts"].append([
                systems(r["system"]), num(r["score_mean"]),
                int(r["n_pass"] or 0), int(r["runs"] or 0),
                lst(r["harness_used"]), sources(r["harness_used_source"]),
                lst(r["oracle_missed"]), lst(r["oracle_missed_gradeable"]),
                lst(r["new_since_task_release_used"]), lst(r["harness_in_testing"]),
                num(r["calls_mean"]), num(r["calls_counted_mean"]),
                num(r["spawns_counted_mean"]),
                int(round(float(r["tokens_mean"] or 0) / 1000)),
                notes(r["notes"]),
            ])

    rows = []
    for key in order:
        c = cases[key]
        c["attempts"].sort(key=lambda a: -(a[1] or 0))
        rows.append(c["head"] + [c["used_new"], c["attempts"]])

    def spread(row):
        scores = [a[1] or 0 for a in row[-1]]
        return max(scores) - min(scores) if scores else 0.0

    rows.sort(key=lambda r: (-spread(r), r[0], r[1], taskids.items[r[2]]))

    return {
        "tracks": tracks.items, "datasets": datasets.items,
        "cellTypes": cells.items, "systems": systems.items,
        "sources": sources.items, "notes": notes.items,
        "taskIds": taskids.items, "queries": queries.items,
        "checks": checks.items, "names": names.items,
        "lists": [list(t) for t in lists.items], "cases": rows,
    }


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    if not src.exists():
        print(f"not found: {src}", file=sys.stderr)
        return 1
    bundle = build(src)
    blob = json.dumps(bundle, ensure_ascii=False, separators=(",", ":"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(blob, encoding="utf-8")
    print(f"{len(bundle['cases'])} cases, "
          f"{sum(len(c[-1]) for c in bundle['cases'])} attempts")
    print(f"{OUT} — {OUT.stat().st_size / 1e6:.2f} MB "
          f"({len(gzip.compress(blob.encode())) / 1e3:.0f} KB gzipped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
