from app.adapters.base import AdapterInput, AdapterResult, ExternalUirAdapter
from app.adapters.builtin import BlockListAdapter, SectionTreeAdapter
from app.schemas.adapter import AdapterCapability, AdapterSelectionItem, SelectedAdapter


class AdapterRegistry:
    min_confidence = 0.5

    def __init__(self) -> None:
        self._adapters: list[ExternalUirAdapter] = []

    def register(self, adapter: ExternalUirAdapter) -> None:
        if any(
            item.capability.adapter_id == adapter.capability.adapter_id
            for item in self._adapters
        ):
            raise ValueError(f"adapter already registered: {adapter.capability.adapter_id}")
        self._adapters.append(adapter)

    def list_capabilities(self) -> list[AdapterCapability]:
        return [adapter.capability for adapter in self._adapters]

    def select_adapter(self, adapter_input: AdapterInput) -> SelectedAdapter:
        dialect_hint = (adapter_input.dialect_hint or "auto").strip()
        scored = self._score_adapters(adapter_input)
        alternatives = [
            AdapterSelectionItem(adapter_id=adapter.capability.adapter_id, confidence=confidence)
            for adapter, confidence in scored
        ]

        explicit = self._explicit_adapter(dialect_hint)
        if explicit is not None:
            return SelectedAdapter(
                adapter_id=explicit.capability.adapter_id,
                confidence=1.0,
                alternatives=[
                    AdapterSelectionItem(adapter_id=explicit.capability.adapter_id, confidence=1.0),
                    *[
                        item
                        for item in alternatives
                        if item.adapter_id != explicit.capability.adapter_id
                    ],
                ],
                review_required=False,
            )
        if dialect_hint not in {"", "auto"}:
            return SelectedAdapter(
                adapter_id=None,
                confidence=0.0,
                alternatives=alternatives,
                review_required=True,
                error="unsupported_dialect",
            )
        if not scored or scored[0][1] < self.min_confidence:
            return SelectedAdapter(
                adapter_id=None,
                confidence=0.0,
                alternatives=alternatives,
                review_required=True,
                error="unsupported_dialect",
            )
        best_adapter, confidence = scored[0]
        return SelectedAdapter(
            adapter_id=best_adapter.capability.adapter_id,
            confidence=confidence,
            alternatives=alternatives,
            review_required=False,
        )

    def convert(self, adapter_input: AdapterInput) -> AdapterResult:
        selected = self.select_adapter(adapter_input)
        if selected.adapter_id is None:
            raise ValueError("unsupported external UIR dialect")
        adapter = self._adapter_by_id(selected.adapter_id)
        return adapter.convert(adapter_input)

    def _score_adapters(
        self, adapter_input: AdapterInput
    ) -> list[tuple[ExternalUirAdapter, float]]:
        return sorted(
            ((adapter, adapter.can_handle(adapter_input)) for adapter in self._adapters),
            key=lambda item: item[1],
            reverse=True,
        )

    def _explicit_adapter(self, dialect_hint: str) -> ExternalUirAdapter | None:
        if dialect_hint in {"", "auto"}:
            return None
        normalized = dialect_hint.replace("-", "_")
        for adapter in self._adapters:
            dialects = {item.replace("-", "_") for item in adapter.capability.supported_dialects}
            if normalized == adapter.capability.adapter_id or normalized in dialects:
                return adapter
        return None

    def _adapter_by_id(self, adapter_id: str) -> ExternalUirAdapter:
        for adapter in self._adapters:
            if adapter.capability.adapter_id == adapter_id:
                return adapter
        raise ValueError(f"adapter not registered: {adapter_id}")


def build_default_registry() -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(BlockListAdapter())
    registry.register(SectionTreeAdapter())
    return registry
