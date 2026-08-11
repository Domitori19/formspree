import json
import pytest
from src import server

async def test_list_all_forms_returns_registered_forms():
    res_str = await server.list_all_forms()
    res = json.loads(res_str)
    assert res["success"] is True
    assert res["total_forms_found"] == 43

async def test_list_all_forms_with_search_query():
    res_str = await server.list_all_forms(query="карпаты")
    res = json.loads(res_str)
    assert res["success"] is True
    assert res["total_forms_found"] > 0
    for form in res["forms"]:
        assert "karpaty" in form["name"].lower() or "карпат" in form["name"].lower()

async def test_leaderboard_uses_every_registered_form(monkeypatch):
    forms_count = 17
    fake_forms = [
        {"id": f"form-{index}", "name": f"Form {index}", "api_key": "test-key"}
        for index in range(forms_count)
    ]

    fetched_ids = []

    async def fake_fetch_all_submissions(form_id, since=None):
        fetched_ids.append(form_id)
        return {
            "success": True,
            "form_id": form_id,
            "submissions": [],
            "is_complete": True,
        }

    def fake_leaderboard(forms_data, period_days):
        return {
            "total_forms_analyzed": len(forms_data),
            "period_days": period_days,
        }

    monkeypatch.setattr(server, "find_forms", lambda query=None: fake_forms)
    monkeypatch.setattr(server, "fetch_all_submissions", fake_fetch_all_submissions)
    monkeypatch.setattr(server, "generate_cross_form_leaderboard", fake_leaderboard)

    result = json.loads(await server.compare_forms_leaderboard())

    assert result["leaderboard"]["total_forms_analyzed"] == forms_count
    assert len(fetched_ids) == forms_count

async def test_get_form_analytics_tool(monkeypatch):
    async def fake_fetch_all_submissions(form_id, since=None):
        return {
            "success": True,
            "submissions": [{"_date": "2026-08-10T12:00:00Z", "data": {"name": "Test"}}],
        }

    monkeypatch.setattr(server, "fetch_all_submissions", fake_fetch_all_submissions)
    res_str = await server.get_form_analytics("mdavnpok", period_days=30)
    res = json.loads(res_str)

    assert res["success"] is True
    assert res["analytics"]["total_submissions"] == 1

async def test_list_submissions_tool(monkeypatch):
    async def fake_fetch_submissions(form_id, limit, since=None):
        return {
            "success": True,
            "submissions": [{"_date": "2026-08-10T12:00:00Z", "data": {"name": "Test"}}],
        }

    monkeypatch.setattr(server, "fetch_submissions", fake_fetch_submissions)
    res_str = await server.list_submissions("mdavnpok", limit=10)
    res = json.loads(res_str)

    assert res["success"] is True
    assert res["total_fetched"] == 1
    assert "Test" in res["formatted_table"]

async def test_submit_form_tool(monkeypatch):
    async def fake_submit_to_formspree(data, form_id=None, email=None):
        return {"success": True, "status_code": 200, "data": {"ok": True}}

    monkeypatch.setattr(server, "submit_to_formspree", fake_submit_to_formspree)
    res_str = await server.submit_form({"name": "Ivan"}, form_id_or_name="mdavnpok", email="ivan@example.com")
    res = json.loads(res_str)

    assert res["success"] is True
    assert res["status_code"] == 200
