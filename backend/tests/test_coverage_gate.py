from tests.coverage_gate import evaluate_coverage


def test_gate_rejects_low_total_and_core_file_coverage():
    report = {
        "totals": {
            "percent_covered": 94.0,
            "num_branches": 100,
            "covered_branches": 89,
        },
        "files": {
            "app/engines/mapping_engine.py": {
                "summary": {"percent_covered": 93.0}
            }
        },
    }

    failures = evaluate_coverage(report)

    assert "total line coverage 94.00% < 95.00%" in failures
    assert "total branch coverage 89.00% < 90.00%" in failures
    assert any("mapping_engine.py" in failure for failure in failures)


def test_gate_accepts_thresholds_and_ignores_non_core_files():
    report = {
        "totals": {
            "percent_covered": 95.0,
            "num_branches": 10,
            "covered_branches": 9,
        },
        "files": {
            "app/engines/mapping_engine.py": {
                "summary": {"percent_covered": 95.0}
            },
            "app/schemas/api.py": {
                "summary": {"percent_covered": 10.0}
            },
        },
    }

    assert evaluate_coverage(report) == []
