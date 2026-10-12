from src.config import get_form_info, find_forms
from src.client import get_auth_headers

def test_get_form_info():
    info = get_form_info("mdavnpok")
    assert info["id"] == "mdavnpok"
    assert "balkany" in info["name"]

    info_karpaty = get_form_info("karpaty-b")
    assert info_karpaty["id"] == "mzdqajld"

def test_search_forms_with_unidecode():
    matched = find_forms("карпаты")
    assert len(matched) > 0
    assert any("karpaty" in f["name"].lower() for f in matched)

def test_get_auth_headers():
    headers = get_auth_headers(api_key="test-key")
    assert headers["Accept"] == "application/json"
    assert headers["Authorization"] == "Bearer test-key"
