from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from dateutil import parser as date_parser

from ..config import Settings
from ..utils.text import content_hash, mask_pii, normalize_text, normalized_label

CANONICAL_FIELDS = {"feedback_text", "source", "user_type", "product_area", "date", "rating"}
REQUIRED_FIELDS = {"feedback_text", "source", "user_type", "product_area", "date"}
ALIASES = {
    "feedback_text": {"feedback_text", "feedback", "comment", "review_text", "narrative", "text"},
    "source": {"source", "channel", "origin", "submitted_via"},
    "user_type": {"user_type", "customer_type", "segment", "persona", "tags"},
    "product_area": {"product_area", "module", "feature", "category", "product"},
    "date": {"date", "created_at", "submitted_at", "date_received", "feedback_date"},
    "rating": {"rating", "stars", "score"},
    "external_id": {"external_id", "id", "feedback_id", "complaint_id"},
}


@dataclass
class ParsedRow:
    source_row: int
    external_id: str | None
    feedback_text_original: str
    feedback_text_normalized: str
    feedback_text_masked: str
    source: str
    user_type: str
    product_area: str
    feedback_date: date
    rating: float | None
    content_hash: str
    duplicate_group_id: str | None = None


@dataclass
class ParseResult:
    rows: list[ParsedRow] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)
    total_rows: int = 0
    column_mapping: dict[str, str] = field(default_factory=dict)
    file_sha256: str = ""

    @property
    def error_count(self) -> int:
        return len({issue["row"] for issue in self.issues if issue["severity"] == "error"})


def _canonical_header(value: str) -> str:
    return normalize_text(value).casefold().replace(" ", "_").replace("-", "_")


def infer_mapping(headers: list[str]) -> dict[str, str]:
    normalized = {_canonical_header(header): header for header in headers}
    mapping: dict[str, str] = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapping[canonical] = normalized[alias]
                break
    return mapping


def _issue(row: int, field_name: str, code: str, message: str, value: object = None, *, severity: str = "error") -> dict:
    return {
        "row": row,
        "field": field_name,
        "code": code,
        "message": message,
        "value": None if value is None else str(value)[:300],
        "severity": severity,
    }


def _parse_date(value: str) -> date:
    parsed = date_parser.parse(value, fuzzy=False)
    result = parsed.date()
    if result > datetime.now(timezone.utc).date():
        raise ValueError("future_date")
    return result


def _parse_rating(value: str) -> float | None:
    if not normalize_text(value):
        return None
    rating = float(value)
    if rating < 0 or rating > 10:
        raise ValueError("rating_out_of_range")
    return rating


def parse_csv(content: bytes, settings: Settings, override_mapping: dict[str, str] | None = None) -> ParseResult:
    result = ParseResult(file_sha256=hashlib.sha256(content).hexdigest())
    if len(content) > settings.max_upload_bytes:
        result.issues.append(_issue(0, "file", "file_too_large", "CSV exceeds upload size limit."))
        return result

    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        result.issues.append(_issue(0, "file", "invalid_encoding", "CSV must be UTF-8 encoded."))
        return result

    try:
        dialect = csv.Sniffer().sniff(decoded[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(decoded), dialect=dialect)
    headers = reader.fieldnames or []
    mapping = override_mapping or infer_mapping(headers)
    result.column_mapping = mapping
    unknown_headers = sorted(set(mapping.values()) - set(headers))
    if unknown_headers:
        for header in unknown_headers:
            result.issues.append(
                _issue(0, "column_mapping", "unknown_mapped_column", f"Mapped column '{header}' is not present in the CSV.")
            )
        return result

    missing = sorted(REQUIRED_FIELDS - set(mapping))
    if missing:
        for field_name in missing:
            result.issues.append(
                _issue(0, field_name, "missing_required_column", f"Required column '{field_name}' is missing.")
            )
        return result

    hash_counts: dict[str, int] = {}
    candidate_rows: list[ParsedRow] = []
    for source_row, raw in enumerate(reader, start=2):
        result.total_rows += 1
        if result.total_rows > settings.max_csv_rows:
            result.issues.append(
                _issue(source_row, "file", "too_many_rows", f"CSV exceeds {settings.max_csv_rows} rows.")
            )
            break

        def get(name: str) -> str:
            header = mapping.get(name)
            return "" if not header else str(raw.get(header) or "")

        issue_start = len(result.issues)
        feedback_original = normalize_text(get("feedback_text"))
        if len(feedback_original) < 8:
            result.issues.append(
                _issue(source_row, "feedback_text", "text_too_short", "Feedback must contain at least 8 characters.", feedback_original)
            )
        if len(feedback_original) > 20_000:
            result.issues.append(
                _issue(source_row, "feedback_text", "text_too_long", "Feedback exceeds 20,000 characters.")
            )

        source = normalized_label(get("source"))
        user_type = normalized_label(get("user_type"))
        product_area = normalized_label(get("product_area"))
        for field_name, value in (("source", source), ("user_type", user_type), ("product_area", product_area)):
            if not value:
                result.issues.append(_issue(source_row, field_name, "required_value", f"{field_name} is required."))

        feedback_date: date | None = None
        try:
            feedback_date = _parse_date(get("date"))
        except (ValueError, OverflowError, TypeError):
            result.issues.append(
                _issue(source_row, "date", "invalid_date", "Date is invalid or in the future.", get("date"))
            )

        rating: float | None = None
        try:
            rating = _parse_rating(get("rating"))
        except (ValueError, TypeError):
            result.issues.append(
                _issue(source_row, "rating", "invalid_rating", "Rating must be between 0 and 10.", get("rating"))
            )

        row_has_error = any(
            issue["severity"] == "error" for issue in result.issues[issue_start:]
        )
        if row_has_error or feedback_date is None:
            continue

        normalized = normalize_text(feedback_original)
        item_hash = content_hash(normalized)
        hash_counts[item_hash] = hash_counts.get(item_hash, 0) + 1
        candidate_rows.append(
            ParsedRow(
                source_row=source_row,
                external_id=normalize_text(get("external_id")) or None,
                feedback_text_original=feedback_original,
                feedback_text_normalized=normalized,
                feedback_text_masked=mask_pii(normalized),
                source=source,
                user_type=user_type,
                product_area=product_area,
                feedback_date=feedback_date,
                rating=rating,
                content_hash=item_hash,
            )
        )

    duplicate_hashes = {item_hash for item_hash, count in hash_counts.items() if count > 1}
    for row in candidate_rows:
        row.duplicate_group_id = row.content_hash if row.content_hash in duplicate_hashes else None
        if row.duplicate_group_id:
            result.issues.append(
                _issue(row.source_row, "feedback_text", "exact_duplicate", "Exact duplicate feedback detected.", severity="warning")
            )
    result.rows = candidate_rows
    return result
