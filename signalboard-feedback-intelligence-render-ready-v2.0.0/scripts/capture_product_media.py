"""Capture reviewer-facing preview images and an animated README walkthrough."""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src" / "feedback_intelligence_engine" / "web"
DOCS = ROOT / "docs"


def annotated_frame(source: Path, caption: str) -> Image.Image:
    image = Image.open(source).convert("RGB")
    target_width = 1040
    height = round(image.height * target_width / image.width)
    image = image.resize((target_width, height), Image.Resampling.LANCZOS)
    banner = 72
    canvas = Image.new("RGB", (target_width, height + banner), "#171815")
    canvas.paste(image, (0, banner))
    draw = ImageDraw.Draw(canvas)
    draw.text((30, 23), caption, fill="#f7f5ed", stroke_width=0)
    return canvas


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    with sync_playwright() as runner:
        executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
        if not executable and Path("/usr/bin/chromium").exists():
            executable = "/usr/bin/chromium"
        browser = runner.chromium.launch(
            headless=True,
            executable_path=executable,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1480, "height": 1000}, device_scale_factor=1)
        page.route(
            "https://fonts.googleapis.com/**",
            lambda route: route.fulfill(status=200, content_type="text/css", body=""),
        )
        page.route("https://fonts.gstatic.com/**", lambda route: route.fulfill(status=204))
        html = (WEB / "index.html").read_text(encoding="utf-8")
        html = html.replace(
            '<link rel="stylesheet" href="/app/styles.css" />',
            f"<style>{(WEB / 'styles.css').read_text(encoding='utf-8')}</style>",
        )
        html = html.replace(
            '<script type="module" src="/app/app.js"></script>',
            '<script>window.__SIGNALBOARD_PREVIEW__=true;</script>',
        )
        html = html.replace("<head>", '<head><base href="https://signalboard.preview/">', 1)
        page.set_content(html, wait_until="domcontentloaded")
        page.add_script_tag(content=(WEB / "app.js").read_text(encoding="utf-8"), type="module")
        page.get_by_role("button", name="Provider settings").wait_for()
        page.wait_for_timeout(900)

        captures: list[tuple[str, str]] = []
        overview = DOCS / "premium-overview.png"
        page.screenshot(path=str(overview), full_page=True)
        captures.append((overview.name, "01 · Evidence-grounded signal overview"))

        page.get_by_role("button", name="Themes").click()
        page.wait_for_timeout(650)
        themes = DOCS / "premium-themes.png"
        page.screenshot(path=str(themes), full_page=True)
        captures.append((themes.name, "02 · Three-pane human review workspace"))

        page.get_by_role("button", name="History").click()
        page.wait_for_timeout(650)
        history = DOCS / "premium-history.png"
        page.screenshot(path=str(history), full_page=True)
        captures.append((history.name, "03 · Versioned product memory and historical context"))

        page.get_by_role("button", name="Provider settings").click()
        page.wait_for_timeout(450)
        provider = DOCS / "premium-provider.png"
        page.screenshot(path=str(provider), full_page=True)
        captures.append((provider.name, "04 · Live AI provider verification"))
        browser.close()

    frames = [annotated_frame(DOCS / filename, caption) for filename, caption in captures]
    gif_path = DOCS / "signalboard-demo.gif"
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=[2100, 2300, 2300, 2300],
        loop=0,
        optimize=True,
    )
    print(gif_path)


if __name__ == "__main__":
    main()
