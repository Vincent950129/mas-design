"""Check that the Tasks tab actually renders its figures, and shoot proofs.

    python tools/verify_figures.py [base_url]

Walks the gallery the way a reader does — cards, an EOG detail, an ALE detail,
the lightbox, a video figure — and fails loudly on a console error, a 404 for
any figure, or an <img> that resolved to nothing. Screenshots land in
`tools/proofs/` for eyeballing.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8021"
PROOFS = Path(__file__).resolve().parent / "proofs"
FAILS: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{f' — {detail}' if detail else ''}")
    if not ok:
        FAILS.append(f"{label}{f': {detail}' if detail else ''}")


def broken_images(page) -> list[str]:
    """Figure images the browser tried and failed to decode.

    Scoped to the gallery: the page's author portraits are not in this
    directory and 404 regardless of anything here.
    """
    return page.eval_on_selector_all(
        ".tg-shot img, .tg-fig img, .tg-lmedia",
        """els => els.filter(e => e.currentSrc && e.complete && e.naturalWidth === 0)
                      .map(e => e.currentSrc)""",
    )


def main() -> int:
    PROOFS.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 950}, device_scale_factor=2)

        errors: list[str] = []
        bad_requests: list[str] = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("requestfailed", lambda r: bad_requests.append(r.url))
        page.on("response", lambda r: bad_requests.append(f"{r.status} {r.url}")
                if r.status >= 400 else None)

        page.goto(f"{BASE}/index.html#tasks", wait_until="networkidle")
        page.wait_for_selector(".tg-card", timeout=30_000)
        page.wait_for_timeout(1800)  # let lazy thumbnails settle

        cards = page.locator(".tg-card").count()
        shots = page.locator(".tg-card.has-shot .tg-shot img").count()
        check("cards rendered", cards > 0, f"{cards} cards")
        check("cards carry a figure", shots > 0, f"{shots}/{cards} with a thumbnail")
        page.screenshot(path=str(PROOFS / "01-grid.png"))

        # --- the default sort, on a pristine load ------------------------- #
        # The select and the module's own default have to agree: the control is
        # painted from the markup, so a mismatch shows the wrong label over a
        # correctly sorted grid (or the reverse) and neither side complains.
        check("sort control defaults to illustrated first",
              page.input_value('[data-f="sort"]') == "fig",
              page.input_value('[data-f="sort"]'))
        opening = page.eval_on_selector_all(
            ".tg-card", "els => els.slice(0, 24).map(e => e.classList.contains('has-shot'))")
        check("the grid opens on illustrated tasks", all(opening),
              f"first 24: {sum(opening)} illustrated")

        check("no broken card thumbnails", not broken_images(page), str(broken_images(page))[:200])

        # --- the "illustrated only" filter -------------------------------- #
        page.select_option('[data-f="fig"]', "1")
        page.wait_for_timeout(1600)
        n_cards = page.locator(".tg-card").count()
        n_shots = page.locator(".tg-card.has-shot").count()
        total = page.locator("[data-tg-count]").inner_text()
        check("illustrated filter keeps only cards with figures",
              n_cards > 0 and n_cards == n_shots, f"{n_shots}/{n_cards} — {total}")
        page.screenshot(path=str(PROOFS / "01b-illustrated.png"))
        page.select_option('[data-f="fig"]', "")
        page.wait_for_timeout(600)

        # --- an EOG task: one app view of its own environment ------------- #
        # Pinned to a single-gym domain rather than taking whatever the grid
        # happens to lead with, since a hybrid task legitimately shows two.
        page.select_option('[data-f="env"]', "eog")
        page.select_option('[data-f="domain"]', "calendar")
        page.wait_for_timeout(500)
        page.locator(".tg-card").first.click()
        page.wait_for_selector(".tg-detail .tg-figs", timeout=15_000)
        page.wait_for_timeout(1200)
        n = page.locator(".tg-detail .tg-fig").count()
        head = page.locator(".tg-detail .tg-h4").first.inner_text()
        check("single-gym EOG detail shows exactly one figure", n == 1,
              f"{n} figures, heading {head!r}")
        caps = page.locator(".tg-detail .tg-fig figcaption").all_inner_texts()
        check("no relational/graph view is shown",
              not any("grader" in c.lower() or "graph" in c.lower() for c in caps),
              "; ".join(caps)[:160])
        page.screenshot(path=str(PROOFS / "02-eog-detail.png"))

        # --- the lightbox ------------------------------------------------- #
        page.locator(".tg-detail .tg-figbtn").first.click()
        page.wait_for_selector(".tg-lbox[open] .tg-lmedia", timeout=15_000)
        page.wait_for_timeout(900)
        big = page.eval_on_selector(".tg-lbox .tg-lmedia",
                                    "e => ({tag: e.tagName, w: e.naturalWidth || e.videoWidth})")
        check("lightbox opens full size", big["w"] > 600, str(big))
        page.screenshot(path=str(PROOFS / "03-lightbox.png"))
        page.locator("[data-tg-lclose]").click()
        page.wait_for_timeout(300)
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

        # --- tasks in one domain must not all share one picture ----------- #
        # This is the whole point of keying figures on the seeded environment
        # rather than on the domain, so it gets a real check.
        page.select_option('[data-f="domain"]', "calendar")
        page.select_option('[data-f="fig"]', "1")
        page.wait_for_timeout(1200)
        srcs = page.eval_on_selector_all(
            ".tg-card.has-shot .tg-shot img",
            "els => els.map(e => e.getAttribute('src'))")
        uniq = len(set(srcs))
        check("calendar tasks show more than one environment", uniq > 1,
              f"{uniq} distinct pictures over {len(srcs)} cards")
        page.screenshot(path=str(PROOFS / "04-per-task-envs.png"))
        page.select_option('[data-f="fig"]', "")
        page.wait_for_timeout(400)

        # --- a hybrid task: one figure per gym it touches ------------------ #
        page.select_option('[data-f="domain"]', "hybrid")
        page.wait_for_timeout(600)
        if page.locator(".tg-card").count():
            page.locator(".tg-card").first.click()
            page.wait_for_selector(".tg-detail .tg-figs", timeout=15_000)
            page.wait_for_timeout(1000)
            n = page.locator(".tg-detail .tg-fig").count()
            head = page.locator(".tg-detail .tg-h4").first.inner_text()
            check("hybrid detail shows one figure per gym", n >= 2,
                  f"{n} figures, heading {head!r}")
            page.screenshot(path=str(PROOFS / "04b-hybrid-detail.png"))
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
        page.select_option('[data-f="domain"]', "all")
        page.wait_for_timeout(400)

        # --- an ALE task with staged artifacts ---------------------------- #
        page.select_option('[data-f="env"]', "ale")
        page.wait_for_timeout(600)
        page.fill('[data-f="q"]', "bridge")
        page.wait_for_timeout(900)
        check("ALE search finds the bridge task", page.locator(".tg-card").count() > 0)
        page.locator(".tg-card").first.click()
        page.wait_for_selector(".tg-detail .tg-figs", timeout=15_000)
        page.wait_for_timeout(1200)
        n = page.locator(".tg-detail .tg-fig").count()
        head = page.locator(".tg-detail .tg-h4").first.inner_text()
        check("ALE detail shows staged artifacts", n >= 1, f"{n} figures, heading {head!r}")
        page.screenshot(path=str(PROOFS / "05-ale-detail.png"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

        # --- an ALE video figure ------------------------------------------ #
        page.fill('[data-f="q"]', "chroma")
        page.wait_for_timeout(900)
        if page.locator(".tg-card").count():
            page.locator(".tg-card").first.click()
            page.wait_for_selector(".tg-detail .tg-figs", timeout=15_000)
            page.wait_for_timeout(800)
            tagged = page.locator(".tg-detail .tg-figtag").count()
            check("video figure is labelled", tagged >= 1, f"{tagged} video tag(s)")
            page.locator(".tg-detail .tg-figbtn").first.click()
            page.wait_for_selector(".tg-lbox[open] video", timeout=15_000)
            page.wait_for_timeout(2200)
            v = page.eval_on_selector("video", """e => ({
                w: e.videoWidth, h: e.videoHeight, t: e.currentTime, dur: e.duration })""")
            check("clip decodes and plays", v["w"] > 0 and v["t"] > 0, str(v))
            page.screenshot(path=str(PROOFS / "06-video-lightbox.png"))
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
            page.keyboard.press("Escape")

        # --- the "illustrated first" sort --------------------------------- #
        page.keyboard.press("Escape")
        page.fill('[data-f="q"]', "")
        page.select_option('[data-f="env"]', "")
        page.select_option('[data-f="fig"]', "")
        page.select_option('[data-f="sort"]', "fig")
        page.wait_for_timeout(1800)
        flags = page.eval_on_selector_all(
            ".tg-card", "els => els.map(e => e.classList.contains('has-shot'))")
        lead = 0
        while lead < len(flags) and flags[lead]:
            lead += 1
        check("illustrated-first sort front-loads the figures",
              lead > 0 and not any(flags[lead:]),
              f"{lead} illustrated then {sum(flags[lead:])} stragglers of {len(flags)}")
        page.screenshot(path=str(PROOFS / "07-sort-illustrated.png"))

        page.select_option('[data-f="sort"]', "domain")
        page.wait_for_timeout(1200)
        first_default = page.eval_on_selector_all(
            ".tg-card", "els => els.slice(0, 12).map(e => e.classList.contains('has-shot'))")
        check("the domain sort still groups by domain rather than by figure",
              not all(first_default), f"first 12: {sum(first_default)} illustrated")

        page.wait_for_timeout(600)
        check("no broken figures anywhere", not broken_images(page), str(broken_images(page))[:200])
        # /profile/* are the page's author portraits, absent from this checkout.
        figure_404s = [b for b in bad_requests
                       if "/static/images/" in b or "tasks.json" in b]
        check("no failed figure requests", not figure_404s, "; ".join(figure_404s[:4]))
        other_404s = [b for b in bad_requests if "/profile/" not in b and "favicon" not in b]
        if other_404s:
            print(f"  note  {len(other_404s)} unrelated failed request(s): {other_404s[:2]}")
        script_errors = [e for e in errors if "status of 404" not in e]
        check("no console errors", not script_errors, "; ".join(script_errors[:3])[:300])

        browser.close()

    print(f"\nproofs -> {PROOFS}")
    if FAILS:
        print(f"\n{len(FAILS)} FAILURE(S):")
        for f in FAILS:
            print(f"  - {f}")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
