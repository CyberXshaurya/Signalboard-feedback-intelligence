"""Download and transform a small real CFPB complaint sample into the engine schema."""

from __future__ import annotations

import argparse
import csv
import io
from pathlib import Path

import httpx

API_URL = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/cfpb_feedback_sample.csv")
    parser.add_argument("--input", help="Optional previously downloaded CFPB CSV")
    parser.add_argument("--size", type=int, default=250)
    parser.add_argument("--date-min", default="2025-01-01")
    parser.add_argument("--date-max", default="2025-12-31")
    args = parser.parse_args()

    params = {
        "date_received_min": args.date_min,
        "date_received_max": args.date_max,
        "field": "all",
        "format": "csv",
        "no_aggs": "true",
        "size": str(args.size),
        "sort": "created_date_desc",
        "has_narrative": "true",
    }
    if args.input:
        raw_text = Path(args.input).read_text(encoding="utf-8-sig")
    else:
        response = httpx.get(API_URL, params=params, timeout=60, follow_redirects=True)
        response.raise_for_status()
        raw_text = response.text
    source = csv.DictReader(io.StringIO(raw_text))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "feedback_text",
                "source",
                "user_type",
                "product_area",
                "date",
                "rating",
                "external_id",
            ],
        )
        writer.writeheader()
        count = 0
        for row in source:
            narrative = (row.get("Consumer complaint narrative") or "").strip()
            if not narrative:
                continue
            writer.writerow(
                {
                    "feedback_text": narrative,
                    "source": row.get("Submitted via") or "Unknown",
                    "user_type": row.get("Tags") or "Unspecified",
                    "product_area": " — ".join(part for part in [row.get("Product") or "Unknown", row.get("Issue") or ""] if part),
                    "date": row.get("Date received") or "",
                    "rating": "",
                    "external_id": row.get("Complaint ID") or "",
                }
            )
            count += 1
            if count >= args.size:
                break
    print(f"Wrote {count} real complaint narratives to {output}")


if __name__ == "__main__":
    main()
