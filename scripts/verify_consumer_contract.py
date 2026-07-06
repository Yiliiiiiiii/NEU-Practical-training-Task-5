"""Verify one package or a package tree against a versioned consumer contract."""

import argparse
import json
from pathlib import Path

from consumer_contract import (
    verify_batch,
    verify_consumer_contract,
    write_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--package", type=Path)
    source.add_argument("--package-root", type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--min-pass-rate", type=float, default=0.95)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.package:
        report = verify_consumer_contract(args.package, args.contract)
        passed = bool(report["passed"])
    else:
        report = verify_batch(args.package_root, args.contract)
        passed = (
            report["consumer_contract_pass_rate"] >= args.min_pass_rate
        )
    write_report(
        report,
        json_path=args.out,
        markdown_path=args.markdown,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
