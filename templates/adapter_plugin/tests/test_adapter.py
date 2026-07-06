import pytest

from app.adapters.base import AdapterInput

from adapter import {{CLASS_NAME}}


def test_scaffold_is_inert_until_implemented() -> None:
    adapter = {{CLASS_NAME}}()
    adapter_input = AdapterInput(payload={})

    assert adapter.can_handle(adapter_input) == 0.0
    with pytest.raises(NotImplementedError):
        adapter.convert(adapter_input)
