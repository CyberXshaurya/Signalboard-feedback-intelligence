from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from collections import Counter

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import __version__
from .config import Settings, get_settings
from .db import get_db
from .models import (
    AnalysisRun,
    Dataset,
    FeedbackItem,
    HistoricalTheme,
    Project,
    Report,
    ReportThemeSnapshot,
    Theme,
    ThemeFeedback,
    ThemeReviewAction,
    WorkflowLog,
)
from .schemas import (
    AnalysisRunOut,
    DatasetOut,
    EditThemeRequest,
    HealthOut,
    HistoricalThemeCreate,
    HistoricalThemeOut,
    MergeThemesRequest,
    ProjectCreate,
    ProjectOut,
    RejectThemeRequest,
    RenameThemeRequest,
    ReportCreate,
    ReportDetail,
    ReportOut,
    ReportSnapshotOut,
    RunSummary,
    SplitThemeRequest,
    ThemeActionOut,
    ThemeCard,
    ThemeDetail,
    ThemeOut,
    WorkflowLogOut,
)
from .services.analytics import calculate_theme_metrics
from .services.csv_ingestion import parse_csv
from .services.reports import create_report
from .services.review import (
    approve_theme,
    edit_theme,
    merge_themes,
    reject_theme,
    rename_theme,
    split_theme,
)
from .services.workflow import execute_analysis

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def current_user(
    settings: SettingsDep, x_user_id: Annotated[str | None, Header()] = None
) -> str:
    if settings.require_user_header and not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return (x_user_id or "demo-user").strip()


User = Annotated[str, Depends(current_user)]


def owned_project(db: Session, project_id: str, user_id: str) -> Project:
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def owned_dataset(db: Session, dataset_id: str, user_id: str) -> Dataset:
    dataset = db.scalar(
        select(Dataset)
        .join(Project, Project.id == Dataset.project_id)
        .where(Dataset.id == dataset_id, Project.owner_id == user_id)
    )
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


def owned_run(db: Session, run_id: str, user_id: str) -> AnalysisRun:
    run = db.scalar(
        select(AnalysisRun)
        .join(Dataset, Dataset.id == AnalysisRun.dataset_id)
        .join(Project, Project.id == Dataset.project_id)
        .where(AnalysisRun.id == run_id, Project.owner_id == user_id)
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return run


def owned_theme(db: Session, theme_id: str, user_id: str) -> Theme:
    theme = db.scalar(
        select(Theme)
        .join(AnalysisRun, AnalysisRun.id == Theme.analysis_run_id)
        .join(Dataset, Dataset.id == AnalysisRun.dataset_id)
        .join(Project, Project.id == Dataset.project_id)
        .where(Theme.id == theme_id, Project.owner_id == user_id)
    )
    if theme is None:
        raise HTTPException(status_code=404, detail="Theme not found")
    return theme


@router.get("/health", response_model=HealthOut)
def health(db: DB, settings: SettingsDep) -> HealthOut:
    db.execute(text("SELECT 1"))
    return HealthOut(
        status="ok",
        database="connected",
        ai_configured=bool(settings.openai_api_key or settings.github_token or settings.ollama_enabled),
        synthesis_provider=settings.synthesis_provider,
        configured_llm_providers=settings.configured_llm_providers,
        embedding_provider=settings.embedding_provider,
        version=__version__,
    )


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: DB, user_id: User) -> Project:
    project = Project(owner_id=user_id, name=payload.name.strip(), description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: DB, user_id: User) -> list[Project]:
    return list(db.scalars(select(Project).where(Project.owner_id == user_id).order_by(Project.created_at.desc())))


