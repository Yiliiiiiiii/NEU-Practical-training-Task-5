from __future__ import annotations

import re
from datetime import UTC, datetime
from math import isfinite
from typing import Any, Literal, Self

from pydantic import Field, field_validator, model_validator

from app.schemas.common import StrictBaseModel
from app.schemas.schema_pack_contract import validate_contract_version, validate_semver

JSON_PATH_PATTERN = re.compile(
    r"^\$(?:\.[A-Za-z_][A-Za-z0-9_-]*|\[(?:0|[1-9]\d*)\])*$"
)
AssertionOperator = Literal[
    "exists",
    "non_empty",
    "type_is",
    "date_format",
    "datetime_format",
    "regex_match",
    "enum_allowed",
    "number_range",
    "text_length",
    "array_length",
    "url_like",
    "equal_to_path",
    "not_equal_to_path",
]


def validate_json_path(value: str) -> str:
    if not JSON_PATH_PATTERN.fullmatch(value):
        raise ValueError("unsupported JSON path syntax")
    return value


class AssertionDefaults(StrictBaseModel):
    severity: Literal["error", "warning"] = "error"
    missing_optional_field: Literal["skip"] = "skip"


class ConversionAssertionDefinition(StrictBaseModel):
    assertion_id: str
    path: str
    operator: AssertionOperator
    severity: Literal["error", "warning"] | None = None
    optional: bool = False
    parameters: dict[str, Any] = Field(default_factory=dict)
    message: str | None = None

    @field_validator("assertion_id")
    @classmethod
    def validate_assertion_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("assertion_id must not be empty")
        return value

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return validate_json_path(value)

    @model_validator(mode="after")
    def validate_parameters(self) -> Self:
        required: dict[str, set[str]] = {
            "type_is": {"expected"},
            "date_format": {"formats"},
            "datetime_format": {"formats"},
            "regex_match": {"pattern"},
            "enum_allowed": {"values"},
            "equal_to_path": {"other_path"},
            "not_equal_to_path": {"other_path"},
        }
        allowed: dict[str, set[str]] = {
            "exists": set(),
            "non_empty": set(),
            "type_is": {"expected"},
            "date_format": {"formats"},
            "datetime_format": {"formats"},
            "regex_match": {"pattern", "mode"},
            "enum_allowed": {"values"},
            "number_range": {"min", "max", "inclusive_min", "inclusive_max"},
            "text_length": {"min", "max"},
            "array_length": {"min", "max"},
            "url_like": set(),
            "equal_to_path": {"other_path"},
            "not_equal_to_path": {"other_path"},
        }
        missing = required.get(self.operator, set()) - self.parameters.keys()
        if missing:
            parameter = sorted(missing)[0]
            raise ValueError(f"{self.operator} requires parameters.{parameter}")
        unexpected = self.parameters.keys() - allowed[self.operator]
        if unexpected:
            raise ValueError(
                f"{self.operator} does not support parameter {sorted(unexpected)[0]}"
            )

        if self.operator == "type_is":
            expected = self.parameters["expected"]
            valid_types = {"string", "number", "integer", "boolean", "array", "object", "null"}
            if not isinstance(expected, str) or expected not in valid_types:
                raise ValueError("type_is parameters.expected is unsupported")
        elif self.operator in {"date_format", "datetime_format"}:
            formats = self.parameters["formats"]
            if not isinstance(formats, list) or not formats or not all(
                isinstance(item, str) and item for item in formats
            ):
                raise ValueError(f"{self.operator} parameters.formats must be non-empty")
            sample = datetime(2000, 1, 2, 3, 4, 5, tzinfo=UTC)
            for date_format in formats:
                try:
                    datetime.strptime(sample.strftime(date_format), date_format)
                except ValueError as exc:
                    raise ValueError(f"invalid strptime format: {date_format}") from exc
        elif self.operator == "regex_match":
            pattern = self.parameters["pattern"]
            if not isinstance(pattern, str):
                raise ValueError("regex_match parameters.pattern must be a string")
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"invalid regular expression: {exc}") from exc
            mode = self.parameters.get("mode", "search")
            if not isinstance(mode, str) or mode not in {"search", "match", "fullmatch"}:
                raise ValueError("regex_match parameters.mode is unsupported")
        elif self.operator == "enum_allowed":
            values = self.parameters["values"]
            if not isinstance(values, list) or not values:
                raise ValueError("enum_allowed parameters.values must be non-empty")
        elif self.operator == "number_range":
            if "min" not in self.parameters and "max" not in self.parameters:
                raise ValueError(f"{self.operator} requires parameters.min or parameters.max")
            for name in ("min", "max"):
                if name not in self.parameters:
                    continue
                value = self.parameters[name]
                if (
                    not isinstance(value, int | float)
                    or isinstance(value, bool)
                    or not isfinite(float(value))
                ):
                    raise ValueError("number_range bounds must be finite numbers")
            for name in ("inclusive_min", "inclusive_max"):
                if name in self.parameters and not isinstance(self.parameters[name], bool):
                    raise ValueError(f"number_range parameters.{name} must be boolean")
            minimum = self.parameters.get("min")
            maximum = self.parameters.get("max")
            if minimum is not None and maximum is not None and minimum > maximum:
                raise ValueError(f"{self.operator} parameters.min cannot exceed parameters.max")
        elif self.operator in {"text_length", "array_length"}:
            if "min" not in self.parameters and "max" not in self.parameters:
                raise ValueError(f"{self.operator} requires parameters.min or parameters.max")
            for name in ("min", "max"):
                if name not in self.parameters:
                    continue
                value = self.parameters[name]
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    raise ValueError(
                        f"{self.operator} bounds must be non-negative integers"
                    )
            minimum = self.parameters.get("min")
            maximum = self.parameters.get("max")
            if minimum is not None and maximum is not None and minimum > maximum:
                raise ValueError(f"{self.operator} parameters.min cannot exceed parameters.max")
        elif self.operator in {"equal_to_path", "not_equal_to_path"}:
            other_path = self.parameters["other_path"]
            if not isinstance(other_path, str):
                raise ValueError(f"{self.operator} parameters.other_path must be a string")
            validate_json_path(other_path)
        return self


class ConversionAssertionConfig(StrictBaseModel):
    contract_version: str
    schema_id: str
    assertion_set_version: str
    defaults: AssertionDefaults = Field(default_factory=AssertionDefaults)
    assertions: list[ConversionAssertionDefinition]

    @field_validator("contract_version")
    @classmethod
    def validate_contract(cls, value: str) -> str:
        return validate_contract_version(value)

    @field_validator("assertion_set_version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return validate_semver(value)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> Self:
        assertion_ids = [item.assertion_id for item in self.assertions]
        if len(assertion_ids) != len(set(assertion_ids)):
            raise ValueError("assertion_id must be unique within a SchemaPack")
        return self
