from datetime import date

from feedback_intelligence_engine.models import FeedbackItem
from feedback_intelligence_engine.services.clustering import CandidateCluster
from feedback_intelligence_engine.services.synthesis import ThemeDraft, _sanitize_draft
from feedback_intelligence_engine.utils.text import content_hash


def test_invented_evidence_ids_are_removed():
    item = FeedbackItem(
        id="valid-feedback-id",
        dataset_id="dataset-id",
        source_row=2,
        feedback_text_original="Report export takes too long",
        feedback_text_normalized="Report export takes too long",
        feedback_text_masked="Report export takes too long",
        source="Support",
        user_type="Enterprise",
        product_area="Reporting",
        feedback_date=date(2025, 1, 1),
        rating=2,
        content_hash=content_hash("Report export takes too long"),
    )
    cluster = CandidateCluster(
        cluster_key="cluster-0",
        item_ids=[item.id],
        representative_ids=[item.id],
        coherence=1.0,
        pattern_type="isolated",
        unique_feedback_count=1,
        dominant_product_area="Reporting",
    )
    draft = ThemeDraft(
        cluster_key="cluster-0",
        title="Slow exports",
        summary="Exports are slow.",
        problem_statement="Users cannot export reports promptly.",
        evidence_feedback_ids=["invented-id"],
        confidence=0.8,
        uncertainty_reason=None,
    )
    cleaned = _sanitize_draft(draft, cluster)
    assert cleaned.evidence_feedback_ids == [item.id]
    assert "invented-id" not in cleaned.evidence_feedback_ids
