"""
МОДУЛЬ СЕТЕВОГО КЛИЕНТА (src/client.py)
--------------------------------------
Этот файл отвечает только за HTTP-запросы к Formspree API:
1. Загрузка страниц лидов (fetch_submissions).
2. Автоматическая пагинация всех страниц (fetch_all_submissions).
3. Публичная отправка данных (submit_to_formspree).
"""

import httpx
from typing import Dict, Any, Optional, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config import (
    FORMSPREE_BASE_URL,
    get_form_info
)

def get_auth_headers(api_key: Optional[str] = None) -> Dict[str, str]:
    """Формирует заголовки HTTP с Bearer API-ключом."""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Formspree-MCP/2.0",
    }
    key_to_use = (api_key or "").strip()
    if key_to_use:
        headers["Authorization"] = f"Bearer {key_to_use}"
    return headers

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
    reraise=True
)
async def _execute_http_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    client: Optional[httpx.AsyncClient] = None
) -> httpx.Response:
    """Выполняет HTTP-запрос. При обрыве сети сделает до 3 повторных попыток."""
    if client is not None:
        return await client.request(method=method, url=url, headers=headers, params=params, json=json_data)

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as temp_client:
        return await temp_client.request(method=method, url=url, headers=headers, params=params, json=json_data)

async def fetch_submissions(
    form_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    since: Optional[str] = None,
    _client: Optional[httpx.AsyncClient] = None
) -> Dict[str, Any]:
    """Загружает одну страницу лидов для выбранной формы."""
    try:
        if limit <= 0 or offset < 0:
            raise ValueError("Параметр limit должен быть > 0, а offset >= 0")

        form = get_form_info(form_id)
        clean_id = form["id"]
        url = f"{FORMSPREE_BASE_URL}/api/0/forms/{clean_id}/submissions"
        headers = get_auth_headers(form.get("api_key"))

        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if since:
            params["since"] = since

        response = await _execute_http_request(
            method="GET",
            url=url,
            headers=headers,
            params=params,
            client=_client
        )

        if response.status_code != 200:
            return {
                "success": False,
                "status_code": response.status_code,
                "error": response.text,
                "form_id": clean_id,
                "form_name": form.get("name")
            }

        return {
            "success": True,
            "form_id": clean_id,
            "form_name": form.get("name"),
            "submissions": response.json()
        }
    except (httpx.HTTPError, ValueError) as exc:
        return {"success": False, "status_code": 500, "error": str(exc)}

async def fetch_all_submissions(
    form_id: Optional[str] = None,
    since: Optional[str] = None,
    max_records: int = 5000
) -> Dict[str, Any]:
    """Загружает все страницы лидов в цикле до конца или до max_records."""
    try:
        if max_records <= 0:
            raise ValueError("max_records должен быть больше 0")
        form = get_form_info(form_id)
    except ValueError as exc:
        return {"success": False, "status_code": 400, "error": str(exc)}

    all_submissions: List[Dict[str, Any]] = []
    offset = 0
    page_size = 100
    is_truncated = False

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http_session:
        while len(all_submissions) < max_records:
            res = await fetch_submissions(
                form_id=form["id"],
                limit=page_size,
                offset=offset,
                since=since,
                _client=http_session
            )

            if not res.get("success"):
                return {
                    **res,
                    "form_id": form["id"],
                    "form_name": form["name"],
                    "partial": bool(all_submissions),
                    "total_fetched": len(all_submissions),
                    "submissions": all_submissions
                }

            submissions_raw = res.get("submissions", [])
            if isinstance(submissions_raw, dict):
                page = submissions_raw.get("submissions", [])
            elif isinstance(submissions_raw, list):
                page = submissions_raw
            else:
                page = []

            if not page:
                break

            remaining_needed = max_records - len(all_submissions)
            all_submissions.extend(page[:remaining_needed])

            if len(page) > remaining_needed or (len(all_submissions) >= max_records and len(page) == page_size):
                is_truncated = True
                break

            if len(page) < page_size:
                break

            offset += len(page)

    return {
        "success": True,
        "form_id": form["id"],
        "form_name": form["name"],
        "total_fetched": len(all_submissions),
        "is_complete": not is_truncated,
        "submissions": all_submissions
    }

async def submit_to_formspree(
    data: Dict[str, Any],
    form_id: Optional[str] = None,
    email: Optional[str] = None
) -> Dict[str, Any]:
    """Публично отправляет заявку в Formspree."""
    try:
        form = get_form_info(form_id)
        url = f"{FORMSPREE_BASE_URL}/f/{form['id']}"

        payload = dict(data)
        if email and "_replyto" not in payload and "email" not in payload:
            payload["_replyto"] = email

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Formspree-MCP/2.0"
        }
        response = await _execute_http_request(method="POST", url=url, headers=headers, json_data=payload)

        try:
            response_json = response.json()
        except Exception:
            response_json = {"text": response.text}

        if response.status_code >= 400:
            return {"success": False, "status_code": response.status_code, "error": response_json}

        return {"success": True, "status_code": response.status_code, "data": response_json}
    except (httpx.HTTPError, ValueError) as exc:
        return {"success": False, "status_code": 500, "error": str(exc)}
