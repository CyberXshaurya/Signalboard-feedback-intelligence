from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Route, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src" / "feedback_intelligence_engine" / "web"


def theme_card(theme_id: str, title: str, count: int = 3) -> dict:
    return {
        "theme": {
            "id": theme_id,
            "analysis_run_id": "preview-run",
            "title": title,
            "summary": f"Summary for {title}",
            "problem_statement": f"Users cannot reliably resolve {title.lower()}.",
            "pattern_type": "repeated",
            "confidence": 0.82,
            "uncertainty_reason": None,
            "status": "needs_review",
            "historical_relationship": "new",
            "historical_theme_id": None,
            "historical_similarity_score": None,
            "merged_into_theme_id": None,
            "approved_by": None,
            "approved_at": None,
            "rejected_at": None,
            "rejection_reason": None,
            "created_at": "2026-07-29T10:00:00Z",
        },
        "metrics": {
            "feedback_count": count,
            "unique_feedback_count": count,
            "duplicate_count": 0,
            "source_distribution": [{"value": "Support", "count": count, "percentage": 100}],
            "user_type_distribution": [{"value": "Power user", "count": count, "percentage": 100}],
            "product_area_distribution": [{"value": "Reporting", "count": count, "percentage": 100}],
            "frequency_over_time": [{"period": "2026-07", "count": count}],
            "rating_summary": {"rated_count": 0, "unrated_count": count, "average": None, "distribution": {}},
        },
    }


def detail(card: dict) -> dict:
    count = card["metrics"]["feedback_count"]
    return {
        **deepcopy(card),
        "historical_theme": None,
        "evidence": [
            {
                "id": f"{card['theme']['id']}-feedback-{index}",
                "source_row": index + 2,
                "feedback_text_original": f"Original supporting feedback {index + 1}",
                "source": "Support",
                "user_type": "Power user",
                "product_area": "Reporting",
                "feedback_date": "2026-07-20",
                "rating": None,
                "membership_score": 0.9,
                "is_primary_evidence": index == 0,
                "assigned_by": "engine",
            }
            for index in range(count)
        ],
    }


