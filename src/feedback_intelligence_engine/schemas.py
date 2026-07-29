from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class ProjectOut(ORMModel):
    id: str
    owner_id: str
    name: str
    description: str | None
    created_at: datetime


class HistoricalThemeCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=5, max_length=5000)
    product_area: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=5000)
    active_from: date | None = None
    active_until: date | None = None


class HistoricalThemeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, min_length=5, max_length=5000)
    product_area: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=5000)
    active_from: date | None = None
    active_until: date | None = None


class HistoricalThemeOut(ORMModel):
    id: str
    title: str
    description: str
    product_area: str | None
    notes: str | None
    active_from: date | None
    active_until: date | None


class ValidationIssue(BaseModel):
    row: int
    field: str
    code: str
    message: str
    value: str | None = None
    severity: Literal["error", "warning"] = "error"


class DatasetOut(ORMModel):
    id: str
    project_id: str
    file_name: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    status: str
    validation_errors: list[dict]
    column_mapping: dict
    created_at: datetime


class AnalysisRunOut(ORMModel):
    id: str
    dataset_id: str
    status: str
    provider: str
    model: str | None
    prompt_version: str
    progress_percent: int
    current_step: str
    started_at: datetime | None
    completed_at: datetime | None
    failure_code: str | None
    failure_message: str | None
    diagnostics: dict


class FeedbackEvidence(ORMModel):
    id: str
    source_row: int
    feedback_text_original: str
    source: str
    user_type: str
    product_area: str
    feedback_date: date
    rating: float | None
    membership_score: float
    is_primary_evidence: bool
    assigned_by: str


class DistributionItem(BaseModel):
    value: str
    count: int
    percentage: float


class TimeBucket(BaseModel):
    period: str
    count: int


class RatingSummary(BaseModel):
    rated_count: int
    unrated_count: int
    average: float | None
    distribution: dict[str, int]


class ThemeMetrics(BaseModel):
    feedback_count: int
    unique_feedback_count: int
    duplicate_count: int
    source_distribution: list[DistributionItem]
    user_type_distribution: list[DistributionItem]
    product_area_distribution: list[DistributionItem]
    frequency_over_time: list[TimeBucket]
    rating_summary: RatingSummary


class ThemeOut(ORMModel):
    id: str
    analysis_run_id: str
    title: str
    summary: str
    problem_statement: str
    pattern_type: str
    confidence: float
    uncertainty_reason: str | None
    status: str
    historical_relationship: str
    historical_theme_id: str | None
    historical_similarity_score: float | None
    merged_into_theme_id: str | None
    approved_by: str | None
    approved_at: datetime | None
    rejected_at: datetime | None
    rejection_reason: str | None
    created_at: datetime


class ThemeDetail(BaseModel):
    theme: ThemeOut
    metrics: ThemeMetrics
    evidence: list[FeedbackEvidence]
    historical_theme: HistoricalThemeOut | None = None


class ThemeCard(BaseModel):
    theme: ThemeOut
    metrics: ThemeMetrics


class RenameThemeRequest(BaseModel):
    title: str = Field(min_length=2, max_length=240)


class EditThemeRequest(BaseModel):
    summary: str | None = Field(default=None, min_length=5, max_length=5000)
    problem_statement: str | None = Field(default=None, min_length=5, max_length=5000)


class MergeThemesRequest(BaseModel):
    theme_ids: list[str] = Field(min_length=2, max_length=20)
    title: str = Field(min_length=2, max_length=240)
    summary: str = Field(min_length=5, max_length=5000)
    problem_statement: str = Field(min_length=5, max_length=5000)


class SplitThemeRequest(BaseModel):
    feedback_item_ids: list[str] = Field(min_length=1)
    new_title: str = Field(min_length=2, max_length=240)
    new_summary: str = Field(min_length=5, max_length=5000)
    new_problem_statement: str = Field(min_length=5, max_length=5000)


class RejectThemeRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=1000)


class ReportCreate(BaseModel):
    title: str = Field(min_length=2, max_length=240)


class ReportOut(ORMModel):
    id: str
    project_id: str
    analysis_run_id: str
    title: str
    version: int
    status: str
    created_by: str
    created_at: datetime
    methodology: dict


class ReportSnapshotOut(ORMModel):
    original_theme_id: str
    theme_title: str
    summary: str
    problem_statement: str
    pattern_type: str
    metrics_json: dict
    evidence_json: list[dict]
    historical_comparison_json: dict


class ReportDetail(BaseModel):
    report: ReportOut
    themes: list[ReportSnapshotOut]


class ThemeActionOut(ORMModel):
    id: str
    analysis_run_id: str
    theme_id: str
    action_type: str
    before_state: dict
    after_state: dict
    performed_by: str
    created_at: datetime


class WorkflowLogOut(ORMModel):
    id: str
    analysis_run_id: str | None
    request_id: str | None
    event_type: str
    severity: str
    step: str | None
    duration_ms: int | None
    metadata_json: dict
    created_at: datetime


class RunSummary(BaseModel):
    run_id: str
    total_feedback: int
    assigned_feedback: int
    coverage_percentage: float
    theme_count: int
    status_distribution: dict[str, int]
    pattern_distribution: dict[str, int]
    approved_feedback_count: int
    rejected_feedback_count: int


class ProviderSelfTestOut(BaseModel):
    status: Literal["ok", "degraded", "unavailable"]
    provider: str
    model: str | None
    llm_operational: bool
    latency_ms: int
    message: str
    request_id: str | None = None


class HealthOut(BaseModel):
    status: str
    database: str
    ai_configured: bool
    synthesis_provider: str
    configured_llm_providers: list[str] = []
    embedding_provider: str = "tfidf"
    version: str
