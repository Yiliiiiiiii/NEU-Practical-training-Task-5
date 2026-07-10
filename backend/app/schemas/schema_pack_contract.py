from __future__ import annotations

import re
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from app.schemas.common import StrictBaseModel

SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
CONTRACT_VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def validate_semver(value: str) -> str:
    if not SEMVER_PATTERN.fullmatch(value):
        raise ValueError("must be a semantic version in MAJOR.MINOR.PATCH format")
    return value


def validate_contract_version(value: str) -> str:
    if not CONTRACT_VERSION_PATTERN.fullmatch(value):
        raise ValueError("must be a contract version in MAJOR.MINOR format")
    return value


def validate_asset_path(value: str) -> str:
    if not value.strip():
        raise ValueError("must be a relative path inside the SchemaPack")
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if posix.is_absolute() or windows.is_absolute() or windows.drive or windows.root:
        raise ValueError("must be a relative path inside the SchemaPack")
    if ".." in posix.parts or ".." in windows.parts:
        raise ValueError("must be a relative path inside the SchemaPack")
    return value


class SchemaPackCompatibility(StrictBaseModel):
    min_agent_version: str
    max_agent_version: str | None = None
    input_uir_version: str
    package_contract_version: str

    @field_validator("min_agent_version", "max_agent_version")
    @classmethod
    def validate_agent_versions(cls, value: str | None) -> str | None:
        return validate_semver(value) if value is not None else None

    @field_validator("input_uir_version", "package_contract_version")
    @classmethod
    def validate_contract_versions(cls, value: str) -> str:
        return validate_contract_version(value)


class SchemaPackAssets(StrictBaseModel):
    target_schema: str
    metadata_template: str
    mapping_rules: str
    content_org: str
    output_assertions: str | None = None
    router_rules: str | None = None

    @field_validator("*")
    @classmethod
    def validate_paths(cls, value: str | None) -> str | None:
        return validate_asset_path(value) if value is not None else None


class SchemaPackExecution(StrictBaseModel):
    default_mapping_mode: Literal["legacy", "global_assignment"] = "global_assignment"
    allow_llm_fallback: bool = False
    include_assertion_report_in_package: bool = False


class SchemaPackSupportedInput(StrictBaseModel):
    normalized_uir_required: bool = True
    source_formats: list[str]
    languages: list[str] = Field(default_factory=list)


class SchemaPackClaimBoundary(StrictBaseModel):
    benchmark_scope: bool = True
    production_ready: bool = False
    notes: str


class SchemaPackManifest(StrictBaseModel):
    contract_version: str
    schema_pack_id: str
    schema_pack_version: str
    display_name: str
    description: str
    status: Literal["example", "experimental", "stable", "deprecated"]
    owner: str
    compatibility: SchemaPackCompatibility
    assets: SchemaPackAssets
    execution: SchemaPackExecution
    supported_input: SchemaPackSupportedInput
    claim_boundary: SchemaPackClaimBoundary

    @field_validator("contract_version")
    @classmethod
    def validate_contract(cls, value: str) -> str:
        return validate_contract_version(value)

    @field_validator("schema_pack_version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return validate_semver(value)

    @field_validator("schema_pack_id", "display_name", "description", "owner")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def validate_compatibility_range(self) -> Self:
        maximum = self.compatibility.max_agent_version
        if maximum is not None:
            minimum_parts = tuple(map(int, self.compatibility.min_agent_version.split(".")))
            maximum_parts = tuple(map(int, maximum.split(".")))
            if maximum_parts < minimum_parts:
                raise ValueError("max_agent_version cannot be lower than min_agent_version")
        return self
