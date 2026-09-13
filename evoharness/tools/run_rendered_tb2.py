#!/usr/bin/env python3
"""Execute the exact TB2 blocks extracted from the rendered construction page."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess

from playwright.sync_api import sync_playwright


ORDER = ["setup", "annotate", "release", "package", "tools", "skills", "agents", "terminal"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--page", default="http://127.0.0.1:8777/evoharness/index.html")
    parser.add_argument("--service", default="http://127.0.0.1:8077")
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.workdir.exists():
        raise SystemExit(f"refusing to overwrite {args.workdir}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(args.page, wait_until="load")
        page.click('.pv-tab[data-pv="construction"]')
        rendered = page.evaluate("""() => [...document.querySelectorAll(
          '[data-pv-view="construction"] [data-tb2-executable]')].map((pre) => ({
            name: pre.dataset.tb2Executable,
            source: pre.querySelector('code').textContent
          }))""")
        browser.close()

    names = [item["name"] for item in rendered]
    if names != ORDER:
        raise SystemExit(f"rendered block order drifted: {names}")
    script = "\n\n".join(item["source"] for item in rendered) + "\n"
    if "/export/" in script or "references/tb2/v1/source" in script:
        raise SystemExit("rendered script contains a private path or downloaded builder")

    args.report_dir.mkdir(parents=True, exist_ok=True)
    (args.report_dir / "rendered-blocks.sh").write_text(script, encoding="utf-8")
    env = dict(os.environ, EVOLVE_TB2_SERVICE=args.service,
               EVOLVE_TB2_WORKDIR=str(args.workdir.resolve()))
    result = subprocess.run(["bash"], input=script, text=True, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (args.report_dir / "run.log").write_text(result.stdout, encoding="utf-8")
    print(result.stdout, end="")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
