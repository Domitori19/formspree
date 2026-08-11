"""
МОДУЛЬ КОНФИГУРАЦИИ И РЕЕСТРА ФОРМ (src/config.py)
-------------------------------------------------
Файл отвечает за:
1. Загрузку списка из 43 форм и их ключей из файла forms.json.
2. Поиск форм по ID, сайтам и ключевым словам.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from unidecode import unidecode

DEFAULT_FORM_ID = "mdavnpok"
FORMSPREE_BASE_URL = "https://formspree.io"

# Словари для быстрого поиска форм в памяти
FORMS_BY_ID: Dict[str, Dict[str, Any]] = {}
FORMS_BY_NAME: Dict[str, Dict[str, Any]] = {}

def load_forms_from_json() -> None:
    """
    Загружает файл forms.json из корня проекта.
    Заполняет словари FORMS_BY_ID и FORMS_BY_NAME.
    """
    FORMS_BY_ID.clear()
    FORMS_BY_NAME.clear()

    # Путь к файлу forms.json в корне проекта
    root_dir = Path(__file__).resolve().parent.parent
    forms_file_path = root_dir / "forms.json"

    if not forms_file_path.exists():
        print(f"Предупреждение: Файл {forms_file_path} не найден.")
        return

    try:
        with open(forms_file_path, "r", encoding="utf-8-sig") as file:
            forms_list = json.load(file)
            if not isinstance(forms_list, list):
                return

            for item in forms_list:
                if not isinstance(item, dict):
                    continue

                form_id = str(item.get("id", "")).strip()
                form_name = str(item.get("name") or form_id).strip()
                api_key = str(item.get("api_key", "")).strip()

                if form_id:
                    form_entry = {
                        "id": form_id,
                        "name": form_name,
                        "api_key": api_key,
                        "category": str(item.get("category", "")).strip(),
                        "tags": item.get("tags", []),
                        "aliases": item.get("aliases", [])
                    }
                    FORMS_BY_ID[form_id.lower()] = form_entry
                    FORMS_BY_NAME[form_name.lower()] = form_entry
    except Exception as error:
        print(f"Ошибка загрузки forms.json: {error}")

# Загружаем реестр при запуске модуля
load_forms_from_json()

def find_forms(query: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Ищет формы по ID, сайту или русскоязычным словам.
    Благодаря библиотеке unidecode поиск понимает и 'карпаты', и 'karpaty'.
    """
    all_forms = list(FORMS_BY_ID.values())
    if not query or not query.strip():
        return all_forms

    clean_query = query.strip().lower().split("/")[-1]
    # Используем unidecode вместо огромного словаря ручной транслитерации!
    latin_query = unidecode(clean_query).lower()

    matched_forms = []
    for form in all_forms:
        searchable_text = f"{form['id']} {form['name']} {form.get('category', '')} {' '.join(form.get('tags', []))}".lower()

        # Проверяем совпадение по исходному тексту и по латинице
        if clean_query in searchable_text or latin_query in searchable_text:
            matched_forms.append(form)

    return matched_forms

def get_form_info(identifier: Optional[str] = None) -> Dict[str, Any]:
    """
    Возвращает словарь с информацией о конкретной форме по её ID или Названию.
    Если идентификатор не передан, использует форму по умолчанию.
    """
    target = (identifier or DEFAULT_FORM_ID).strip()
    if not target:
        raise ValueError("ID формы не указан")

    clean_ident = target.lower().split("/")[-1]

    # 1. Проверяем точное совпадение по ID
    if clean_ident in FORMS_BY_ID:
        return FORMS_BY_ID[clean_ident]

    # 2. Проверяем точное совпадение по Названию
    if clean_ident in FORMS_BY_NAME:
        return FORMS_BY_NAME[clean_ident]

    # 3. Ищем по подстроке/ключевому слову через find_forms
    matches = find_forms(clean_ident)
    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        names_str = ", ".join(f["name"] for f in matches[:5])
        raise ValueError(f"Найдено несколько подходящих форм ({names_str}). Уточните запрос.")

    # Если форма не найдена в реестре, возвращаем дефолтный объект
    return {"id": clean_ident, "name": target, "api_key": ""}
