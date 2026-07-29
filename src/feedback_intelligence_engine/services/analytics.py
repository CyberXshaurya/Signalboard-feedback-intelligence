from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import FeedbackItem, ThemeFeedback


def _distribution(values: list[str]) -> list[dict]:
    total = len(values)
    counts = Counter(values)
    return [
        {"value": value, "count": count, "percentage": round((count / total) * 100, 2)}
        for value, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    ] if total else []


def _time_granularity(items: list[FeedbackItem]) -> str:
    if not items:
        return "month"
    span = (max(item.feedback_date for item in items) - min(item.feedback_date for item in items)).days
    if span <= 45:
        return "day"
    if span <= 240:
        return "week"
    return "month"


def _period_key(item: FeedbackItem, granularity: str) -> str:
    value = item.feedback_date
    if granularity == "day":
        return value.isoformat()
    if granularity == "week":
        year, week, _ = value.isocalendar()
        return f"{year}-W{week:02d}"
    return f"{value.year}-{value.month:02d}"


def calculate_theme_metrics(db: Session, theme_id: str) -> dict:
    items = list(
        db.scalars(
            select(FeedbackItem)
            .join(ThemeFeedback, ThemeFeedback.feedback_item_id == FeedbackItem.id)
            .where(ThemeFeedback.theme_id == theme_id)
            .order_by(FeedbackItem.feedback_date, FeedbackItem.source_row)
        )
    )
    hashes = [item.content_hash for item in items]
    unique_count = len(set(hashes))
    granularity = _time_granularity(items)
    periods = Counter(_period_key(item, granularity) for item in items)
    rated = [item.rating for item in items if item.rating is not None]
    rating_distribution = Counter(str(item.rating) for item in items if item.rating is not None)
    return {
        "feedback_count": len(items),
        "unique_feedback_count": unique_count,
        "duplicate_count": len(items) - unique_count,
        "source_distribution": _distribution([item.source for item in items]),
        "user_type_distribution": _distribution([item.user_type for item in items]),
        "product_area_distribution": _distribution([item.product_area for item in items]),
        "frequency_over_time": [
            {"period": period, "count": count} for period, count in sorted(periods.items())
        ],
        "rating_summary": {
            "rated_count": len(rated),
            "unrated_count": len(items) - len(rated),
            "average": round(sum(rated) / len(rated), 2) if rated else None,
            "distribution": dict(sorted(rating_distribution.items())),
        },
    }
