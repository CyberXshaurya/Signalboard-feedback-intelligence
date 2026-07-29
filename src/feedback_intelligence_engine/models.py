from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    datasets: Mapped[list[Dataset]] = relationship(back_populates="project", cascade="all, delete")
    historical_themes: Mapped[list[HistoricalTheme]] = relationship(
        back_populates="project", cascade="all, delete"
    )


class Dataset(Base, TimestampMixin):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_sha256: Mapped[str] = mapped_column(String(64), index=True)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default="ready")
    validation_errors: Mapped[list[dict]] = mapped_column(JSON, default=list)
    column_mapping: Mapped[dict] = mapped_column(JSON, default=dict)

    project: Mapped[Project] = relationship(back_populates="datasets")
    feedback_items: Mapped[list[FeedbackItem]] = relationship(
        back_populates="dataset", cascade="all, delete"
    )
    analysis_runs: Mapped[list[AnalysisRun]] = relationship(
        back_populates="dataset", cascade="all, delete"
    )

    __table_args__ = (UniqueConstraint("project_id", "file_sha256", name="uq_project_file_hash"),)


class FeedbackItem(Base, TimestampMixin):
    __tablename__ = "feedback_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), index=True)
    source_row: Mapped[int] = mapped_column(Integer)
    external_id: Mapped[str | None] = mapped_column(String(255))
    feedback_text_original: Mapped[str] = mapped_column(Text)
    feedback_text_normalized: Mapped[str] = mapped_column(Text)
    feedback_text_masked: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(120), index=True)
    user_type: Mapped[str] = mapped_column(String(120), index=True)
    product_area: Mapped[str] = mapped_column(String(160), index=True)
    feedback_date: Mapped[date] = mapped_column(Date, index=True)
    rating: Mapped[float | None] = mapped_column(Float)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    duplicate_group_id: Mapped[str | None] = mapped_column(String(64), index=True)
    validation_status: Mapped[str] = mapped_column(String(30), default="valid")

    dataset: Mapped[Dataset] = relationship(back_populates="feedback_items")
    theme_links: Mapped[list[ThemeFeedback]] = relationship(
        back_populates="feedback_item", cascade="all, delete"
    )


class HistoricalTheme(Base, TimestampMixin):
    __tablename__ = "historical_themes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    product_area: Mapped[str | None] = mapped_column(String(160))
    notes: Mapped[str | None] = mapped_column(Text)
    active_from: Mapped[date | None] = mapped_column(Date)
    active_until: Mapped[date | None] = mapped_column(Date)

    project: Mapped[Project] = relationship(back_populates="historical_themes")


class AnalysisRun(Base, TimestampMixin):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    provider: Mapped[str] = mapped_column(String(40), default="heuristic")
    model: Mapped[str | None] = mapped_column(String(120))
    prompt_version: Mapped[str] = mapped_column(String(40), default="theme-v1")
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    current_step: Mapped[str] = mapped_column(String(80), default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(100))
    failure_message: Mapped[str | None] = mapped_column(Text)
    diagnostics: Mapped[dict] = mapped_column(JSON, default=dict)

    dataset: Mapped[Dataset] = relationship(back_populates="analysis_runs")
    themes: Mapped[list[Theme]] = relationship(back_populates="analysis_run", cascade="all, delete")
    logs: Mapped[list[WorkflowLog]] = relationship(back_populates="analysis_run", cascade="all, delete")


class Theme(Base, TimestampMixin):
    __tablename__ = "themes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    analysis_run_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(240))
    summary: Mapped[str] = mapped_column(Text)
    problem_statement: Mapped[str] = mapped_column(Text)
    pattern_type: Mapped[str] = mapped_column(String(30), default="uncertain")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    uncertainty_reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="needs_review", index=True)
    historical_relationship: Mapped[str] = mapped_column(String(40), default="new")
    historical_theme_id: Mapped[str | None] = mapped_column(
        ForeignKey("historical_themes.id", ondelete="SET NULL")
    )
    historical_similarity_score: Mapped[float | None] = mapped_column(Float)
    merged_into_theme_id: Mapped[str | None] = mapped_column(
        ForeignKey("themes.id", ondelete="SET NULL")
    )
    approved_by: Mapped[str | None] = mapped_column(String(128))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="themes")
    feedback_links: Mapped[list[ThemeFeedback]] = relationship(
        back_populates="theme", cascade="all, delete-orphan"
    )


class ThemeFeedback(Base):
    __tablename__ = "theme_feedback"

    theme_id: Mapped[str] = mapped_column(
        ForeignKey("themes.id", ondelete="CASCADE"), primary_key=True
    )
    feedback_item_id: Mapped[str] = mapped_column(
        ForeignKey("feedback_items.id", ondelete="CASCADE"), primary_key=True
    )
    membership_score: Mapped[float] = mapped_column(Float, default=1.0)
    is_primary_evidence: Mapped[bool] = mapped_column(default=False)
    assigned_by: Mapped[str] = mapped_column(String(30), default="engine")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    theme: Mapped[Theme] = relationship(back_populates="feedback_links")
    feedback_item: Mapped[FeedbackItem] = relationship(back_populates="theme_links")


class ThemeReviewAction(Base):
    __tablename__ = "theme_review_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    analysis_run_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True
    )
    theme_id: Mapped[str] = mapped_column(ForeignKey("themes.id", ondelete="CASCADE"), index=True)
    action_type: Mapped[str] = mapped_column(String(40))
    before_state: Mapped[dict] = mapped_column(JSON, default=dict)
    after_state: Mapped[dict] = mapped_column(JSON, default=dict)
    performed_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    analysis_run_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(240))
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="saved")
    created_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    methodology: Mapped[dict] = mapped_column(JSON, default=dict)

    snapshots: Mapped[list[ReportThemeSnapshot]] = relationship(
        cascade="all, delete-orphan", back_populates="report"
    )


class ReportThemeSnapshot(Base):
    __tablename__ = "report_theme_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), index=True)
    original_theme_id: Mapped[str] = mapped_column(String(36))
    theme_title: Mapped[str] = mapped_column(String(240))
    summary: Mapped[str] = mapped_column(Text)
    problem_statement: Mapped[str] = mapped_column(Text)
    pattern_type: Mapped[str] = mapped_column(String(30))
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_json: Mapped[list[dict]] = mapped_column(JSON, default=list)
    historical_comparison_json: Mapped[dict] = mapped_column(JSON, default=dict)

    report: Mapped[Report] = relationship(back_populates="snapshots")


class WorkflowLog(Base):
    __tablename__ = "workflow_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    analysis_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True
    )
    request_id: Mapped[str | None] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="INFO")
    step: Mapped[str | None] = mapped_column(String(80))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analysis_run: Mapped[AnalysisRun | None] = relationship(back_populates="logs")
