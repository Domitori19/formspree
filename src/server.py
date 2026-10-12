"""
MCP-СЕРВЕР FORMSPREE (src/server.py)
------------------------------------
Инструменты:
1. list_all_forms — просмотр и поиск подключённых форм.
2. compare_forms_leaderboard — сводный лидерборд по всем направлениям.
3. get_form_analytics — детализация и график по любой форме.
4. list_submissions — таблица лидов по любой форме.
5. submit_form — отправка данных в форму (только если ENABLE_SUBMIT_FORM=true).

Режимы запуска:
- STDIO (по умолчанию) — для локального подключения через `docker exec`.
- Streamable HTTP (TRANSPORT=streamable-http или --http) — для подключения по сети.
  Доступ защищается секретным путём: MCP_PATH=/mcp/<длинный-случайный-код>.
"""

import sys
import os
import json
import asyncio
from typing import Dict, Any, Optional

from mcp.server import MCPServer

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
from starlette.requests import Request
from starlette.responses import JSONResponse

# Настройки сетевого режима (берутся из переменных окружения)
MCP_PATH = os.getenv("MCP_PATH", "/mcp").strip() or "/mcp"
ENABLE_SUBMIT_FORM = os.getenv("ENABLE_SUBMIT_FORM", "false").strip().lower() in ("1", "true", "yes")

mcp = MCPServer(
    name="Formspree Forms Analytics",
    instructions="Аналитика заявок Formspree по всем подключённым турам и направлениям."
)

@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health_check(_: Request) -> JSONResponse:
    """Проверка состояния для Docker и прокси. Не раскрывает данных."""
    return JSONResponse({
        "status": "ok",
        "service": "formspree-mcp",
        "transport": "streamable-http",
        "forms_loaded": len(FORMS_BY_ID)
    })

@mcp.tool()
async def list_all_forms(query: Optional[str] = None) -> str:
    """
    Инструмент 1: Возвращает список всех подключённых форм.
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
    Инструмент 2: Строит сводный рейтинг (лидерборд) по всем турам.
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
    Инструмент 3: Возвращает детализированную аналитику и график по любой форме.
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

# Отправка заявок выключена по умолчанию, чтобы через сервер нельзя было слать фейковые лиды
if ENABLE_SUBMIT_FORM:
    mcp.tool()(submit_form)

if __name__ == "__main__":
    # Выбор режима работы: STDIO (по умолчанию) или Streamable HTTP на выбранном порту
    transport = os.getenv("TRANSPORT", "stdio").lower()
    if "--http" in sys.argv or transport in ("http", "streamable-http"):
        port = int(os.getenv("PORT", "9090"))
        host = os.getenv("HOST", "0.0.0.0")
        # Секретный путь не печатаем целиком, чтобы он не попал в логи
        path_mode = "открытый путь /mcp — только для локального запуска" if MCP_PATH == "/mcp" else "секретный путь /mcp/***"
        print(f"Запуск MCP сервера (streamable-http) на http://{host}:{port} ({path_mode})")
        mcp.run(
            transport="streamable-http",
            host=host,
            port=port,
            streamable_http_path=MCP_PATH,
            stateless_http=True,
            json_response=True
        )
    else:
        mcp.run()
