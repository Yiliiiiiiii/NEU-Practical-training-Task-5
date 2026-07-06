# {{CLASS_NAME}}

Adapter id: `{{ADAPTER_ID}}`

1. Replace the sample fixture with representative upstream payloads.
2. Implement deterministic `can_handle` and `convert` behavior.
3. Preserve source paths in adapter trace evidence.
4. Add badcases and run the adapter evaluator.
5. Request review before adding the adapter to `build_default_registry`.

The scaffold is deliberately inert and never auto-registers itself.
