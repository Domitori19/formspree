"""
МОДУЛЬ MCP СЕРВЕРА ДЛЯ CLAUDE DESKTOP (src/server.py)
----------------------------------------------------
Предоставляет 5 инструментов для Claude Desktop:
1. list_all_forms — просмотр и поиск подключенных 43 форм.
2. compare_forms_leaderboard — Сводный Лидерборд по всем направлениям.
3. get_form_analytics — детализация и график по любой из 43 форм.
4. list_submissions — вывод таблицы лидов по любой форме.
5. submit_form — отправка данных в форму.
"""

import sys
import os
import json
import asyncio
from typing import Dict, Any, Optional, List

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from mcp.server import MCPServer as FastMCP

from src.config import (
    FORMS_BY_ID,
    find_forms,
    get_form_info
)
from src.client import (
    fetch_submissions,
    fetch_all_submissions,
    submit_to_formspree
)
from src.analytics import (
    generate_analytics,
    format_markdown_table,
    generate_cross_form_leaderboard
)

# 1. Создаем экземпляр FastMCP Сервера
mcp = FastMCP(
    name="Formspree 43-Forms Multi-Server",
    instructions="MCP Сервер для аналитики и управления 43 турами и направлениями."
)

@mcp.tool()
async def list_all_forms(query: Optional[str] = None) -> str:
    """
    Инструмент 1: Возвращает список всех 43 подключенных форм.
    Поддерживает поиск по слову (например: 'карпаты', 'италия', 'лаванда').
    """
    matched_forms = find_forms(query)
    result_list = [{"id": f["id"], "name": f["name"]} for f in matched_forms]

    return json.dumps({
        "success": True,
        "total_forms_found": len(result_list),
        "search_query": query,
        "forms": result_list
    }, indent=2, ensure_ascii=False)

@mcp.tool()
async def compare_forms_leaderboard(
    period_days: int = 30,
    query: Optional[str] = None
) -> str:
    """
    Инструмент 2: Строит СВОДНЫЙ РЕЙТИНГ (ЛИДЕРБОРД) по всем 43 турам.
    Показывает, какая форма на 1 месте, а где продажи просели.
    """
    target_forms = find_forms(query)
    semaphore = asyncio.Semaphore(5)

    async def fetch_one_form(form_item):
        fid = form_item["id"]
        fname = form_item["name"]
        async with semaphore:
            res = await fetch_all_submissions(form_id=fid)

        if not res.get("success"):
            return {
                "success": False,
                "form_id": fid,
                "form_name": fname,
                "error": res.get("error", "Ошибка загрузки"),
                "submissions": res.get("submissions", [])
            }

        return {
            "success": True,
            "form_id": fid,
            "form_name": fname,
            "is_complete": res.get("is_complete", True),
            "submissions": res.get("submissions", [])
        }

    tasks = [fetch_one_form(form) for form in target_forms]
    forms_data = await asyncio.gather(*tasks)

    leaderboard = generate_cross_form_leaderboard(forms_data, period_days=period_days)

    return json.dumps({
        "success": True,
        "leaderboard": leaderboard
    }, indent=2, ensure_ascii=False)

@mcp.tool()
async def get_form_analytics(
    form_id_or_name: Optional[str] = None,
    period_days: int = 30,
    since: Optional[str] = None
) -> str:
    """
    Инструмент 3: Возвращает детализированную аналитику и график по любой из 43 форм.
    Можно передавать как ID ('xoeaadqn'), так и Название ('balkany' или 'карпаты').
    """
    form_info = get_form_info(form_id_or_name)
    clean_id = form_info["id"]
    form_name = form_info["name"]

    res = await fetch_all_submissions(form_id=clean_id, since=since)
    if not res.get("success"):
        return json.dumps(res, indent=2, ensure_ascii=False)

    submissions_list = res.get("submissions", [])
    analytics_result = generate_analytics(submissions=submissions_list, period_days=period_days)

    return json.dumps({
        "success": True,
        "form_id": clean_id,
        "form_name": form_name,
        "analytics": analytics_result
    }, indent=2, ensure_ascii=False)

@mcp.tool()
async def list_submissions(
    form_id_or_name: Optional[str] = None,
    limit: int = 50,
    since: Optional[str] = None
) -> str:
    """
    Инструмент 4: Возвращает таблицу лидов по выбранной форме.
    """
    form_info = get_form_info(form_id_or_name)
    clean_id = form_info["id"]
    form_name = form_info["name"]

    res = await fetch_submissions(form_id=clean_id, limit=limit, since=since)
    if not res.get("success"):
        return json.dumps(res, indent=2, ensure_ascii=False)

    submissions_raw = res.get("submissions", [])
    if isinstance(submissions_raw, dict) and "submissions" in submissions_raw:
        submissions_list = submissions_raw["submissions"]
    elif isinstance(submissions_raw, list):
        submissions_list = submissions_raw
    else:
        submissions_list = []

    table_markdown = format_markdown_table(submissions_list)

    return json.dumps({
        "success": True,
        "form_id": clean_id,
        "form_name": form_name,
        "total_fetched": len(submissions_list),
        "formatted_table": table_markdown,
        "submissions": submissions_list
    }, indent=2, ensure_ascii=False)

@mcp.tool()
async def submit_form(
    data: Dict[str, Any],
    form_id_or_name: Optional[str] = None,
    email: Optional[str] = None
) -> str:
    """
    Инструмент 5: Публичная отправка формы.
    """
    res = await submit_to_formspree(data=data, form_id=form_id_or_name, email=email)
    return json.dumps(res, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    # Выбор режима работы: STDIO (по умолчанию) или SSE HTTP сервер на выбранном порту
    transport = os.getenv("TRANSPORT", "stdio").lower()
    if "--sse" in sys.argv or transport == "sse":
        port = int(os.getenv("PORT", "9090"))
        host = os.getenv("HOST", "0.0.0.0")
        print(f"Запуск MCP сервера в режиме SSE на http://{host}:{port}/sse")
        mcp.run(transport="sse", host=host, port=port)
    else:
        mcp.run()
