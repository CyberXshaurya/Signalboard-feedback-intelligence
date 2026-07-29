from feedback_intelligence_engine.models import AnalysisRun, Dataset, FeedbackItem, Project, Theme, ThemeFeedback
from feedback_intelligence_engine.services.analytics import calculate_theme_metrics
from feedback_intelligence_engine.services.review import merge_themes, split_theme


def _item(dataset_id: str, row: int, text: str) -> FeedbackItem:
    from datetime import date
    from feedback_intelligence_engine.utils.text import content_hash

    return FeedbackItem(
        dataset_id=dataset_id,
        source_row=row,
        feedback_text_original=text,
        feedback_text_normalized=text,
        feedback_text_masked=text,
        source="Support",
        user_type="Pro",
        product_area="Reporting",
        feedback_date=date(2025, 1, row),
        rating=None,
        content_hash=content_hash(text),
    )


def test_merge_and_split_preserve_memberships(db_session):
    project = Project(owner_id="demo-user", name="P")
    db_session.add(project)
    db_session.flush()
    dataset = Dataset(project_id=project.id, file_name="x.csv", file_sha256="x", status="ready")
    db_session.add(dataset)
    db_session.flush()
    run = AnalysisRun(dataset_id=dataset.id, status="ready_for_review")
    db_session.add(run)
    db_session.flush()
    items = [_item(dataset.id, i, f"Report problem number {i}") for i in range(1, 5)]
    db_session.add_all(items)
    db_session.flush()
    t1 = Theme(analysis_run_id=run.id, title="A", summary="Summary A", problem_statement="Problem A")
    t2 = Theme(analysis_run_id=run.id, title="B", summary="Summary B", problem_statement="Problem B")
    db_session.add_all([t1, t2])
    db_session.flush()
    db_session.add_all(
        [ThemeFeedback(theme_id=t1.id, feedback_item_id=items[0].id), ThemeFeedback(theme_id=t1.id, feedback_item_id=items[1].id), ThemeFeedback(theme_id=t2.id, feedback_item_id=items[2].id), ThemeFeedback(theme_id=t2.id, feedback_item_id=items[3].id)]
    )
    db_session.commit()

    merged = merge_themes(db_session, [t1, t2], "Merged", "Merged summary", "Merged problem", "demo-user")
    assert calculate_theme_metrics(db_session, merged.id)["feedback_count"] == 4

    split = split_theme(
        db_session,
        merged,
        [items[0].id, items[1].id],
        "Split",
        "Split summary",
        "Split problem",
        "demo-user",
    )
    assert calculate_theme_metrics(db_session, split.id)["feedback_count"] == 2
    assert calculate_theme_metrics(db_session, merged.id)["feedback_count"] == 2
