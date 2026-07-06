import json
from pathlib import Path

from test_downstream_exports import load_script


def test_cli_parser_exposes_documented_commands() -> None:
    module = load_script("schemapack_cli")
    parser = module.build_parser()
    commands = {
        "convert-external": ["--input", "input.json", "--out", "out.json"],
        "import": ["--input", "input.json"],
        "create-task": [
            "--doc-id",
            "doc_1",
            "--schema-id",
            "policy_doc",
            "--template-id",
            "policy_doc_base_v1",
        ],
        "execute-task": ["--task-id", "task_1"],
        "download-package": ["--task-id", "task_1", "--out", "package.zip"],
        "eval": [
            "--package",
            "package.zip",
            "--contract",
            "contract.json",
            "--out",
            "report.json",
        ],
        "list-schemas": [],
        "list-adapters": [],
    }

    for command, arguments in commands.items():
        assert parser.parse_args([command, *arguments]).command == command


def test_convert_external_command_delegates_to_sdk(tmp_path: Path) -> None:
    module = load_script("schemapack_cli")
    source = tmp_path / "external.json"
    output = tmp_path / "converted.json"
    source.write_text('{"id":"external_1"}', encoding="utf-8")
    calls: list[dict] = []

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def convert_external_uir(self, payload, **options):
            calls.append({"payload": payload, "options": options})
            return {"standard_uir": {"doc_id": "doc_1"}}

    result = module.main(
        [
            "--base-url",
            "https://schemapack.test",
            "convert-external",
            "--input",
            str(source),
            "--out",
            str(output),
            "--route",
        ],
        client_factory=lambda *args, **kwargs: FakeClient(),
    )

    assert result == 0
    assert calls[0]["payload"]["id"] == "external_1"
    assert calls[0]["options"]["route_schema"] is True
    assert json.loads(output.read_text(encoding="utf-8"))["doc_id"] == "doc_1"
