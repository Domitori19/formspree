import json
from pathlib import Path

import pytest

FORMS_FILE = Path(__file__).resolve().parent.parent / "forms.json"


@pytest.fixture
def expected_forms_count():
    """Количество форм в forms.json — чтобы тесты не ломались при добавлении форм."""
    with open(FORMS_FILE, "r", encoding="utf-8-sig") as file:
        return len(json.load(file))
