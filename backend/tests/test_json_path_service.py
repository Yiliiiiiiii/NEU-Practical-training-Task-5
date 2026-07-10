from __future__ import annotations

from copy import deepcopy


def test_json_path_resolves_object_field() -> None:
    from app.services.json_path_service import JsonPathService

    result = JsonPathService().resolve({"data": {"title": "Notice"}}, "$.data.title")

    assert result.found is True
    assert result.value == "Notice"
    assert result.normalized_path == "$.data.title"
    assert result.error is None


def test_json_path_resolves_array_index() -> None:
    from app.services.json_path_service import JsonPathService

    result = JsonPathService().resolve({"chunks": [{"text": "First"}]}, "$.chunks[0].text")

    assert result.found is True
    assert result.value == "First"


def test_json_path_returns_missing_key_without_error() -> None:
    from app.services.json_path_service import JsonPathService

    result = JsonPathService().resolve({"data": {}}, "$.data.title")

    assert result.found is False
    assert result.value is None
    assert result.error is None


def test_json_path_returns_structured_invalid_syntax_error() -> None:
    from app.services.json_path_service import JsonPathService

    result = JsonPathService().resolve({"data": {}}, "$.data[*]")

    assert result.found is False
    assert result.error == "unsupported JSON path syntax"


def test_json_path_does_not_mutate_input() -> None:
    from app.services.json_path_service import JsonPathService

    payload = {"data": {"items": [1, 2, 3]}}
    original = deepcopy(payload)

    JsonPathService().resolve(payload, "$.data.items[1]")

    assert payload == original