@router.post("/projects/{project_id}/historical-themes", response_model=HistoricalThemeOut, status_code=201)
def add_historical_theme(
    project_id: str, payload: HistoricalThemeCreate, db: DB, user_id: User
) -> HistoricalTheme:
    owned_project(db, project_id, user_id)
    item = HistoricalTheme(project_id=project_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/projects/{project_id}/historical-themes", response_model=list[HistoricalThemeOut])
def list_historical_themes(project_id: str, db: DB, user_id: User) -> list[HistoricalTheme]:
    owned_project(db, project_id, user_id)
    return list(db.scalars(select(HistoricalTheme).where(HistoricalTheme.project_id == project_id)))


@router.post("/projects/{project_id}/datasets", response_model=DatasetOut, status_code=201)
async def upload_dataset(
    project_id: str,
    db: DB,
    settings: SettingsDep,
    user_id: User,
    file: Annotated[UploadFile, File()],
    column_mapping_json: str | None = None,
) -> Dataset:
    owned_project(db, project_id, user_id)
    if not file.filename or not file.filename.casefold().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Only CSV files are supported")
    content = await file.read(settings.max_upload_bytes + 1)
    try:
        override = json.loads(column_mapping_json) if column_mapping_json else None
    except JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="column_mapping_json is not valid JSON") from exc
    result = parse_csv(content, settings, override)
    fatal = [issue for issue in result.issues if issue["severity"] == "error" and issue["row"] == 0]
    if fatal:
        raise HTTPException(status_code=422, detail={"issues": fatal})

    dataset = Dataset(
        project_id=project_id,
        file_name=file.filename,
        file_sha256=result.file_sha256,
        total_rows=result.total_rows,
        valid_rows=len(result.rows),
        invalid_rows=result.error_count,
        status="ready" if result.rows else "validation_failed",
        validation_errors=result.issues,
        column_mapping=result.column_mapping,
    )
    db.add(dataset)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This exact file was already imported into the project")
    for row in result.rows:
        db.add(FeedbackItem(dataset_id=dataset.id, **row.__dict__))
    db.commit()
    db.refresh(dataset)
    return dataset


