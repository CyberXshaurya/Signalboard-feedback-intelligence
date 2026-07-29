"""Run the full engine on a CSV and write a compact verification report."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from feedback_intelligence_engine.config import Settings
from feedback_intelligence_engine.db import Base
from feedback_intelligence_engine.models import AnalysisRun, Dataset, FeedbackItem, Project, Theme
from feedback_intelligence_engine.services.analytics import calculate_theme_metrics
from feedback_intelligence_engine.services.csv_ingestion import parse_csv
from feedback_intelligence_engine.services.workflow import execute_analysis


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--output", default="data/engine_smoke_summary.json")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as temp_dir:
        database_path = Path(temp_dir) / "smoke.db"
        database_url = f"sqlite:///{database_path}"
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        settings = Settings(
            database_url=database_url,
            synthesis_provider="heuristic",
            embedding_provider="tfidf",
            max_csv_rows=10_000,
        )
        with Session() as db:
            project = Project(owner_id="smoke-test", name="Real-data smoke test")
            db.add(project)
            db.flush()
            parsed = parse_csv(Path(args.csv_path).read_bytes(), settings)
            dataset = Dataset(
                project_id=project.id,
                file_name=Path(args.csv_path).name,
                file_sha256=parsed.file_sha256,
                total_rows=parsed.total_rows,
                valid_rows=len(parsed.rows),
                invalid_rows=parsed.error_count,
                status="ready" if parsed.rows else "validation_failed",
                validation_errors=parsed.issues,
                column_mapping=parsed.column_mapping,
            )
            db.add(dataset)
            db.flush()
            for row in parsed.rows:
                db.add(FeedbackItem(dataset_id=dataset.id, **row.__dict__))
            db.commit()
            run = AnalysisRun(dataset_id=dataset.id)
            db.add(run)
            db.commit()
            db.refresh(run)
            execute_analysis(db, run, settings)
            themes = list(
                db.scalars(
                    select(Theme)
                    .where(Theme.analysis_run_id == run.id)
                    .order_by(Theme.created_at)
                )
            )
            theme_summaries = []
            for theme in themes:
                metrics = calculate_theme_metrics(db, theme.id)
                theme_summaries.append(
                    {
                        "title": theme.title,
                        "pattern_type": theme.pattern_type,
                        "confidence": theme.confidence,
                        "feedback_count": metrics["feedback_count"],
                        "unique_feedback_count": metrics["unique_feedback_count"],
                        "primary_source": metrics["source_distribution"][0]["value"]
                        if metrics["source_distribution"]
                        else None,
                    }
                )
            report = {
                "input_file": Path(args.csv_path).name,
                "total_rows": parsed.total_rows,
                "valid_rows": len(parsed.rows),
                "invalid_rows": parsed.error_count,
                "warnings": len([issue for issue in parsed.issues if issue["severity"] == "warning"]),
                "run_status": run.status,
                "synthesis_provider": run.provider,
                "cluster_diagnostics": run.diagnostics.get("clustering", {}),
                "theme_count": len(themes),
                "largest_theme": max((item["feedback_count"] for item in theme_summaries), default=0),
                "themes": sorted(
                    theme_summaries, key=lambda item: (-item["feedback_count"], item["title"])
                ),
            }
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps({key: value for key, value in report.items() if key != "themes"}, indent=2))


if __name__ == "__main__":
    main()
