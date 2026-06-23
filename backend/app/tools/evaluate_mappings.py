import argparse
import json
from pathlib import Path

from app.evaluation.mapping_evaluator import evaluate_cases, load_eval_cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate SchemaPack mapping fixtures.")
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    args = parser.parse_args(argv)

    report = evaluate_cases(load_eval_cases(args.fixture))
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(_markdown(report), encoding="utf-8")
    if not args.json_out and not args.md_out:
        print(text)
    return 0 if report["f1"] >= 0.85 else 1


def _markdown(report: dict) -> str:
    return "\n".join([
        "# Mapping Evaluation Report",
        "",
        f"- Samples: {report['sample_count']}",
        f"- Gold mappings: {report['gold_mapping_count']}",
        f"- Precision: {report['precision']:.4f}",
        f"- Recall: {report['recall']:.4f}",
        f"- F1: {report['f1']:.4f}",
        f"- Unmapped required fields: {report['unmapped_required_fields']}",
        f"- Review-required predictions: {report['review_required_count']}",
        "",
    ])


if __name__ == "__main__":
    raise SystemExit(main())
