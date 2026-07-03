"""
ph_test.validator — Structural validation of PH orchestrator output.

After the two-agent loop completes, this module checks that the PH
orchestrator produced the expected artifacts.  Validation is structural
only — not content-exact.

Usage::

    from pathlib import Path
    from src.ph_test.validator import validate

    errors = validate(fixture, project_dir)
    if errors:
        for msg in errors:
            print(f"FAIL: {msg}")
    else:
        print("All checks passed.")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.ph_test.fixtures import Fixture

# Path to the design spec, relative to the project directory.
_DESIGN_SPEC_REL = Path("publishing-house") / "spec" / "design.md"

# Path to the manifest, relative to the project directory.
_MANIFEST_REL = Path("publishing-house") / "manifest.yaml"


def validate_conversation(fixture: Fixture, result: Any) -> list[str]:
    """Phase 1: validate conversation-level outcomes from a RunResult.

    Parameters
    ----------
    fixture:
        The loaded fixture with expected_outcomes.conversation settings.
    result:
        A RunResult object from runner.run().

    Returns
    -------
    list[str]
        Error strings. Empty = conversation checks passed.
    """
    errors: list[str] = []
    conv = fixture.expected_outcomes.conversation

    if result.turns < conv.min_turns:
        errors.append(
            f"Conversation too short: {result.turns} turns < minimum {conv.min_turns}"
        )

    if conv.termination_reason is not None:
        if result.termination_reason != conv.termination_reason:
            errors.append(
                f"Termination reason: expected '{conv.termination_reason}' "
                f"but got '{result.termination_reason}'"
            )

    if result.errors:
        for e in result.errors:
            errors.append(f"Runner error: {e}")

    return errors


def validate(fixture: Fixture, project_dir: Path) -> list[str]:
    """Validate PH orchestrator output against a fixture's expected outcomes.

    Checks three things in order, collecting ALL failures before returning:

    1. **File existence** — every path in ``fixture.expected_outcomes.files``
       must exist relative to *project_dir*.
    2. **Manifest field checks** — for each dotted-path key in
       ``fixture.expected_outcomes.manifest``, navigate the parsed YAML and
       assert the value matches.
    3. **Design spec section presence** — for each string in
       ``fixture.expected_outcomes.design_spec_sections``, the string must
       appear (case-insensitively) in the content of
       ``publishing-house/spec/design.md``.

    Parameters
    ----------
    fixture:
        The loaded and validated fixture describing expected outcomes.
    project_dir:
        Absolute path to the root of the PH project being validated.

    Returns
    -------
    list[str]
        A list of human-readable error strings.  An empty list means all
        checks passed.
    """
    errors: list[str] = []

    outcomes = fixture.expected_outcomes

    # ------------------------------------------------------------------
    # 1. File existence checks
    # ------------------------------------------------------------------
    for rel_path in outcomes.files:
        target = project_dir / rel_path
        if not target.exists():
            errors.append(f"Missing expected file: {rel_path}")

    # ------------------------------------------------------------------
    # 2. Manifest field checks
    # ------------------------------------------------------------------
    if outcomes.manifest:
        manifest_path = project_dir / _MANIFEST_REL
        manifest_data: dict[str, Any] | None = None
        manifest_load_error: str | None = None

        if not manifest_path.exists():
            manifest_load_error = (
                f"Cannot check manifest fields: "
                f"{_MANIFEST_REL} does not exist in project_dir"
            )
        else:
            try:
                with manifest_path.open("r", encoding="utf-8") as fh:
                    manifest_data = yaml.safe_load(fh) or {}
            except yaml.YAMLError as exc:
                manifest_load_error = f"Failed to parse manifest YAML: {exc}"

        if manifest_load_error is not None:
            errors.append(manifest_load_error)
        else:
            for dotted_key, expected_value in outcomes.manifest.items():
                actual_value, nav_error = _navigate_dotted_path(
                    manifest_data, dotted_key
                )
                if nav_error is not None:
                    errors.append(
                        f"Manifest field '{dotted_key}': {nav_error}"
                    )
                elif actual_value != expected_value:
                    errors.append(
                        f"Manifest field '{dotted_key}': "
                        f"expected {expected_value!r}, got {actual_value!r}"
                    )

    # ------------------------------------------------------------------
    # 3. Design spec section presence checks
    # ------------------------------------------------------------------
    spec_path = project_dir / _DESIGN_SPEC_REL
    design_content: str | None = None

    if not spec_path.exists():
        errors.append(
            f"Cannot check design spec sections: {_DESIGN_SPEC_REL} "
            f"does not exist in project_dir"
        )
    else:
        design_content = spec_path.read_text(encoding="utf-8")

    if design_content is not None:
        lower_content = design_content.lower()
        for section in outcomes.design_spec_sections:
            if section.lower() not in lower_content:
                errors.append(
                    f"Design spec missing section: '{section}'"
                )

    return errors


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _navigate_dotted_path(
    data: dict[str, Any] | None,
    dotted_key: str,
) -> tuple[Any, str | None]:
    """Navigate a dotted-path key through a nested dict.

    Parameters
    ----------
    data:
        The parsed YAML manifest (or any nested dict).
    dotted_key:
        A dotted path such as ``"phases.intake.status"``.

    Returns
    -------
    tuple[Any, str | None]
        ``(value, None)`` when the path is found, or
        ``(None, error_message)`` when the path cannot be traversed.
    """
    if data is None:
        return None, f"manifest is empty or None"

    parts = dotted_key.split(".")
    current: Any = data
    traversed: list[str] = []

    for part in parts:
        if not isinstance(current, dict):
            path_so_far = ".".join(traversed)
            return None, (
                f"expected a mapping at '{path_so_far}', "
                f"got {type(current).__name__}"
            )
        if part not in current:
            path_so_far = ".".join(traversed + [part])
            return None, f"key '{path_so_far}' not found in manifest"
        current = current[part]
        traversed.append(part)

    return current, None
