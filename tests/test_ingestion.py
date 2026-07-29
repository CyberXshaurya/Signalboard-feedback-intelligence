from feedback_intelligence_engine.config import Settings
from feedback_intelligence_engine.services.csv_ingestion import parse_csv


def test_alias_mapping_and_duplicate_warning():
    content = b"comment,channel,segment,module,submitted_at,stars\nSlow export,Support,Pro,Reports,2025-01-01,2\nSlow export,Support,Pro,Reports,2025-01-02,2\n"
    result = parse_csv(content, Settings())
    assert len(result.rows) == 2
    assert result.column_mapping["feedback_text"] == "comment"
    assert all(row.duplicate_group_id for row in result.rows)
    assert any(issue["code"] == "exact_duplicate" for issue in result.issues)


def test_missing_column_is_fatal():
    content = b"feedback_text,source,user_type,date\nThe export is too slow,Support,Pro,2025-01-01\n"
    result = parse_csv(content, Settings())
    assert not result.rows
    assert any(issue["code"] == "missing_required_column" for issue in result.issues)


def test_invalid_rows_do_not_block_valid_rows():
    content = b"feedback_text,source,user_type,product_area,date,rating\nExport takes several minutes,Support,Pro,Reports,2025-01-01,2\nBad,Support,Pro,Reports,not-a-date,99\n"
    result = parse_csv(content, Settings())
    assert len(result.rows) == 1
    assert result.error_count == 1
