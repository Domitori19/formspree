"""
МОДУЛЬ АНАЛИТИКИ И ЛИДЕРБОРДА (src/analytics.py)
-----------------------------------------------
Этот модуль занимается расчетами и версткой:
1. unnest_submission — вынимает контакты клиенты из 'data'.
2. generate_analytics — считает сводку за период, среднее в день и рисует график.
3. compare_periods — сравнивает прошлые 30 дней с текущими 30 днями (% роста/падения).
4. generate_cross_form_leaderboard — строит рейтинг по всем турам с медалями.
"""

import re
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
import pandas as pd
import plotext as plt
from tabulate import tabulate

def strip_ansi_codes(text: str) -> str:
    """Удаляет цветные служебные символы ANSI из текстовых графиков."""
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)

def unnest_submission(submission: Dict[str, Any]) -> Dict[str, Any]:
    """
    Разворачивает вложенный словарь 'data' от Formspree.
    Было: {"data": {"name": "Иван", "email": "a@b.com"}, "_date": "2026-08-10"}
    Стало: {"name": "Иван", "email": "a@b.com", "_date": "2026-08-10"}
    """
    flattened: Dict[str, Any] = {}

    date_value = submission.get("created_at") or submission.get("_date") or submission.get("date")
    if date_value:
        flattened["_date"] = str(date_value)

    data_payload = submission.get("data")
    if isinstance(data_payload, dict):
        for key, val in data_payload.items():
            if not key.startswith("_"):
                flattened[key] = val

    excluded_keys = {"data", "_date", "created_at", "date", "id", "hashid"}
    for key, val in submission.items():
        if key not in excluded_keys and not key.startswith("_"):
            if key not in flattened:
                flattened[key] = val

    return flattened

def create_empty_analytics(period_days: int, message: str) -> Dict[str, Any]:
    """Возвращает пустую структуру отчета, если заявок нет."""
    return {
        "total_submissions": 0,
        "period_days": period_days,
        "active_days": 0,
        "avg_submissions_per_day": 0.0,
        "avg_submissions_per_active_day": 0.0,
        "peak_day": {"date": "None", "count": 0},
        "first_submission": None,
        "latest_submission": None,
        "message": message,
        "ascii_chart": "Нет данных.",
        "formatted_table": "Нет данных.",
        "daily_breakdown": {},
        "top_fields": []
    }

def generate_analytics(submissions: List[Dict[str, Any]], period_days: int = 30) -> Dict[str, Any]:
    """
    Анализирует лиды конкретной формы за указанный период (по умолчанию 30 дней).
    Возвращает словарь со статистикой, графиком и таблицей.
    """
    if not submissions:
        return create_empty_analytics(period_days, "Нет заявок для анализа.")

    flat_list = [unnest_submission(sub) for sub in submissions]
    df = pd.DataFrame(flat_list)

    if "_date" in df.columns:
        df["dt"] = pd.to_datetime(df["_date"], errors="coerce", utc=True)
    else:
        df["dt"] = pd.NaT

    df = df[df["dt"].notna()].copy()
    if period_days > 0:
        now_utc = datetime.now(timezone.utc)
        cutoff_date = now_utc - timedelta(days=period_days)
        df = df[(df["dt"] >= cutoff_date) & (df["dt"] <= now_utc)]

    if df.empty:
        return create_empty_analytics(period_days, f"Нет заявок за последние {period_days} дней.")

    df["parsed_date"] = df["dt"].dt.date.astype(str)
    daily_counts = df["parsed_date"].value_counts().sort_index()
    dates_list = [str(d) for d in daily_counts.index]

    total_submissions = len(df)
    active_days = len(daily_counts)
    days_in_period = period_days if period_days > 0 else max(1, len(dates_list))

    avg_per_day = round(total_submissions / days_in_period, 2)
    avg_per_active_day = round(total_submissions / max(1, active_days), 2)

    peak_date = str(daily_counts.idxmax()) if not daily_counts.empty else "None"
    peak_count = int(daily_counts.max()) if not daily_counts.empty else 0

    # Строим текстовый график с помощью Plotext
    plt.clear_data()
    plt.clf()
    plt.bar(dates_list, [int(c) for c in daily_counts.values], width=0.5, marker="#")
    plt.title("Динамика поступления заявок")
    plt.theme("clear")
    plt.plotsize(50, max(8, len(dates_list) + 3))

    chart_output = strip_ansi_codes(plt.build())
    table_markdown = format_markdown_table(df.to_dict(orient="records"))

    # Анализируем частоту заполнености полей
    top_fields_list = []
    excluded_cols = {"_date", "created_at", "id", "hashid", "parsed_date", "dt"}

    for col in df.columns:
        if col in excluded_cols or col.startswith("_"):
            continue
        valid_series = df[col].dropna()
        if valid_series.empty:
            continue

        value_counts = valid_series.value_counts().head(3)
        frequent_vals = [f"{val} ({cnt})" for val, cnt in value_counts.items() if str(val).strip()]

        top_fields_list.append({
            "field_name": col,
            "occurrences": int(len(valid_series)),
            "frequent_values": frequent_vals
        })

    return {
        "total_submissions": total_submissions,
        "period_days": period_days,
        "active_days": active_days,
        "avg_submissions_per_day": avg_per_day,
        "avg_submissions_per_active_day": avg_per_active_day,
        "peak_day": {"date": peak_date, "count": peak_count},
        "first_submission": dates_list[0] if dates_list else None,
        "latest_submission": dates_list[-1] if dates_list else None,
        "ascii_chart": chart_output,
        "formatted_table": table_markdown,
        "daily_breakdown": {str(k): int(v) for k, v in daily_counts.items()},
        "top_fields": top_fields_list
    }

