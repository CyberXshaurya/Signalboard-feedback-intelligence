from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Theme, ThemeFeedback, ThemeReviewAction


def snapshot_theme(theme: Theme) -> dict:
    return {
        "id": theme.id,
        "title": theme.title,
        "summary": theme.summary,
        "problem_statement": theme.problem_statement,
        "status": theme.status,
        "pattern_type": theme.pattern_type,
        "confidence": theme.confidence,
        "merged_into_theme_id": theme.merged_into_theme_id,
        "rejection_reason": theme.rejection_reason,
    }


def add_action(
    db: Session,
    theme: Theme,
    action_type: str,
    before: dict,
    after: dict,
    user_id: str,
) -> None:
    db.add(
        ThemeReviewAction(
            analysis_run_id=theme.analysis_run_id,
            theme_id=theme.id,
            action_type=action_type,
            before_state=before,
            after_state=after,
            performed_by=user_id,
        )
    )


def rename_theme(db: Session, theme: Theme, title: str, user_id: str) -> Theme:
    before = snapshot_theme(theme)
    theme.title = title.strip()
    after = snapshot_theme(theme)
    add_action(db, theme, "rename", before, after, user_id)
    db.commit()
    db.refresh(theme)
    return theme


def edit_theme(
    db: Session, theme: Theme, summary: str | None, problem_statement: str | None, user_id: str
) -> Theme:
    before = snapshot_theme(theme)
    if summary is not None:
        theme.summary = summary.strip()
    if problem_statement is not None:
        theme.problem_statement = problem_statement.strip()
    add_action(db, theme, "edit", before, snapshot_theme(theme), user_id)
    db.commit()
    db.refresh(theme)
    return theme


def merge_themes(
    db: Session,
    themes: list[Theme],
    title: str,
    summary: str,
    problem_statement: str,
    user_id: str,
) -> Theme:
    run_ids = {theme.analysis_run_id for theme in themes}
    if len(run_ids) != 1:
        raise ValueError("Themes must belong to the same analysis run")
    if any(theme.status == "merged" for theme in themes):
        raise ValueError("An already merged theme cannot be merged again")

    new_theme = Theme(
        analysis_run_id=themes[0].analysis_run_id,
        title=title.strip(),
        summary=summary.strip(),
        problem_statement=problem_statement.strip(),
        pattern_type="repeated",
        confidence=round(sum(theme.confidence for theme in themes) / len(themes), 2),
        status="needs_review",
        historical_relationship=(
            "recurring" if any(theme.historical_relationship == "recurring" for theme in themes) else "new"
        ),
    )
    db.add(new_theme)
    db.flush()

    memberships: dict[str, ThemeFeedback] = {}
    for theme in themes:
        links = list(
            db.scalars(select(ThemeFeedback).where(ThemeFeedback.theme_id == theme.id))
        )
        for link in links:
            memberships.setdefault(link.feedback_item_id, link)
    for item_id, link in memberships.items():
        db.add(
            ThemeFeedback(
                theme_id=new_theme.id,
                feedback_item_id=item_id,
                membership_score=link.membership_score,
                is_primary_evidence=link.is_primary_evidence,
                assigned_by="human_merge",
            )
        )

    for theme in themes:
        before = snapshot_theme(theme)
        theme.status = "merged"
        theme.merged_into_theme_id = new_theme.id
        add_action(db, theme, "merge", before, snapshot_theme(theme), user_id)
    add_action(db, new_theme, "created_by_merge", {}, snapshot_theme(new_theme), user_id)
    db.commit()
    db.refresh(new_theme)
    return new_theme


def split_theme(
    db: Session,
    theme: Theme,
    selected_item_ids: list[str],
    title: str,
    summary: str,
    problem_statement: str,
    user_id: str,
) -> Theme:
    links = list(db.scalars(select(ThemeFeedback).where(ThemeFeedback.theme_id == theme.id)))
    existing_ids = {link.feedback_item_id for link in links}
    selected = set(selected_item_ids)
    if not selected.issubset(existing_ids):
        raise ValueError("Split contains feedback that is not assigned to the theme")
    if not selected or selected == existing_ids:
        raise ValueError("Split must move at least one, but not all, feedback items")

    new_theme = Theme(
        analysis_run_id=theme.analysis_run_id,
        title=title.strip(),
        summary=summary.strip(),
        problem_statement=problem_statement.strip(),
        pattern_type="repeated" if len(selected) > 1 else "isolated",
        confidence=theme.confidence,
        status="needs_review",
        historical_relationship="new",
    )
    db.add(new_theme)
    db.flush()
    before = snapshot_theme(theme)
    for link in links:
        if link.feedback_item_id in selected:
            db.add(
                ThemeFeedback(
                    theme_id=new_theme.id,
                    feedback_item_id=link.feedback_item_id,
                    membership_score=link.membership_score,
                    is_primary_evidence=link.is_primary_evidence,
                    assigned_by="human_split",
                )
            )
            db.delete(link)
    theme.status = "needs_review"
    add_action(db, theme, "split_source", before, snapshot_theme(theme), user_id)
    add_action(db, new_theme, "created_by_split", {}, snapshot_theme(new_theme), user_id)
    db.commit()
    db.refresh(new_theme)
    return new_theme


def approve_theme(db: Session, theme: Theme, user_id: str) -> Theme:
    membership_count = db.query(ThemeFeedback).filter(ThemeFeedback.theme_id == theme.id).count()
    if membership_count == 0:
        raise ValueError("Theme has no supporting feedback")
    before = snapshot_theme(theme)
    theme.status = "approved"
    theme.approved_by = user_id
    theme.approved_at = datetime.now(timezone.utc)
    theme.rejected_at = None
    theme.rejection_reason = None
    add_action(db, theme, "approve", before, snapshot_theme(theme), user_id)
    db.commit()
    db.refresh(theme)
    return theme


def reject_theme(db: Session, theme: Theme, reason: str, user_id: str) -> Theme:
    before = snapshot_theme(theme)
    theme.status = "rejected"
    theme.rejected_at = datetime.now(timezone.utc)
    theme.rejection_reason = reason.strip()
    theme.approved_at = None
    theme.approved_by = None
    add_action(db, theme, "reject", before, snapshot_theme(theme), user_id)
    db.commit()
    db.refresh(theme)
    return theme
