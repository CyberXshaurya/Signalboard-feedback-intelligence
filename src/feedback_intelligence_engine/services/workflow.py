from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings
from ..request_context import get_request_id
from ..models import (
    AnalysisRun,
    FeedbackItem,
    HistoricalTheme,
    Theme,
    ThemeFeedback,
    WorkflowLog,
)
from .clustering import cluster_feedback
from .synthesis import PROMPT_VERSION, synthesize_themes


def log_event(
    db: Session,
    *,
    run_id: str | None,
    event_type: str,
    step: str | None = None,
    severity: str = "INFO",
    duration_ms: int | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(
        WorkflowLog(
            analysis_run_id=run_id,
            request_id=get_request_id(),
            event_type=event_type,
            severity=severity,
            step=step,
            duration_ms=duration_ms,
            metadata_json=metadata or {},
        )
    )


def _set_progress(db: Session, run: AnalysisRun, status: str, step: str, progress: int) -> None:
    run.status = status
    run.current_step = step
    run.progress_percent = progress
    db.flush()


def _historical_match(
    theme_title: str, theme_summary: str, product_area: str | None, historical: list[HistoricalTheme]
) -> tuple[str, str | None, float]:
    if not historical:
        return "new", None, 0.0
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    current = f"{product_area or ''} {theme_title} {theme_summary}"
    documents = [current] + [
        f"{item.product_area or ''} {item.title} {item.description} {item.notes or ''}" for item in historical
    ]
    try:
        matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform(documents)
        similarities = cosine_similarity(matrix[0:1], matrix[1:]).ravel()
    except ValueError:
        return "new", None, 0.0
    best_index = int(similarities.argmax())
    score = float(similarities[best_index])
    if score >= 0.58:
        relationship = "recurring"
    elif score >= 0.36:
        relationship = "possibly_related"
    else:
        return "new", None, round(score, 4)
    return relationship, historical[best_index].id, round(score, 4)


def execute_analysis(db: Session, run: AnalysisRun, settings: Settings) -> AnalysisRun:
    start = time.perf_counter()
    run.started_at = datetime.now(timezone.utc)
    run.prompt_version = PROMPT_VERSION
    try:
        _set_progress(db, run, "preprocessing", "loading_feedback", 10)
        log_event(db, run_id=run.id, event_type="analysis.started", step="loading_feedback")
        db.commit()

        items = list(
            db.scalars(
                select(FeedbackItem)
                .where(FeedbackItem.dataset_id == run.dataset_id)
                .order_by(FeedbackItem.source_row)
            )
        )
        if not items:
            raise ValueError("Dataset contains no valid feedback items")

        _set_progress(db, run, "clustering", "clustering_feedback", 35)
        cluster_start = time.perf_counter()
        clustering = cluster_feedback(items, settings)
        log_event(
            db,
            run_id=run.id,
            event_type="clustering.completed",
            step="clustering_feedback",
            duration_ms=int((time.perf_counter() - cluster_start) * 1000),
            metadata=clustering.diagnostics,
        )
        db.commit()

        _set_progress(db, run, "synthesising", "synthesising_themes", 60)
        synthesis_start = time.perf_counter()
        synthesis = synthesize_themes(clustering.clusters, items, settings)
        run.provider = synthesis.provider
        run.model = synthesis.model
        log_event(
            db,
            run_id=run.id,
            event_type="synthesis.completed",
            step="synthesising_themes",
            duration_ms=int((time.perf_counter() - synthesis_start) * 1000),
            metadata=synthesis.diagnostics,
        )
        db.commit()

        _set_progress(db, run, "validating", "persisting_grounded_themes", 80)
        items_by_id = {item.id: item for item in items}
        project_id = run.dataset.project_id
        historical = list(
            db.scalars(select(HistoricalTheme).where(HistoricalTheme.project_id == project_id))
        )
        historical_scores: dict[str, float] = {}
        for cluster in clustering.clusters:
            draft = synthesis.drafts[cluster.cluster_key]
            product_areas = {items_by_id[item_id].product_area for item_id in cluster.item_ids}
            primary_area = next(iter(product_areas)) if len(product_areas) == 1 else None
            relationship, historical_id, score = _historical_match(
                draft.title, draft.summary, primary_area, historical
            )
            theme = Theme(
                analysis_run_id=run.id,
                title=draft.title,
                summary=draft.summary,
                problem_statement=draft.problem_statement,
                pattern_type=cluster.pattern_type,
                confidence=draft.confidence,
                uncertainty_reason=draft.uncertainty_reason,
                status="needs_review",
                historical_relationship=relationship,
                historical_theme_id=historical_id,
                historical_similarity_score=score,
            )
            db.add(theme)
            db.flush()
            evidence_ids = set(draft.evidence_feedback_ids)
            for item_id in cluster.item_ids:
                db.add(
                    ThemeFeedback(
                        theme_id=theme.id,
                        feedback_item_id=item_id,
                        membership_score=cluster.coherence,
                        is_primary_evidence=item_id in evidence_ids,
                        assigned_by=synthesis.provider,
                    )
                )
            historical_scores[theme.id] = score

        run.status = "ready_for_review"
        run.current_step = "complete"
        run.progress_percent = 100
        run.completed_at = datetime.now(timezone.utc)
        run.diagnostics = {
            "clustering": clustering.diagnostics,
            "synthesis": synthesis.diagnostics,
            "historical_similarity": historical_scores,
        }
        log_event(
            db,
            run_id=run.id,
            event_type="analysis.completed",
            step="complete",
            duration_ms=int((time.perf_counter() - start) * 1000),
            metadata={"theme_count": len(clustering.clusters), "provider": synthesis.provider},
        )
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:
        db.rollback()
        run = db.get(AnalysisRun, run.id)
        if run is not None:
            run.status = "failed"
            run.current_step = "failed"
            run.failure_code = type(exc).__name__
            run.failure_message = str(exc)[:2000]
            run.completed_at = datetime.now(timezone.utc)
            log_event(
                db,
                run_id=run.id,
                event_type="analysis.failed",
                step="failed",
                severity="ERROR",
                duration_ms=int((time.perf_counter() - start) * 1000),
                metadata={"error_type": type(exc).__name__, "message": str(exc)[:1000]},
            )
            db.commit()
        raise