@router.get("/datasets/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: str, db: DB, user_id: User) -> Dataset:
    return owned_dataset(db, dataset_id, user_id)


@router.get("/projects/{project_id}/datasets", response_model=list[DatasetOut])
def list_datasets(project_id: str, db: DB, user_id: User) -> list[Dataset]:
    owned_project(db, project_id, user_id)
    return list(
        db.scalars(
            select(Dataset)
            .where(Dataset.project_id == project_id)
            .order_by(Dataset.created_at.desc())
        )
    )


@router.get("/datasets/{dataset_id}/analysis-runs", response_model=list[AnalysisRunOut])
def list_analysis_runs(dataset_id: str, db: DB, user_id: User) -> list[AnalysisRun]:
    owned_dataset(db, dataset_id, user_id)
    return list(
        db.scalars(
            select(AnalysisRun)
            .where(AnalysisRun.dataset_id == dataset_id)
            .order_by(AnalysisRun.created_at.desc())
        )
    )


@router.post("/datasets/{dataset_id}/analysis-runs", response_model=AnalysisRunOut, status_code=201)
def create_analysis_run(dataset_id: str, db: DB, settings: SettingsDep, user_id: User) -> AnalysisRun:
    dataset = owned_dataset(db, dataset_id, user_id)
    if dataset.valid_rows == 0:
        raise HTTPException(status_code=422, detail="Dataset has no valid rows")
    run = AnalysisRun(dataset_id=dataset.id, status="pending", current_step="pending")
    db.add(run)
    db.commit()
    db.refresh(run)
    try:
        return execute_analysis(db, run, settings)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")


@router.get("/analysis-runs/{run_id}", response_model=AnalysisRunOut)
def get_analysis_run(run_id: str, db: DB, user_id: User) -> AnalysisRun:
    return owned_run(db, run_id, user_id)


@router.get("/analysis-runs/{run_id}/themes", response_model=list[ThemeOut])
def list_themes(run_id: str, db: DB, user_id: User, status_filter: str | None = None) -> list[Theme]:
    owned_run(db, run_id, user_id)
    query = select(Theme).where(Theme.analysis_run_id == run_id)
    if status_filter:
        query = query.where(Theme.status == status_filter)
    return list(db.scalars(query.order_by(Theme.created_at)))


@router.get("/analysis-runs/{run_id}/theme-cards", response_model=list[ThemeCard])
def list_theme_cards(run_id: str, db: DB, user_id: User) -> list[ThemeCard]:
    owned_run(db, run_id, user_id)
    themes = list(
        db.scalars(
            select(Theme)
            .where(Theme.analysis_run_id == run_id, Theme.status != "merged")
            .order_by(Theme.created_at)
        )
    )
    return [
        ThemeCard(theme=ThemeOut.model_validate(theme), metrics=calculate_theme_metrics(db, theme.id))
        for theme in themes
    ]


@router.get("/themes/{theme_id}", response_model=ThemeDetail)
def get_theme(theme_id: str, db: DB, user_id: User) -> ThemeDetail:
    theme = owned_theme(db, theme_id, user_id)
    evidence_rows = list(
        db.execute(
            select(FeedbackItem, ThemeFeedback)
            .join(ThemeFeedback, ThemeFeedback.feedback_item_id == FeedbackItem.id)
            .where(ThemeFeedback.theme_id == theme.id)
            .order_by(FeedbackItem.feedback_date, FeedbackItem.source_row)
        )
    )
    evidence = [
        {
            "id": item.id,
            "source_row": item.source_row,
            "feedback_text_original": item.feedback_text_original,
            "source": item.source,
            "user_type": item.user_type,
            "product_area": item.product_area,
            "feedback_date": item.feedback_date,
            "rating": item.rating,
            "membership_score": link.membership_score,
            "is_primary_evidence": link.is_primary_evidence,
            "assigned_by": link.assigned_by,
        }
        for item, link in evidence_rows
    ]
    historical = db.get(HistoricalTheme, theme.historical_theme_id) if theme.historical_theme_id else None
    return ThemeDetail(
        theme=ThemeOut.model_validate(theme),
        metrics=calculate_theme_metrics(db, theme.id),
        evidence=evidence,
        historical_theme=historical,
    )


@router.patch("/themes/{theme_id}/rename", response_model=ThemeOut)
def rename(theme_id: str, payload: RenameThemeRequest, db: DB, user_id: User) -> Theme:
    return rename_theme(db, owned_theme(db, theme_id, user_id), payload.title, user_id)


@router.patch("/themes/{theme_id}", response_model=ThemeOut)
def edit(theme_id: str, payload: EditThemeRequest, db: DB, user_id: User) -> Theme:
    return edit_theme(
        db, owned_theme(db, theme_id, user_id), payload.summary, payload.problem_statement, user_id
    )


@router.post("/themes/merge", response_model=ThemeOut, status_code=201)
def merge(payload: MergeThemesRequest, db: DB, user_id: User) -> Theme:
    unique_ids = list(dict.fromkeys(payload.theme_ids))
    themes = [owned_theme(db, theme_id, user_id) for theme_id in unique_ids]
    try:
        return merge_themes(db, themes, payload.title, payload.summary, payload.problem_statement, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/themes/{theme_id}/split", response_model=ThemeOut, status_code=201)
def split(theme_id: str, payload: SplitThemeRequest, db: DB, user_id: User) -> Theme:
    try:
        return split_theme(
            db,
            owned_theme(db, theme_id, user_id),
            payload.feedback_item_ids,
            payload.new_title,
            payload.new_summary,
            payload.new_problem_statement,
            user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/themes/{theme_id}/history", response_model=list[ThemeActionOut])
def theme_history(theme_id: str, db: DB, user_id: User) -> list[ThemeReviewAction]:
    theme = owned_theme(db, theme_id, user_id)
    return list(
        db.scalars(
            select(ThemeReviewAction)
            .where(ThemeReviewAction.theme_id == theme.id)
            .order_by(ThemeReviewAction.created_at)
        )
    )


@router.get("/analysis-runs/{run_id}/logs", response_model=list[WorkflowLogOut])
def run_logs(run_id: str, db: DB, user_id: User) -> list[WorkflowLog]:
    owned_run(db, run_id, user_id)
    return list(
        db.scalars(
            select(WorkflowLog)
            .where(WorkflowLog.analysis_run_id == run_id)
            .order_by(WorkflowLog.created_at)
        )
    )


@router.get("/analysis-runs/{run_id}/summary", response_model=RunSummary)
def run_summary(run_id: str, db: DB, user_id: User) -> RunSummary:
    run = owned_run(db, run_id, user_id)
    total_feedback = int(
        db.scalar(select(func.count(FeedbackItem.id)).where(FeedbackItem.dataset_id == run.dataset_id)) or 0
    )
    themes = list(db.scalars(select(Theme).where(Theme.analysis_run_id == run.id)))
    assigned_feedback = int(
        db.scalar(
            select(func.count(func.distinct(ThemeFeedback.feedback_item_id)))
            .join(Theme, Theme.id == ThemeFeedback.theme_id)
            .where(Theme.analysis_run_id == run.id, Theme.status != "merged")
        )
        or 0
    )
    approved_feedback = int(
        db.scalar(
            select(func.count(func.distinct(ThemeFeedback.feedback_item_id)))
            .join(Theme, Theme.id == ThemeFeedback.theme_id)
            .where(Theme.analysis_run_id == run.id, Theme.status == "approved")
        )
        or 0
    )
    rejected_feedback = int(
        db.scalar(
            select(func.count(func.distinct(ThemeFeedback.feedback_item_id)))
            .join(Theme, Theme.id == ThemeFeedback.theme_id)
            .where(Theme.analysis_run_id == run.id, Theme.status == "rejected")
        )
        or 0
    )
    return RunSummary(
        run_id=run.id,
        total_feedback=total_feedback,
        assigned_feedback=assigned_feedback,
        coverage_percentage=round((assigned_feedback / total_feedback) * 100, 2) if total_feedback else 0.0,
        theme_count=len(themes),
        status_distribution=dict(Counter(theme.status for theme in themes)),
        pattern_distribution=dict(Counter(theme.pattern_type for theme in themes)),
        approved_feedback_count=approved_feedback,
        rejected_feedback_count=rejected_feedback,
    )


@router.post("/themes/{theme_id}/approve", response_model=ThemeOut)
def approve(theme_id: str, db: DB, user_id: User) -> Theme:
    try:
        return approve_theme(db, owned_theme(db, theme_id, user_id), user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/themes/{theme_id}/reject", response_model=ThemeOut)
def reject(theme_id: str, payload: RejectThemeRequest, db: DB, user_id: User) -> Theme:
    return reject_theme(db, owned_theme(db, theme_id, user_id), payload.reason, user_id)


@router.post("/analysis-runs/{run_id}/reports", response_model=ReportOut, status_code=201)
def save_report(run_id: str, payload: ReportCreate, db: DB, user_id: User) -> Report:
    run = owned_run(db, run_id, user_id)
    try:
        return create_report(db, run, payload.title, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/projects/{project_id}/reports", response_model=list[ReportOut])
def list_reports(project_id: str, db: DB, user_id: User) -> list[Report]:
    owned_project(db, project_id, user_id)
    return list(
        db.scalars(
            select(Report)
            .where(Report.project_id == project_id)
            .order_by(Report.created_at.desc())
        )
    )


@router.get("/reports/{report_id}", response_model=ReportDetail)
def get_report(report_id: str, db: DB, user_id: User) -> ReportDetail:
    report = db.scalar(
        select(Report)
        .join(Project, Project.id == Report.project_id)
        .where(Report.id == report_id, Project.owner_id == user_id)
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    snapshots = list(
        db.scalars(
            select(ReportThemeSnapshot)
            .where(ReportThemeSnapshot.report_id == report.id)
            .order_by(ReportThemeSnapshot.theme_title)
        )
    )
    return ReportDetail(
        report=ReportOut.model_validate(report),
        themes=[ReportSnapshotOut.model_validate(snapshot) for snapshot in snapshots],
    )
