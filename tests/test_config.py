import pytest
from src.config import find_forms, get_form_info, load_forms_from_json

def test_load_forms_from_json():
    load_forms_from_json()
    forms = find_forms()
    assert len(forms) == 43

def test_find_forms_by_cyrillic_query():
    # Поиск "карпаты" должен переводиться в unidecode и находить формы Karpaty
    results = find_forms("карпаты")
    assert len(results) > 0
    assert any("karpaty" in f["name"].lower() for f in results)

def test_find_forms_by_tag_or_category():
    results = find_forms("balkany")
    assert len(results) > 0
    assert any("balkany" in f["name"].lower() for f in results)

def test_find_forms_empty_query_returns_all():
    forms = find_forms("")
    assert len(forms) == 43

def test_get_form_info_by_id():
    info = get_form_info("mdavnpok")
    assert info["id"] == "mdavnpok"
    assert "balkany" in info["name"].lower()

def test_get_form_info_ambiguous_query_raises():
    with pytest.raises(ValueError, match="Найдено несколько"):
        get_form_info("tury")

def test_get_form_info_fallback():
    # Неизвестный ID возвращает дефолтный объект
    info = get_form_info("unknown_form_id_123")
    assert info["id"] == "unknown_form_id_123"
