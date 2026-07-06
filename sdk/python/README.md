# SchemaPack Python SDK

The SDK is a small synchronous client for the public SchemaPack HTTP API.

```powershell
$env:PYTHONPATH = "sdk\python"
```

```python
from schemapack_client import SchemaPackClient

with SchemaPackClient(
    "http://127.0.0.1:8000",
    api_key=None,
) as client:
    converted = client.convert_external_uir(
        {"id": "external_1", "chunks": []},
        source_system="topic11",
    )
    schemas = client.list_schemas()
```

Set `SCHEMAPACK_API_KEY` for the unified CLI when API-key authentication is
enabled. The SDK does not log request bodies, API keys, or downloaded package
content.

Current client methods cover standard UIR import, External UIR convert/import,
task create/execute, package download, schema listing, and adapter listing.
Review Workbench, Schema Draft, Evaluation Center, and knowledge-governance APIs
remain available through the public HTTP API but do not yet have dedicated SDK
methods.
