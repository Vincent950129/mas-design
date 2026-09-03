#!/usr/bin/env python3
"""Checks for the Evaluate tab's two execution environments.

The tab now offers a choice: the hosted service, which works today, and running
locally, which does not yet. That split is only useful if it stays honest, so
these checks pin the claims that would mislead someone if they drifted -- the
"coming soon" marker on the runner, the row and config counts quoted for each
dataset, and the column names in the snippet, all read back from the Hub rather
than trusted. Also verifies the switcher itself, since a panel that fails to
hide would show both environments' instructions at once.

Needs network for the Hub checks; pass --offline to skip them.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8777/evoharness/index.html"

# What the page claims, and therefore what the Hub has to agree with.
CLAIMS = {
    "ZixuanKe/evovling_tools": {"rows": 4615, "configs": 49},
    "ZixuanKe/evovling_skills": {"rows": 3243, "configs": 31},
    "ZixuanKe/evovling_agents": {"rows": 3327, "configs": 32},
}
COLLECTION = "https://huggingface.co/collections/ZixuanKe/evoharnessbench"
# Where a key comes from, and the env var the SDK actually reads for it
# (``EvalClient.__init__`` in simple_agentic_evals/client.py).
LOGIN = "https://mas-orchestra.salesforceresearch.ai/mas_r1/demo/"
KEY_ENV = "EVAL_SERVICE_API_KEY"
# The three tutorials, shallowest first, with the code-cell count the page quotes and the
# notebook's own filename -- both read back off Colab rather than trusted.
TUTORIALS = [
    ("1xJEpRf_s0zG-M9QynS3MBk7Nkr-xB11r", "Quick start", 6,
     "evolve_eval_colab_tutorial_quick_start.ipynb"),
    ("1vrcGelN9GmwiCK25c6qZNG3Z0sHWxE5o", "More details", 8,
     "evolve_eval_colab_tutorial_quick_start_detail.ipynb"),
    ("1mYQEDCVFStXMRWYI2hpEGBXwyRx1NSFj", "Full detail", 25,
     "evolve_eval_colab_tutorial_full.ipynb"),
]
# Columns the snippet reads; a rename upstream would leave dead code on the page.
EOG_COLS = ["user_prompt", "oracle_tools", "cummulative_tools", "verifiers",
            "gym_servers_config"]
ALE_COLS = ["task_prompt", "input_files", "agent_must_do"]

fails: list[str] = []
checks = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global checks
    checks += 1
    print(f"  {'ok  ' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        fails.append(label + (f": {detail}" if detail else ""))


def hub(path: str) -> dict:
    req = urllib.request.Request(f"https://huggingface.co/{path}",
                                 headers={"User-Agent": "evoharness-verify"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def server_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "evoharness-verify"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)


def check_hub() -> None:
    print("\nHugging Face")
    for ds, want in CLAIMS.items():
        try:
            meta = hub(f"api/datasets/{ds}")
        except urllib.error.HTTPError as e:
            check(False, f"{ds} resolves", f"HTTP {e.code}")
            continue
        check(not meta.get("private"), f"{ds} is public")
        check(any(t == "license:apache-2.0" for t in meta.get("tags", [])),
              f"{ds} is Apache-2.0", str([t for t in meta.get("tags", []) if "license" in t]))

        size = server_json(
            "https://datasets-server.huggingface.co/size?dataset=" + ds.replace("/", "%2F"))
        rows = size["size"]["dataset"]["num_rows"]
        check(rows == want["rows"], f"{ds} row count matches the page",
              f"page says {want['rows']}, Hub says {rows}")

        splits = server_json(
            "https://datasets-server.huggingface.co/splits?dataset=" + ds.replace("/", "%2F"))
        cfgs = {s["config"] for s in splits["splits"]}
        check(len(cfgs) == want["configs"], f"{ds} config count matches the page",
              f"page says {want['configs']}, Hub says {len(cfgs)}")
        # The page tells the reader configs are {domain}_v{stage} with train/test.
        check(all(re.fullmatch(r".+_v\d+", c) for c in cfgs),
              f"{ds} configs are all {{domain}}_v{{stage}}",
              str(sorted(c for c in cfgs if not re.fullmatch(r".+_v\d+", c))[:4]))
        check({s["split"] for s in splits["splits"]} == {"train", "test"},
              f"{ds} splits are train/test",
              str(sorted({s["split"] for s in splits["splits"]})))

    # The snippet names real columns, in the config the snippet actually loads.
    for cfg, cols, label in (("hr_v1", EOG_COLS, "EOG"), ("ale_v1", ALE_COLS, "ALE")):
        rows = server_json(
            "https://datasets-server.huggingface.co/first-rows"
            f"?dataset=ZixuanKe%2Fevovling_tools&config={cfg}&split=test")
        have = {f["name"] for f in rows["features"]}
        missing = [c for c in cols if c not in have]
        check(not missing, f"{label} columns quoted on the page exist in {cfg}", str(missing))

    try:
        hub("api/collections/ZixuanKe/evoharnessbench")
        check(True, "the linked collection resolves")
    except urllib.error.HTTPError as e:
        check(False, "the linked collection resolves", f"HTTP {e.code}")


def check_colab() -> None:
    """Load each notebook signed out, the way a reader arrives at it.

    Colab answers 200 for any document id and resolves the notebook client-side, so an
    HTTP check proves nothing: an unshared or missing notebook renders the Google sign-in
    page instead. Loading it is the only way to tell, and it also lets the code-cell counts
    quoted on the page be counted rather than asserted.
    """
    from playwright.sync_api import sync_playwright

    print("\nColab tutorials")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for doc, title, cells, fname in TUTORIALS:
            pg = b.new_page(viewport={"width": 1400, "height": 1000})
            try:
                pg.goto(f"https://colab.research.google.com/drive/{doc}",
                        wait_until="domcontentloaded", timeout=60000)
                pg.wait_for_function("() => document.title.includes('.ipynb')", timeout=45000)
                pg.wait_for_timeout(3500)
                got = pg.title()
                check(got.startswith(fname), f"{title} opens without a Google login", got)
                n = pg.eval_on_selector_all(".code-cell, .cell.code", "ns => ns.length")
                check(n == cells, f"{title} really has the {cells} code cells the page quotes",
                      f"counted {n}")
            except Exception as e:  # noqa: BLE001 - a hang here is a finding, not a crash
                check(False, f"{title} opens without a Google login",
                      f"{type(e).__name__}: {str(e)[:80]}")
            pg.close()
        b.close()


def check_page() -> None:
    from playwright.sync_api import sync_playwright

    print("\nRendered page")
    errs: list[str] = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 1200})
        pg.on("console", lambda m: m.type == "error"
              and "404" not in m.text and errs.append(m.text))
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE, wait_until="networkidle")
        pg.click('.pv-tab[data-pv="evaluate"]')
        pg.wait_for_timeout(800)

        def shown() -> list[str]:
            return pg.eval_on_selector_all(
                ".ev-panel", "ns => ns.filter(p => p.offsetHeight > 0).map(p => p.dataset.evPanel)")

        check(len(pg.query_selector_all(".ev-tab")) == 2, "two environments are offered",
              str(len(pg.query_selector_all(".ev-tab"))))
        check(shown() == ["api"], "the hosted service is the default", str(shown()))
        # The quickstart tabs belong to the hosted panel only.
        check(pg.eval_on_selector(".sv-tabs", "n => n.offsetHeight > 0"),
              "quickstart tabs show under the hosted panel")

        # The chooser has to read as a control, not as one more white card in a section
        # made of white cards -- that was the whole complaint about the first cut. Measured
        # off rendered pixels, since the panel is a gradient and the unpicked option is
        # translucent over it, neither of which computed styles report usefully.
        def lum(sel: str) -> float:
            import io

            import numpy as np
            from PIL import Image

            px = np.asarray(Image.open(io.BytesIO(
                pg.locator(sel).first.screenshot())).convert("RGB"), dtype=float)
            return float((px * [0.2126, 0.7152, 0.0722]).sum(axis=2).mean())

        seg_l, card_l = lum(".ev-choose"), lum(".sv-card")
        check(card_l - seg_l > 90, "the chooser stands well clear of the cards below it",
              f"chooser {seg_l:.0f} vs card {card_l:.0f}")
        on_l, off_l = lum(".ev-tab.is-active"), lum(".ev-tab:not(.is-active)")
        check(on_l - off_l > 90, "picked and unpicked options are far apart",
              f"active {on_l:.0f} vs inactive {off_l:.0f}")
        # White-on-dark for the option that is not selected, or its text disappears.
        ink = ("n => { const c = getComputedStyle(n).color.match(/[\\d.]+/g).map(Number);"
               " return 0.2126*c[0] + 0.7152*c[1] + 0.0722*c[2]; }")
        check(pg.eval_on_selector(".ev-tab:not(.is-active) .ev-tt", ink) > 200,
              "the unpicked option's title stays legible on the dark panel",
              f"{pg.eval_on_selector('.ev-tab:not(.is-active) .ev-tt', ink):.0f}")

        # Getting a key is step one, and it says where the key comes from.
        first = pg.eval_on_selector(".sv-tab", "n => [n.dataset.sv, n.innerText.trim(),"
                                               " n.classList.contains('is-active')]")
        check(first[0] == "key" and first[2], "the API key is the first quickstart step", str(first))
        check("API key" in first[1], "the first step is labelled for the key", first[1])
        key = '.sv-panel[data-sv-panel="key"] '
        ktx = pg.eval_on_selector(key, "n => n.innerText")
        check("MyAuthtoken" in ktx, "the key step names MyAuthtoken")
        check(KEY_ENV in ktx, f"the key step names {KEY_ENV}")
        klinks = pg.eval_on_selector_all(key + "a", "ns => ns.map(n => n.href)")
        check(LOGIN in klinks, "the key step links the login page", str(klinks))
        check(all(pg.eval_on_selector_all(
            key + "a", "ns => ns.map(n => n.target === '_blank' && n.rel.includes('noopener'))")),
            "the key step's links open safely")
        check(pg.eval_on_selector_all(key + ".sv-code code .t-k", "ns => ns.length") > 0,
              "the key step's snippets are syntax highlighted")

        # The knobs are a recap, so they have to land after the walkthrough that motivates
        # them -- reading them before the reader knows how a run works is the old bug.
        order = pg.evaluate(
            """() => {
                 const y = s => document.querySelector(s).getBoundingClientRect().top;
                 return {flow: y('.sv-flow'), tabs: y('.sv-tabs'), knobs: y('.sv-knobs'),
                         tuts: y('.sv-tuts')};
               }""")
        check(order["flow"] < order["tabs"] < order["knobs"] < order["tuts"],
              "how a run works comes first, then the walkthrough, then the recap, then Colab",
              str({k: round(v) for k, v in order.items()}))

        # Three depths, shallowest first, each to its own notebook.
        cards = pg.eval_on_selector_all(
            ".sv-tut", "ns => ns.map(n => [n.href, n.innerText.replace(/\\s+/g,' ')])")
        check(len(cards) == 3, "three tutorial depths are offered", str(len(cards)))
        for i, (doc, title, cells, _) in enumerate(TUTORIALS):
            href, txt = cards[i] if i < len(cards) else ("", "")
            check(doc in href, f"tutorial {i + 1} points at the {title.lower()} notebook", href)
            check(title in txt, f"tutorial {i + 1} is labelled {title}", txt[:60])
            check(f"{cells} code cells" in txt, f"tutorial {i + 1} quotes its size", txt[:90])
        check(all(pg.eval_on_selector_all(
            ".sv-tut", "ns => ns.map(n => n.target === '_blank' && n.rel.includes('noopener'))")),
            "the tutorials open safely")
        # innerText, so the badge's uppercasing shows up here too.
        check(pg.eval_on_selector(".sv-tut.is-first",
                                  "n => /start here/i.test(n.innerText)"),
              "the shallowest one is marked as the place to start")

        pg.click('.ev-tab[data-ev="local"]')
        pg.wait_for_timeout(400)
        check(shown() == ["local"], "switching hides the hosted panel entirely", str(shown()))
        check(not pg.eval_on_selector(".sv-tabs", "n => n.offsetHeight > 0"),
              "the hosted quickstart is not left visible under the local panel")

        local = '.ev-panel[data-ev-panel="local"] '
        hrefs = pg.eval_on_selector_all(local + 'a[href*="huggingface"]',
                                        "ns => ns.map(n => n.getAttribute('href'))")
        for ds in CLAIMS:
            check(f"https://huggingface.co/datasets/{ds}" in hrefs, f"{ds} is linked")
        check(COLLECTION in hrefs, "the collection is linked")
        check(all(pg.eval_on_selector_all(
            local + "a", "ns => ns.map(n => n.target === '_blank' && n.rel.includes('noopener'))")),
            "outbound links open safely")

        txt = pg.eval_on_selector(local, "n => n.innerText")
        check("Coming soon" in txt or "COMING SOON" in txt.upper(),
              "the runner is marked coming soon")
        # The page must not promise a local grade it cannot deliver.
        check(re.search(r"local\s+grade\s+is not something you can produce", txt) is not None,
              "the page says a local grade is not possible yet")
        for col in EOG_COLS:
            check(col in txt, f"the snippet shows {col}")

        # Highlighting and copy come from the same module; both must reach this panel.
        check(pg.eval_on_selector_all(local + ".sv-code code .t-k", "ns => ns.length") > 0,
              "the local snippet is syntax highlighted")
        check(len(pg.query_selector_all(local + ".sv-copy")) > 0, "the local snippet is copyable")

        pg.click(".ev-jump")
        pg.wait_for_timeout(400)
        check(shown() == ["api"], "the in-panel link switches back to the hosted path", str(shown()))

        # Narrow: both grids have to collapse or the cards overflow the container.
        pg.set_viewport_size({"width": 420, "height": 1000})
        pg.click('.ev-tab[data-ev="local"]')
        pg.wait_for_timeout(500)
        over = pg.eval_on_selector_all(
            ".ev-seg, .ev-ds, .ev-dcard, .ev-soon",
            "ns => ns.filter(n => n.scrollWidth > n.parentElement.clientWidth + 1)"
            ".map(n => n.className)")
        check(not over, "nothing overflows at 420px", str(over))
        pg.screenshot(path=str(ROOT / "tools/proofs/eval-local-mobile.png"), full_page=False)

        # The hosted panel has grids of its own, including the three tutorials.
        pg.click('.ev-tab[data-ev="api"]')
        pg.wait_for_timeout(400)
        over = pg.eval_on_selector_all(
            ".sv-tuts, .sv-tut, .sv-knobs, .sv-knob, .sv-cards, .sv-cta",
            "ns => ns.filter(n => n.scrollWidth > n.parentElement.clientWidth + 1)"
            ".map(n => n.className)")
        check(not over, "the hosted panel's own grids hold up at 420px", str(over))
        check(pg.eval_on_selector_all(
            ".sv-tuts", "ns => ns.map(n => getComputedStyle(n).gridTemplateColumns.split(' ').length)"
        ) == [1], "the three tutorials stack rather than squeeze")
        b.close()

    check(not errs, "no console errors", str(errs[:3]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="skip the Hugging Face checks")
    args = ap.parse_args()

    syn = subprocess.run(["node", "--check", str(ROOT / "app.js")],
                         capture_output=True, text=True)
    print("Syntax")
    check(syn.returncode == 0, "app.js parses", syn.stderr.strip()[:200])

    check_page()
    if not args.offline:
        check_hub()
        check_colab()

    print(f"\n{checks - len(fails)}/{checks} checks passed")
    if fails:
        print(f"\n{len(fails)} FAILURE(S):")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
