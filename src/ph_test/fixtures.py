"""
ph_test.fixtures — Fixture loader for the PH autonomous E2E test harness.

Loads YAML fixture files and validates them into typed Fixture objects
that drive the two-agent simulation (tester bot + PH orchestrator).
"""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class ConversationOutcomes(BaseModel, frozen=True):
    """Phase 1: conversation-level validation (API-only mode)."""
    min_turns: int = 5
    termination_reason: str | None = None  # None = accept any


class ExpectedOutcomes(BaseModel, frozen=True):
    """Describes the artifacts and state the PH is expected to produce."""

    # Phase 1: conversation-level (always present)
    conversation: ConversationOutcomes = ConversationOutcomes()

    # Phase 2: file/artifact checks (optional — requires file system access)
    files: list[str] = Field(default_factory=list)
    manifest: dict[str, str] = Field(default_factory=dict)
    design_spec_sections: list[str] = Field(default_factory=list)

    @field_validator("files")
    @classmethod
    def files_must_be_non_empty_strings(cls, v: list[str]) -> list[str]:
        for item in v:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("each file path must be a non-empty string")
        return v

    @field_validator("design_spec_sections")
    @classmethod
    def sections_must_be_non_empty_strings(cls, v: list[str]) -> list[str]:
        for item in v:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("each design_spec_section must be a non-empty string")
        return v


# ---------------------------------------------------------------------------
# Top-level Fixture model
# ---------------------------------------------------------------------------

Mode = Literal["onboarded", "express", "self-published"]


class Fixture(BaseModel, frozen=True):
    """A single ph-test fixture that drives a tester-bot + PH-orchestrator run."""

    mode: Mode
    product: str = Field(min_length=1)
    name: str = Field(min_length=1)
    initial_prompt: str
    follow_up_details: str
    expected_outcomes: ExpectedOutcomes

    @field_validator("initial_prompt")
    @classmethod
    def initial_prompt_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("initial_prompt must not be blank or whitespace-only")
        return v

    @field_validator("follow_up_details")
    @classmethod
    def follow_up_details_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("follow_up_details must not be blank or whitespace-only")
        return v

    @field_validator("product")
    @classmethod
    def product_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("product must not be blank or whitespace-only")
        return v

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank or whitespace-only")
        return v


# ---------------------------------------------------------------------------
# Public loader
# ---------------------------------------------------------------------------


def load_fixture(path: str | Path) -> Fixture:
    """Read a YAML fixture file and return a validated :class:`Fixture`.

    Args:
        path: Absolute or relative path to the fixture YAML file.

    Returns:
        A fully validated, immutable :class:`Fixture` instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If the file is not valid YAML.
        pydantic.ValidationError: If the YAML content fails schema validation.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Fixture file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    return Fixture.model_validate(raw)
