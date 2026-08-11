import pytest
from datetime import datetime, timezone, timedelta
from src.analytics import (
    compare_periods,
    format_markdown_table,
    generate_analytics,
    generate_cross_form_leaderboard,
    strip_ansi_codes,
    unnest_submission,
    create_empty_analytics
)

def test_unnest_submission_flattens_data_dict():
    raw = {
        "_date": "2026-08-10T10:00:00Z",
        "data": {
            "name": "Alice",
            "email": "alice@example.com"
        }
    }
    flat = unnest_submission(raw)
    assert flat["_date"] == "2026-08-10T10:00:00Z"
    assert flat["name"] == "Alice"
    assert flat["email"] == "alice@example.com"

def test_create_empty_analytics():
    res = create_empty_analytics(period_days=30, message="Тест пустых данных")
    assert res["total_submissions"] == 0
    assert res["period_days"] == 30
    assert res["message"] == "Тест пустых данных"
    assert res["ascii_chart"] == "Нет данных."

def test_period_days_filtering():
    now = datetime.now(timezone.utc)
    recent_date = (now - timedelta(days=2)).isoformat()
    old_date = (now - timedelta(days=40)).isoformat()

    mock_subs = [
        {"_date": recent_date, "data": {"name": "Recent User"}},
        {"_date": old_date, "data": {"name": "Old User"}}
    ]

    result = generate_analytics(mock_subs, period_days=7)
    assert result["total_submissions"] == 1
    assert len(result["top_fields"]) > 0
    assert result["top_fields"][0]["field_name"] == "name"

def test_daily_averages_use_full_period_and_active_days():
    now = datetime.now(timezone.utc).isoformat()
    mock_subs = [
        {"_date": now, "data": {"name": f"Lead {index}"}}
        for index in range(30)
    ]

    result = generate_analytics(mock_subs, period_days=30)
    assert result["avg_submissions_per_day"] == 1.0
    assert result["avg_submissions_per_active_day"] == 30.0

def test_strip_ansi_and_chart_generation():
    raw_text = "\x1b[31mHello World\x1b[0m"
    clean_text = strip_ansi_codes(raw_text)
    assert "\x1b" not in clean_text
    assert clean_text == "Hello World"

def test_format_markdown_table():
    mock_subs = [
        {"_date": "2026-08-10", "data": {"name": "Bob", "phone": "+12345"}}
    ]
    table_str = format_markdown_table(mock_subs)
    assert "Bob" in table_str
    assert "+12345" in table_str

def test_compare_periods_growth_status():
    now = datetime.now(timezone.utc)
    submissions = [
        {"_date": (now - timedelta(days=1)).isoformat()} for _ in range(20)
    ] + [
        {"_date": (now - timedelta(days=8)).isoformat()} for _ in range(5)
    ]

    result = compare_periods(submissions, period_days=7)
    assert result["current_submissions"] == 20
    assert result["previous_submissions"] == 5
    assert result["change_percent"] == 300.0
    assert result["status"] == "growth"

def test_compare_periods_decline_status():
    now = datetime.now(timezone.utc)
    submissions = [
        {"_date": (now - timedelta(days=1)).isoformat()} for _ in range(2)
    ] + [
        {"_date": (now - timedelta(days=8)).isoformat()} for _ in range(10)
    ]

    result = compare_periods(submissions, period_days=7)
    assert result["current_submissions"] == 2
    assert result["previous_submissions"] == 10
    assert result["change_percent"] == -80.0
    assert result["status"] == "decline"

def test_compare_periods_inactive_status():
    now = datetime.now(timezone.utc)
    submissions = [
        {"_date": (now - timedelta(days=8)).isoformat()} for _ in range(10)
    ]

    result = compare_periods(submissions, period_days=7)
    assert result["current_submissions"] == 0
    assert result["status"] == "inactive"

def test_failed_form_is_not_counted_as_zero_leads():
    result = generate_cross_form_leaderboard([
        {
            "success": False,
            "form_id": "broken-form",
            "form_name": "Broken form",
            "error": "Timeout",
        }
    ])

    assert result["total_forms_analyzed"] == 0
    assert result["total_forms_failed"] == 1
    assert result["ranking"] == []