@pytest.mark.ui
def test_primary_review_buttons_execute_complete_browser_flows():
    cards = [theme_card("preview-theme-0", "Incorrect information on your report: Loan"), theme_card("preview-theme-1", "Attempts to collect debt not owed", 2)]
    reports: list[dict] = []

    def find_card(theme_id: str) -> dict:
        return next(card for card in cards if card["theme"]["id"] == theme_id)

    def json_response(route: Route, body, status: int = 200) -> None:
        route.fulfill(status=status, content_type="application/json", body=json.dumps(body))

    def handler(route: Route) -> None:
        request = route.request
        path = urlparse(request.url).path
        method = request.method
        payload = json.loads(request.post_data or "{}")

        if path.endswith("/summary"):
            json_response(route, {"run_id": "preview-run", "total_feedback": 5, "assigned_feedback": 5, "coverage_percentage": 100, "theme_count": len(cards), "status_distribution": {}, "pattern_distribution": {"repeated": len(cards)}, "approved_feedback_count": sum(c["metrics"]["feedback_count"] for c in cards if c["theme"]["status"] == "approved"), "rejected_feedback_count": 0})
            return
        if path.endswith("/theme-cards"):
            json_response(route, cards)
            return
        if path.endswith("/logs"):
            json_response(route, [])
            return
        if path == "/api/v1/themes/merge" and method == "POST":
            selected = [find_card(theme_id) for theme_id in payload["theme_ids"]]
            merged = theme_card("theme-merged", payload["title"], sum(c["metrics"]["feedback_count"] for c in selected))
            merged["theme"]["summary"] = payload["summary"]
            merged["theme"]["problem_statement"] = payload["problem_statement"]
            cards[:] = [card for card in cards if card["theme"]["id"] not in payload["theme_ids"]] + [merged]
            json_response(route, merged["theme"])
            return
        if path.startswith("/api/v1/themes/"):
            parts = path.split("/")
            theme_id = parts[4]
            card = find_card(theme_id)
            suffix = parts[5] if len(parts) > 5 else ""
            if method == "GET":
                json_response(route, detail(card))
                return
            if suffix == "rename" and method == "PATCH":
                card["theme"]["title"] = payload["title"]
            elif suffix == "approve" and method == "POST":
                card["theme"]["status"] = "approved"
                card["theme"]["approved_by"] = "demo-user"
            elif suffix == "reject" and method == "POST":
                card["theme"]["status"] = "rejected"
                card["theme"]["rejection_reason"] = payload["reason"]
            elif suffix == "split" and method == "POST":
                created = theme_card("theme-split", payload["new_title"], len(payload["feedback_item_ids"]))
                created["theme"]["summary"] = payload["new_summary"]
                created["theme"]["problem_statement"] = payload["new_problem_statement"]
                card["metrics"]["feedback_count"] -= len(payload["feedback_item_ids"])
                card["metrics"]["unique_feedback_count"] -= len(payload["feedback_item_ids"])
                cards.append(created)
                json_response(route, created["theme"])
                return
            elif method == "PATCH":
                card["theme"].update(payload)
            json_response(route, card["theme"])
            return
        if path.endswith("/reports") and method == "POST":
            report = {"id": "report-1", "title": payload["title"], "version": 1, "created_by": "demo-user", "created_at": "2026-07-29T10:00:00Z"}
            reports.append(report)
            json_response(route, report, 201)
            return
        if path == "/api/v1/projects/preview-project/reports":
            json_response(route, reports)
            return
        json_response(route, {"detail": f"not mocked: {method} {path}"}, 404)

    with sync_playwright() as runner:
        executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
        if not executable and Path("/usr/bin/chromium").exists():
            executable = "/usr/bin/chromium"
        browser = runner.chromium.launch(headless=True, executable_path=executable, args=["--no-sandbox", "--disable-setuid-sandbox"])
        page = browser.new_page(viewport={"width": 1480, "height": 1000})
        page.route("https://signalboard.test/api/v1/**", handler)
        page.route("https://fonts.googleapis.com/**", lambda route: route.fulfill(status=200, content_type="text/css", body=""))
        page.route("https://fonts.gstatic.com/**", lambda route: route.fulfill(status=204))
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)

        html = (WEB / "index.html").read_text(encoding="utf-8")
        html = html.replace('<link rel="stylesheet" href="/app/styles.css" />', f"<style>{(WEB / 'styles.css').read_text(encoding='utf-8')}</style>")
        html = html.replace('<script type="module" src="/app/app.js"></script>', '<script>window.__SIGNALBOARD_PREVIEW__=true;</script>')
        html = html.replace("<head>", '<head><base href="https://signalboard.test/">', 1)
        page.set_content(html, wait_until="domcontentloaded")
        page.add_script_tag(content=(WEB / "app.js").read_text(encoding="utf-8"), type="module")

        page.get_by_role("button", name="Themes").click()
        page.get_by_title("Rename theme").click()
        page.locator("#rename-value").fill("Reviewed export performance")
        page.get_by_role("button", name="Save title").click()
        page.get_by_role("heading", name="Reviewed export performance").wait_for()

        page.get_by_role("button", name="Approve").click()
        page.locator(".status-badge.approved").wait_for()

        page.locator(".split-check").first.check()
        page.get_by_role("button", name="Split 1").click()
        page.locator("#split-title").fill("Large export timeout")
        page.locator("#split-summary").fill("Large export jobs time out.")
        page.locator("#split-problem").fill("Users cannot finish large export jobs.")
        page.get_by_role("button", name="Create split theme").click()
        page.get_by_role("heading", name="Large export timeout").wait_for()

        page.locator(".merge-check").nth(0).check()
        page.locator(".merge-check").nth(1).check()
        page.get_by_role("button", name="Merge 2").click()
        page.locator("#merge-title").fill("Unified reporting reliability")
        page.get_by_role("button", name="Merge themes").click()
        page.get_by_role("heading", name="Unified reporting reliability").wait_for()

        page.get_by_role("button", name="Approve").click()
        page.get_by_role("button", name="Reports").click()
        page.get_by_role("button", name="Save reviewed report").click()
        page.get_by_role("button", name="Save snapshot").click()
        page.get_by_role("heading", name="Reviewed feedback synthesis", exact=False).wait_for()

        browser.close()
        assert errors == []
