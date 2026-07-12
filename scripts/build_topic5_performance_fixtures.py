"""Generate deterministic mixed-content Topic 5 performance fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from topic5_reliability_common import ROOT, canonical_json_bytes, performance_request

DEFAULT_OUTPUT = ROOT / "eval" / "topic5_performance" / "v1" / "fixtures"
SIZES = (10, 100, 1_000, 10_000)


def build(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    fixtures = []
    for size in SIZES:
        payload = performance_request(size)
        path = output_dir / f"{size}.json"
        data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        path.write_text(data, encoding="utf-8")
        fixtures.append(
            {
                "block_count": size,
                "path": path.name,
                "bytes": len(data.encode("utf-8")),
                "sha256": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
            }
        )
    manifest = {
        "dataset_id": "topic5_performance",
        "dataset_version": "1.0.0",
        "generator": "scripts/build_topic5_performance_fixtures.py",
        "fixtures": fixtures,
    }
    (output_dir.parent / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(build(args.output_dir), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
