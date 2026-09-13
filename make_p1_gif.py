#!/usr/bin/env python3
"""Capture the Page 1 animation from index.html as a looping GIF."""

from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "index.html"
OUTPUT = ROOT / "p1-animation.gif"

WIDTH = 968
# Match P1's native 942:960 viewBox so its own animated camera remains intact.
HEIGHT = 987
FPS = 10
LOOP_SECONDS = 18.6
FRAME_COUNT = round(FPS * LOOP_SECONDS)

CAPTURE_CSS = f"""
html, body {{
  width: {WIDTH}px !important;
  height: {HEIGHT}px !important;
  margin: 0 !important;
  overflow: hidden !important;
  background: #fbfaf8 !important;
}}
.view-toggle, #page2, #page1 .col--text, #page1 .scroll-cue,
#page1 > .triggers {{
  display: none !important;
}}
#page1 {{
  position: fixed !important;
  inset: 0 !important;
  width: {WIDTH}px !important;
  height: {HEIGHT}px !important;
  opacity: 1 !important;
}}
#page1 .page__pin {{
  position: absolute !important;
  inset: 0 !important;
  display: block !important;
  width: 100% !important;
  height: 100% !important;
  max-width: none !important;
  margin: 0 !important;
  padding: 0 !important;
}}
#page1 .col--viz {{
  position: absolute !important;
  inset: 0 !important;
  display: block !important;
  width: 100% !important;
  height: 100% !important;
}}
#loop {{
  display: block !important;
  width: 100% !important;
  height: 100% !important;
  max-height: none !important;
}}
"""


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="p1-gif-") as temp_name:
        frames = Path(temp_name)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={"width": WIDTH, "height": HEIGHT},
                device_scale_factor=1,
            )
            page.goto(SOURCE.as_uri(), wait_until="domcontentloaded")
            page.wait_for_function("document.fonts.status === 'loaded'")
            page.add_style_tag(content=CAPTURE_CSS)
            # Start at a normal loop boundary, rather than the page's one-off initial
            # reveal. First wait for stage 7, then for its reset back to stage 1.
            page.wait_for_function(
                "document.querySelector('.stage-item[data-stage=\"7\"]')"
                ".classList.contains('is-active')",
                timeout=12_000,
            )
            page.wait_for_function(
                "document.querySelector('.stage-item[data-stage=\"1\"]')"
                ".classList.contains('is-active')",
                timeout=16_000,
            )

            started = time.monotonic()
            for frame in range(FRAME_COUNT):
                target = started + frame / FPS
                remaining = target - time.monotonic()
                if remaining > 0:
                    time.sleep(remaining)
                page.screenshot(path=frames / f"frame-{frame:04d}.png")

            browser.close()

        palette = frames / "palette.png"
        pattern = str(frames / "frame-%04d.png")
        run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-framerate",
                str(FPS),
                "-i",
                pattern,
                "-vf",
                "palettegen=max_colors=160:stats_mode=diff",
                str(palette),
            ]
        )
        run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-framerate",
                str(FPS),
                "-i",
                pattern,
                "-i",
                str(palette),
                "-lavfi",
                "paletteuse=dither=sierra2_4a:diff_mode=rectangle",
                "-loop",
                "0",
                str(OUTPUT),
            ]
        )

    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
