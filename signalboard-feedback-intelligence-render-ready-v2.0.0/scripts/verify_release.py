"""Run a credential-free end-to-end release check against the packaged real-data sample."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Settings and the SQLAlchemy engine are constructed at import time.
verification_dir = Path(tempfile.mkdtemp(prefix="signalboard-release-"))
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{verification_dir / 'release.db'}"
os.environ["SYNTHESIS_PROVIDER"] = "heuristic"
os.environ["EMBEDDING_PROVIDER"] = "tfidf"
os.environ["REQUIRE_USER_HEADER"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from feedback_intelligence_engine import __version__  # noqa: E402
from feedback_intelligence_engine.main import app  # noqa: E402

USER_HEADERS = {"X-User-Id": "release-verifier"}
SAMPLE = ROOT / "data" / "cfpb_feedback_sample.csv"


def require(response, expected: int):
    if response.status_code != expected:
        raise AssertionError(
            f"{response.request.method} {response.request.url}: "
            f"expected {expected}, received {response.status_code}: {response.text}"
        )
    return response.json() if response.content else None


def main() -> None:
    with TestClient(app) as client:
        health = require(client.get("/api/v1/health", headers=USER_HEADERS), 200)
        assert health["version"] == __version__
        index = client.get("/", headers=USER_HEADERS)
        assert index.status_code == 200 and "Signalboard" in index.text
        sample_asset = client.get("/app/cfpb_feedback_sample.csv", headers=USER_HEADERS)
        assert sample_asset.status_code == 200 and b"feedback_text" in sample_asset.content[:200]

        project = require(
            client.post(
                "/api/v1/projects",
                headers=USER_HEADERS,
                json={
                    "name": "Release verification",
                    "description": "Automated real-data release verification.",
                },
            ),
            201,
        )
        with SAMPLE.open("rb") as handle:
            dataset = require(
                client.post(
                    f"/api/v1/projects/{project['id']}/datasets",
                    headers=USER_HEADERS,
                    files={"file": (SAMPLE.name, handle, "text/csv")},
                ),
                201,
            )
        assert dataset["total_rows"] == 250
        assert dataset["valid_rows"] == 250
        assert dataset["invalid_rows"] == 0

        run = require(
            client.post(
                f"/api/v1/datasets/{dataset['id']}/analysis-runs",
                headers=USER_HEADERS,
            ),
            201,
        )
        assert run["status"] == "ready_for_review"
        assert run["provider"] == "heuristic"

        summary = require(
            client.get(f"/api/v1/analysis-runs/{run['id']}/summary", headers=USER_HEADERS),
            200,
        )
        cards = require(
            client.get(f"/api/v1/analysis-runs/{run['id']}/theme-cards", headers=USER_HEADERS),
            200,
        )
        logs = require(
            client.get(f"/api/v1/analysis-runs/{run['id']}/logs", headers=USER_HEADERS),
            200,
        )
        assert summary["coverage_percentage"] == 100.0
        assert len(cards) >= 2
        assert any(item["event_type"] == "analysis.completed" for item in logs)

        first_theme = cards[0]["theme"]
        detail = require(client.get(f"/api/v1/themes/{first_theme['id']}", headers=USER_HEADERS), 200)
        assert detail["evidence"]
        assert any(item["is_primary_evidence"] for item in detail["evidence"])

        approved = require(
            client.post(f"/api/v1/themes/{first_theme['id']}/approve", headers=USER_HEADERS),
            200,
        )
        assert approved["status"] == "approved"

        report = require(
            client.post(
                f"/api/v1/analysis-runs/{run['id']}/reports",
                headers=USER_HEADERS,
                json={"title": "Verified release report"},
            ),
            201,
        )
        report_detail = require(client.get(f"/api/v1/reports/{report['id']}", headers=USER_HEADERS), 200)
        assert report_detail["themes"][0]["evidence_json"]

        result = {
            "version": __version__,
            "database": health["database"],
            "sample_rows": dataset["valid_rows"],
            "duplicate_warnings": sum(
                1 for issue in dataset["validation_errors"] if issue["code"] == "exact_duplicate"
            ),
            "theme_count": summary["theme_count"],
            "coverage_percentage": summary["coverage_percentage"],
            "approved_theme_id": approved["id"],
            "report_version": report["version"],
            "workflow_events": len(logs),
            "status": "passed",
        }
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
