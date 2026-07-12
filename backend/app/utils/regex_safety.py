from __future__ import annotations

import re

UNSUPPORTED_REGEX_PATTERNS = (
    (re.compile(r"\\[1-9]"), "backreferences are unsupported"),
    (re.compile(r"\(\?<[=!].*?\)"), "lookbehind is unsupported"),
    (re.compile(r"\(\?\("), "conditional groups are unsupported"),
    (re.compile(r"\(\?P="), "named backreferences are unsupported"),
    (
        re.compile(r"\([^)]*(?:\*|\+|\{\d+,?\d*\})[^)]*\)(?:\*|\+|\{\d+,?\d*\})"),
        "nested repetition is unsupported",
    ),
)


def validate_safe_regex(pattern: str, *, max_length: int = 1_000) -> str:
    if len(pattern) > max_length:
        raise ValueError(f"regex exceeds maximum length {max_length}")
    for detector, reason in UNSUPPORTED_REGEX_PATTERNS:
        if detector.search(pattern):
            raise ValueError(f"unsafe regex: {reason}")
    re.compile(pattern)
    return pattern