def format_markdown_table(submissions: List[Dict[str, Any]]) -> str:
    """Превращает список заявок в ровную таблицу Markdown."""
    if not submissions:
        return "Заявки не найдены."

    rows = []
    for idx, sub in enumerate(submissions, start=1):
        flat = unnest_submission(sub)
        date_str = str(flat.get("_date") or "Unknown")[:10]
        row = {"#": idx, "Дата": date_str}

        for k, v in flat.items():
            if k not in ("_date", "dt") and not k.startswith("_"):
                val_str = str(v).strip()
                row[k.capitalize()] = val_str[:40] + "..." if len(val_str) > 40 else val_str
        rows.append(row)

    if not rows:
        return "Нет данных для отображения."

    return tabulate(rows, headers="keys", tablefmt="github")

def compare_periods(
    submissions: List[Dict[str, Any]],
    period_days: int,
    threshold_percent: float = 15.0
) -> Dict[str, Any]:
    """
    Сравнивает текущий период с предыдущим таким же периодом.
    Вычисляет процент изменения (% роста или % падения).
    """
    if period_days <= 0:
        raise ValueError("period_days должен быть больше 0")

    parsed_dates = []
    for sub in submissions:
        date_val = unnest_submission(sub).get("_date")
        parsed = pd.to_datetime(date_val, errors="coerce", utc=True)
        if not pd.isna(parsed):
            parsed_dates.append(parsed.to_pydatetime())

    now = datetime.now(timezone.utc)
    current_start = now - timedelta(days=period_days)
    previous_start = now - timedelta(days=period_days * 2)

    current_period_dates = [d for d in parsed_dates if current_start <= d <= now]
    previous_period_dates = [d for d in parsed_dates if previous_start <= d < current_start]

    current_count = len(current_period_dates)
    previous_count = len(previous_period_dates)
    active_days = len({d.date() for d in current_period_dates})

    if previous_count == 0:
        if current_count > 0:
            change_percent = None
            status = "new"
        else:
            change_percent = 0.0
            status = "stable"
    else:
        change_percent = round((current_count - previous_count) / previous_count * 100, 1)
        if current_count == 0:
            status = "inactive"
        elif change_percent <= -abs(threshold_percent):
            status = "decline"
        elif change_percent >= abs(threshold_percent):
            status = "growth"
        else:
            status = "stable"

    return {
        "current_submissions": current_count,
        "previous_submissions": previous_count,
        "change_percent": change_percent,
        "status": status,
        "active_days": active_days,
        "avg_per_day": round(current_count / period_days, 2),
        "avg_per_active_day": round(current_count / max(1, active_days), 2),
        "latest_submission": max(current_period_dates).date().isoformat() if current_period_dates else None
    }

def generate_cross_form_leaderboard(
    forms_data: List[Dict[str, Any]],
    period_days: int = 30,
    threshold_percent: float = 15.0
) -> Dict[str, Any]:
    """
    Строит рейтинг туров (лидерборд) по всем направлениям с медалями 🥇, 🥈, 🥉.
    """
    leaderboard = []
    failed_forms_count = 0
    total_leads = 0

    for item in forms_data:
        fname = item.get("form_name", "Неизвестно")
        fid = item.get("form_id", "")

        if not item.get("success", True):
            failed_forms_count += 1
            continue

        subs = item.get("submissions", [])
        comparison = compare_periods(subs, period_days, threshold_percent)
        leads_count = comparison["current_submissions"]
        total_leads += leads_count

        leaderboard.append({
            "form_name": fname,
            "form_id": fid,
            "total_submissions": leads_count,
            "avg_per_day": comparison["avg_per_day"],
            "avg_per_active_day": comparison["avg_per_active_day"],
            "latest_submission": comparison["latest_submission"],
            "previous_submissions": comparison["previous_submissions"],
            "change_percent": comparison["change_percent"],
            "status": comparison["status"]
        })

    # Сортируем по убыванию лидов (кто на 1-м месте)
    leaderboard.sort(key=lambda x: x["total_submissions"], reverse=True)

    table_rows = []
    status_ru_names = {
        "growth": "Рост",
        "stable": "Стабильно",
        "decline": "Падение",
        "inactive": "Нет новых",
        "new": "Новая активность"
    }

    for idx, entry in enumerate(leaderboard, start=1):
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        rank_str = medals.get(idx, f"{idx}.")
        change = entry["change_percent"]
        change_str = "новая" if change is None else f"{change:+.1f}%"

        table_rows.append({
            "Ранг": rank_str,
            "Форма / Направление": entry["form_name"],
            "ID формы": entry["form_id"],
            "Текущий период": entry["total_submissions"],
            "Прошлый период": entry["previous_submissions"],
            "Изменение": change_str,
            "Статус": status_ru_names.get(entry["status"], entry["status"]),
            "В день": entry["avg_per_day"],
            "В активный день": entry["avg_per_active_day"],
            "Последний лид": entry["latest_submission"] or "—"
        })

    table_markdown = tabulate(table_rows, headers="keys", tablefmt="github") if table_rows else "Нет данных."

    return {
        "period_days": period_days,
        "total_forms_analyzed": len(leaderboard),
        "total_forms_failed": failed_forms_count,
        "total_leads_all_forms": total_leads,
        "leaderboard_table": table_markdown,
        "ranking": leaderboard
    }
