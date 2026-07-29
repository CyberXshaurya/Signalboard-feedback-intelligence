from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    AnalysisRun,
    FeedbackItem,
    HistoricalTheme,
    Report,
    ReportThemeSnapshot,
    Theme,
    ThemeFeedback,
)
from .analytics import calculate_theme_metrics


def create_report(db: Session, run: AnalysisRun, title: str, user_id: str) -> Report:
    approved = list(
        db.scalars(
            select(Theme)
            .where(Theme.analysis_run_id == run.id, Theme.status == "approved")
            .order_by(Theme.created_at)
        )
    )
    if not approved:
        raise ValueError("At least one approved theme is required")
    project_id = run.dataset.project_id
    latest_version = db.scalar(
        select(func.max(Report.version)).where(Report.analysis_run_id == run.id)
    ) or 0
    report = Report(
        project_id=project_id,
        analysis_run_id=run.id,
        title=title.strip(),
        version=latest_version + 1,
        created_by=user_id,
        methodology={
            "theme_generation": "AI-assisted or deterministic fallback with human review",
            "counts": "Calculated from validated theme-feedback memberships",
            "roadmap_priority": "Not generated",
            "historical_counts_included": False,
            "prompt_version": run.prompt_version,
            "provider": run.provider,
            "model": run.model,
        },
    )
    db.add(report)
    db.flush()

    for theme in approved:
        evidence_rows = list(
            db.execute(
                select(FeedbackItem, ThemeFeedback)
                .join(ThemeFeedback, ThemeFeedback.feedback_item_id == FeedbackItem.id)
                .where(ThemeFeedback.theme_id == theme.id)
                .order_by(FeedbackItem.feedback_date, FeedbackItem.source_row)
            )
        )
        historical = db.get(HistoricalTheme, theme.historical_theme_id) if theme.historical_theme_id else None
        db.add(
            ReportThemeSnapshot(
                report_id=report.id,
                original_theme_id=theme.id,
                theme_title=theme.title,
                summary=theme.summary,
                problem_statement=theme.problem_statement,
                pattern_type=theme.pattern_type,
                metrics_json=calculate_theme_metrics(db, theme.id),
                evidence_json=[
                    {
                        "feedback_id": item.id,
                        "source_row": item.source_row,
                        "feedback_text": item.feedback_text_original,
                        "source": item.source,
                        "user_type": item.user_type,
                        "product_area": item.product_area,
                        "date": item.feedback_date.isoformat(),
                        "rating": item.rating,
                        "membership_score": link.membership_score,
                        "is_primary_evidence": link.is_primary_evidence,
                        "assigned_by": link.assigned_by,
                    }
                    for item, link in evidence_rows
                ],
                historical_comparison_json={
                    "relationship": theme.historical_relationship,
                    "similarity_score": theme.historical_similarity_score,
                    "historical_theme": None
                    if historical is None
                    else {
                        "id": historical.id,
                        "title": historical.title,
                        "description": historical.description,
                    },
                },
            )
        )
    db.commit()
    db.refresh(report)
    return report
