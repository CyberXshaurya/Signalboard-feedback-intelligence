import json
from datetime import date
from types import SimpleNamespace

import pytest

from feedback_intelligence_engine.config import Settings
from feedback_intelligence_engine.models import FeedbackItem
from feedback_intelligence_engine.services.clustering import CandidateCluster, cluster_feedback
from feedback_intelligence_engine.services.synthesis import (
    ThemeDraft,
    ThemeDraftBatch,
    _openai_synthesis,
    synthesize_themes,
)
from feedback_intelligence_engine.utils.text import content_hash


def make_item(index: int) -> FeedbackItem:
    text = f"Report export problem {index} takes too long"
    return FeedbackItem(
        id=f"feedback-{index}",
        dataset_id="dataset",
        source_row=index + 2,
        feedback_text_original=text,
        feedback_text_normalized=text,
        feedback_text_masked=text,
        source="Support",
        user_type="Enterprise",
        product_area="Reporting",
        feedback_date=date(2025, 1, 1),
        rating=2,
        content_hash=content_hash(text),
    )


def test_explicit_openai_modes_require_a_key():
    items = [make_item(1), make_item(2)]
    cluster = CandidateCluster(
        cluster_key="cluster-0",
        item_ids=[item.id for item in items],
        representative_ids=[item.id for item in items],
        coherence=0.8,
        pattern_type="repeated",
        unique_feedback_count=2,
        dominant_product_area="Reporting",
    )
    with pytest.raises(RuntimeError, match="SYNTHESIS_PROVIDER"):
        synthesize_themes([cluster], items, Settings(synthesis_provider="openai"))
    with pytest.raises(RuntimeError, match="EMBEDDING_PROVIDER"):
        cluster_feedback(items, Settings(embedding_provider="openai"))


def test_openai_synthesis_is_batched_and_parsed(monkeypatch):
    items = [make_item(index) for index in range(21)]
    clusters = [
        CandidateCluster(
            cluster_key=f"cluster-{index}",
            item_ids=[item.id],
            representative_ids=[item.id],
            coherence=1.0,
            pattern_type="isolated",
            unique_feedback_count=1,
            dominant_product_area="Reporting",
        )
        for index, item in enumerate(items)
    ]
    calls = []

    class FakeResponses:
        def parse(self, *, model, input, text_format):
            calls.append(input)
            payload = json.loads(input[1]["content"].split("\n", 1)[1])
            parsed = ThemeDraftBatch(
                themes=[
                    ThemeDraft(
                        cluster_key=row["cluster_key"],
                        title="Grounded theme",
                        summary="Grounded summary from supplied feedback.",
                        problem_statement="Users cannot complete the expected reporting workflow.",
                        evidence_feedback_ids=[row["representative_feedback"][0]["feedback_id"]],
                        confidence=0.8,
                        uncertainty_reason=None,
                    )
                    for row in payload
                ]
            )
            return SimpleNamespace(output_parsed=parsed, id=f"response-{len(calls)}")

    class FakeOpenAI:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    import feedback_intelligence_engine.services.synthesis as module

    monkeypatch.setattr(module, "OpenAI", FakeOpenAI)
    result = _openai_synthesis(
        clusters,
        {item.id: item for item in items},
        Settings(
            openai_api_key="test-key",
            synthesis_provider="openai",
            max_clusters_per_synthesis=20,
        ),
    )
    assert len(calls) == 2
    assert len(result.drafts) == 21
    assert result.diagnostics["batch_count"] == 2
