import json
from datetime import date

from feedback_intelligence_engine.config import Settings
from feedback_intelligence_engine.models import FeedbackItem
from feedback_intelligence_engine.services.clustering import CandidateCluster
from feedback_intelligence_engine.services.synthesis import _github_synthesis


def make_item(index: int) -> FeedbackItem:
    return FeedbackItem(
        id=f"feedback-{index}",
        dataset_id="dataset-1",
        source_row=index + 2,
        external_id=None,
        feedback_text_original=f"Export freezes during report generation {index}",
        feedback_text_normalized=f"Export freezes during report generation {index}",
        feedback_text_masked=f"Export freezes during report generation {index}",
        source="Support",
        user_type="Enterprise",
        product_area="Reporting",
        feedback_date=date(2026, 7, 1),
        rating=2,
        content_hash=f"hash-{index}",
        duplicate_group_id=None,
        validation_status="valid",
    )


def test_github_models_uses_json_schema_and_server_side_token(monkeypatch):
    items = [make_item(0), make_item(1)]
    cluster = CandidateCluster(
        cluster_key="cluster-0",
        item_ids=[item.id for item in items],
        representative_ids=[item.id for item in items],
        coherence=0.82,
        pattern_type="repeated",
        unique_feedback_count=2,
        dominant_product_area="Reporting",
    )
    captured = {}

    class FakeResponse:
        headers = {"x-github-request-id": "request-1"}

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "themes": [
                                        {
                                            "cluster_key": "cluster-0",
                                            "title": "Report export freezes",
                                            "summary": "Users report export freezes while generating reports.",
                                            "problem_statement": "Users cannot reliably export reports.",
                                            "evidence_feedback_ids": ["feedback-0"],
                                            "confidence": 0.84,
                                            "uncertainty_reason": None,
                                        }
                                    ]
                                }
                            )
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers, json):
            captured.update({"url": url, "headers": headers, "payload": json})
            return FakeResponse()

    import feedback_intelligence_engine.services.synthesis as module

    monkeypatch.setattr(module.httpx, "Client", FakeClient)
    result = _github_synthesis(
        [cluster],
        {item.id: item for item in items},
        Settings(
            github_token="secret-token",
            synthesis_provider="github",
            github_model="openai/gpt-4.1-mini",
        ),
    )

    assert result.provider == "github"
    assert result.drafts["cluster-0"].evidence_feedback_ids == ["feedback-0"]
    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer secret-token"
    assert captured["payload"]["response_format"]["type"] == "json_schema"
    schema = captured["payload"]["response_format"]["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["ThemeDraft"]["additionalProperties"] is False
    assert "uncertainty_reason" in schema["$defs"]["ThemeDraft"]["required"]
    assert "secret-token" not in json.dumps(captured["payload"])
