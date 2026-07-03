"""
Tests for ph_test.validator — TDD (RED phase first).

Covers:
  - All checks pass → validate() returns []
  - Missing file → error string contains filename
  - Wrong manifest field value → error string contains field path + expected/actual
  - Missing design spec section → error string contains section name
  - design.md does not exist → error returned, no crash
  - Multiple errors are all returned (collect all, not just first)
  - Dotted-path manifest navigation (nested keys)
  - Case-insensitive design spec section matching
"""

import textwrap
from pathlib import Path

import pytest
import yaml

from src.ph_test.fixtures import ExpectedOutcomes, Fixture
from src.ph_test.validator import validate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_fixture(
    files: list[str] | None = None,
    manifest: dict[str, str] | None = None,
    design_spec_sections: list[str] | None = None,
) -> Fixture:
    """Return a minimal Fixture with the given expected_outcomes."""
    return Fixture(
        mode="onboarded",
        product="test-product",
        name="test-fixture",
        initial_prompt="Please build something.",
        follow_up_details="Here are the details.",
        expected_outcomes=ExpectedOutcomes(
            files=files or ["publishing-house/manifest.yaml"],
            manifest=manifest or {},
            design_spec_sections=design_spec_sections or ["Introduction"],
        ),
    )


def setup_project_dir(
    tmp_path: Path,
    files: list[str] | None = None,
    manifest_content: dict | None = None,
    design_spec_content: str | None = None,
) -> Path:
    """
    Create a mock project directory under tmp_path.

    Parameters
    ----------
    files:
        List of relative file paths to create (empty files unless
        special-cased below).
    manifest_content:
        If provided, written as YAML to publishing-house/manifest.yaml.
    design_spec_content:
        If provided, written as text to publishing-house/spec/design.md.
    """
    project = tmp_path / "project"
    project.mkdir()

    for rel in files or []:
        target = project / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()

    if manifest_content is not None:
        manifest_path = project / "publishing-house" / "manifest.yaml"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(yaml.dump(manifest_content), encoding="utf-8")

    if design_spec_content is not None:
        spec_path = project / "publishing-house" / "spec" / "design.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(design_spec_content, encoding="utf-8")

    return project


# ---------------------------------------------------------------------------
# 1. Happy path — all checks pass
# ---------------------------------------------------------------------------


class TestValidateAllPass:
    def test_returns_empty_list_when_all_checks_pass(self, tmp_path: Path):
        manifest_data = {
            "phases": {
                "intake": {"status": "completed"},
                "vetting": {"status": "completed"},
            }
        }
        design_md = textwrap.dedent(
            """\
            # Design Spec

            ## Problem Statement
            This is a problem.

            ## Learning Objectives
            - Objective 1
            """
        )
        fixture = make_fixture(
            files=[
                "publishing-house/spec/design.md",
                "publishing-house/manifest.yaml",
            ],
            manifest={
                "phases.intake.status": "completed",
                "phases.vetting.status": "completed",
            },
            design_spec_sections=["Problem Statement", "Learning Objectives"],
        )
        project = setup_project_dir(
            tmp_path,
            files=[
                "publishing-house/spec/design.md",
                "publishing-house/manifest.yaml",
            ],
            manifest_content=manifest_data,
            design_spec_content=design_md,
        )

        errors = validate(fixture, project)

        assert errors == []

    def test_returns_empty_list_with_empty_manifest_checks(self, tmp_path: Path):
        """No manifest field assertions → should still pass if file exists."""
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={},
            design_spec_sections=["Overview"],
        )
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
            design_spec_content="## Overview\nSome content.",
        )

        errors = validate(fixture, project)

        assert errors == []


# ---------------------------------------------------------------------------
# 2. File existence failures
# ---------------------------------------------------------------------------


class TestFileMissing:
    def test_missing_single_file_returns_error_with_filename(self, tmp_path: Path):
        fixture = make_fixture(
            files=["publishing-house/spec/design.md"],
            manifest={},
            design_spec_sections=["Overview"],
        )
        # project dir has no files at all, but design.md section check
        # would fail too — focus on file check here with no sections required
        fixture_no_sections = make_fixture(
            files=["publishing-house/spec/design.md"],
            manifest={},
            design_spec_sections=["dummy"],
        )
        project = setup_project_dir(tmp_path)

        errors = validate(fixture_no_sections, project)

        file_errors = [e for e in errors if "design.md" in e]
        assert len(file_errors) >= 1

    def test_error_string_contains_missing_filename(self, tmp_path: Path):
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={},
            design_spec_sections=["Overview"],
        )
        # provide design.md so section check passes, but not manifest.yaml
        project = setup_project_dir(
            tmp_path,
            design_spec_content="## Overview\nContent.",
        )

        errors = validate(fixture, project)

        assert any("manifest.yaml" in e for e in errors)

    def test_missing_nested_file_returns_error(self, tmp_path: Path):
        fixture = make_fixture(
            files=["publishing-house/spec/design.md", "publishing-house/manifest.yaml"],
            manifest={},
            design_spec_sections=["Overview"],
        )
        # Only create manifest, not design.md
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
            design_spec_content="## Overview\nContent.",
        )
        # Overwrite the auto-created design.md from setup_project_dir
        # Actually we created design.md via design_spec_content — remove it
        (project / "publishing-house" / "spec" / "design.md").unlink()

        errors = validate(fixture, project)

        assert any("design.md" in e for e in errors)


# ---------------------------------------------------------------------------
# 3. Manifest field value failures
# ---------------------------------------------------------------------------


class TestManifestFieldFailures:
    def test_wrong_manifest_value_returns_error(self, tmp_path: Path):
        manifest_data = {"phases": {"intake": {"status": "pending"}}}
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={"phases.intake.status": "completed"},
            design_spec_sections=["Overview"],
        )
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
            manifest_content=manifest_data,
            design_spec_content="## Overview\nContent.",
        )

        errors = validate(fixture, project)

        assert len(errors) >= 1

    def test_error_contains_field_path(self, tmp_path: Path):
        manifest_data = {"phases": {"intake": {"status": "pending"}}}
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={"phases.intake.status": "completed"},
            design_spec_sections=["Overview"],
        )
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
            manifest_content=manifest_data,
            design_spec_content="## Overview\nContent.",
        )

        errors = validate(fixture, project)

        assert any("phases.intake.status" in e for e in errors)

    def test_error_contains_expected_value(self, tmp_path: Path):
        manifest_data = {"phases": {"intake": {"status": "pending"}}}
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={"phases.intake.status": "completed"},
            design_spec_sections=["Overview"],
        )
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
            manifest_content=manifest_data,
            design_spec_content="## Overview\nContent.",
        )

        errors = validate(fixture, project)

        assert any("completed" in e for e in errors)

    def test_error_contains_actual_value(self, tmp_path: Path):
        manifest_data = {"phases": {"intake": {"status": "pending"}}}
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={"phases.intake.status": "completed"},
            design_spec_sections=["Overview"],
        )
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
            manifest_content=manifest_data,
            design_spec_content="## Overview\nContent.",
        )

        errors = validate(fixture, project)

        assert any("pending" in e for e in errors)

    def test_deeply_nested_manifest_path_navigated_correctly(self, tmp_path: Path):
        manifest_data = {
            "phases": {
                "automation": {
                    "sub": {
                        "catalog_item": {"status": "completed"}
                    }
                }
            }
        }
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={"phases.automation.sub.catalog_item.status": "completed"},
            design_spec_sections=["Overview"],
        )
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
            manifest_content=manifest_data,
            design_spec_content="## Overview\nContent.",
        )

        errors = validate(fixture, project)

        assert errors == []

    def test_missing_manifest_key_returns_error(self, tmp_path: Path):
        """A dotted path that doesn't exist in the manifest should be an error."""
        manifest_data = {"phases": {"intake": {}}}  # missing 'status' key
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={"phases.intake.status": "completed"},
            design_spec_sections=["Overview"],
        )
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
            manifest_content=manifest_data,
            design_spec_content="## Overview\nContent.",
        )

        errors = validate(fixture, project)

        assert len(errors) >= 1
        assert any("phases.intake.status" in e for e in errors)


# ---------------------------------------------------------------------------
# 4. Design spec section failures
# ---------------------------------------------------------------------------


class TestDesignSpecSectionFailures:
    def test_missing_section_returns_error(self, tmp_path: Path):
        design_md = "## Overview\nSome content."
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={},
            design_spec_sections=["Problem Statement"],
        )
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
            design_spec_content=design_md,
        )

        errors = validate(fixture, project)

        assert len(errors) >= 1
        assert any("Problem Statement" in e for e in errors)

    def test_section_check_is_case_insensitive(self, tmp_path: Path):
        """Section names are checked case-insensitively."""
        design_md = "## PROBLEM STATEMENT\nSome content."
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={},
            design_spec_sections=["problem statement"],
        )
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
            design_spec_content=design_md,
        )

        errors = validate(fixture, project)

        assert errors == []

    def test_section_check_case_insensitive_mixed(self, tmp_path: Path):
        """Section present in mixed case in doc, searched in original case from fixture."""
        design_md = "## Learning Objectives\nContent."
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={},
            design_spec_sections=["LEARNING OBJECTIVES"],
        )
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
            design_spec_content=design_md,
        )

        errors = validate(fixture, project)

        assert errors == []

    def test_error_string_contains_section_name(self, tmp_path: Path):
        design_md = "## Overview\nSome content."
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={},
            design_spec_sections=["Target Audience"],
        )
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
            design_spec_content=design_md,
        )

        errors = validate(fixture, project)

        assert any("Target Audience" in e for e in errors)


# ---------------------------------------------------------------------------
# 5. design.md does not exist — error, not crash
# ---------------------------------------------------------------------------


class TestDesignMdMissing:
    def test_missing_design_md_returns_error_not_crash(self, tmp_path: Path):
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={},
            design_spec_sections=["Overview"],
        )
        # project has manifest.yaml but no design.md at all
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
        )

        errors = validate(fixture, project)

        # Should return at least one error (design.md missing), not raise
        assert isinstance(errors, list)
        assert len(errors) >= 1

    def test_missing_design_md_error_is_descriptive(self, tmp_path: Path):
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={},
            design_spec_sections=["Overview"],
        )
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
        )

        errors = validate(fixture, project)

        # At minimum the error should reference design.md in some way
        assert any("design.md" in e or "design" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# 6. Multiple errors collected (not short-circuit on first failure)
# ---------------------------------------------------------------------------


class TestMultipleErrorsCollected:
    def test_all_three_error_types_collected_together(self, tmp_path: Path):
        """Missing file + wrong manifest + missing section → 3+ errors returned."""
        manifest_data = {"phases": {"intake": {"status": "pending"}}}
        fixture = make_fixture(
            files=[
                "publishing-house/manifest.yaml",
                "publishing-house/spec/design.md",   # will be missing
                "publishing-house/extra-file.txt",    # will be missing
            ],
            manifest={"phases.intake.status": "completed"},
            design_spec_sections=["Problem Statement", "Target Audience"],
        )
        # Setup: create manifest (correct file), but wrong value.
        # design.md is NOT created → file check fails AND section check fails.
        # extra-file.txt NOT created → file check fails.
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
            manifest_content=manifest_data,
            # No design_spec_content → design.md does not exist
        )

        errors = validate(fixture, project)

        # There should be multiple errors: at least missing files + manifest + sections
        assert len(errors) >= 3

    def test_two_missing_files_both_reported(self, tmp_path: Path):
        fixture = make_fixture(
            files=[
                "publishing-house/manifest.yaml",
                "publishing-house/spec/design.md",
            ],
            manifest={},
            design_spec_sections=["Overview"],
        )
        # Create neither file; provide design content so section check passes
        # (but design.md won't exist on disk → section check also fails)
        project = setup_project_dir(tmp_path)

        errors = validate(fixture, project)

        filenames_in_errors = " ".join(errors)
        assert "manifest.yaml" in filenames_in_errors
        assert "design.md" in filenames_in_errors

    def test_two_wrong_manifest_fields_both_reported(self, tmp_path: Path):
        manifest_data = {
            "phases": {
                "intake": {"status": "pending"},
                "vetting": {"status": "in_progress"},
            }
        }
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={
                "phases.intake.status": "completed",
                "phases.vetting.status": "completed",
            },
            design_spec_sections=["Overview"],
        )
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
            manifest_content=manifest_data,
            design_spec_content="## Overview\nContent.",
        )

        errors = validate(fixture, project)

        assert any("phases.intake.status" in e for e in errors)
        assert any("phases.vetting.status" in e for e in errors)

    def test_two_missing_sections_both_reported(self, tmp_path: Path):
        design_md = "## Overview\nSome content."
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={},
            design_spec_sections=["Problem Statement", "Learning Objectives"],
        )
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
            design_spec_content=design_md,
        )

        errors = validate(fixture, project)

        assert any("Problem Statement" in e for e in errors)
        assert any("Learning Objectives" in e for e in errors)


# ---------------------------------------------------------------------------
# 7. Return type contract
# ---------------------------------------------------------------------------


class TestReturnTypeContract:
    def test_returns_list_on_pass(self, tmp_path: Path):
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={},
            design_spec_sections=["Overview"],
        )
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
            design_spec_content="## Overview\nContent.",
        )

        result = validate(fixture, project)

        assert isinstance(result, list)

    def test_returns_list_on_failure(self, tmp_path: Path):
        fixture = make_fixture(
            files=["publishing-house/missing.yaml"],
            manifest={},
            design_spec_sections=["Overview"],
        )
        project = setup_project_dir(
            tmp_path,
            design_spec_content="## Overview\nContent.",
        )

        result = validate(fixture, project)

        assert isinstance(result, list)
        assert all(isinstance(e, str) for e in result)

    def test_error_strings_are_non_empty(self, tmp_path: Path):
        fixture = make_fixture(
            files=["publishing-house/missing.yaml"],
            manifest={},
            design_spec_sections=["Overview"],
        )
        project = setup_project_dir(
            tmp_path,
            design_spec_content="## Overview\nContent.",
        )

        errors = validate(fixture, project)

        assert all(e.strip() for e in errors)


# ---------------------------------------------------------------------------
# 8. Manifest file missing when manifest field checks are requested
# ---------------------------------------------------------------------------


class TestManifestFileMissingWithFieldChecks:
    def test_manifest_yaml_missing_with_field_checks_returns_error(self, tmp_path: Path):
        """When manifest field checks are defined but manifest.yaml is absent,
        the validator should return an error rather than crash."""
        fixture = make_fixture(
            files=[],
            manifest={"phases.intake.status": "completed"},
            design_spec_sections=["Overview"],
        )
        # project has design.md but NO manifest.yaml at the expected location
        project = setup_project_dir(
            tmp_path,
            design_spec_content="## Overview\nContent.",
        )

        errors = validate(fixture, project)

        assert isinstance(errors, list)
        assert len(errors) >= 1
        # Error should mention manifest
        assert any("manifest" in e.lower() for e in errors)

    def test_manifest_yaml_missing_error_is_descriptive(self, tmp_path: Path):
        fixture = make_fixture(
            files=[],
            manifest={"phases.intake.status": "completed"},
            design_spec_sections=["Overview"],
        )
        project = setup_project_dir(
            tmp_path,
            design_spec_content="## Overview\nContent.",
        )

        errors = validate(fixture, project)

        # Should not be a generic/empty string
        assert all(len(e) > 10 for e in errors)


# ---------------------------------------------------------------------------
# 9. Invalid YAML in manifest.yaml
# ---------------------------------------------------------------------------


class TestManifestInvalidYaml:
    def test_invalid_yaml_returns_error_not_crash(self, tmp_path: Path):
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={"phases.intake.status": "completed"},
            design_spec_sections=["Overview"],
        )
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
            design_spec_content="## Overview\nContent.",
        )
        # Overwrite manifest.yaml with invalid YAML
        manifest_path = project / "publishing-house" / "manifest.yaml"
        manifest_path.write_text("key: [unclosed bracket\n", encoding="utf-8")

        errors = validate(fixture, project)

        assert isinstance(errors, list)
        assert len(errors) >= 1
        assert any("yaml" in e.lower() or "parse" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# 10. Non-dict intermediate node in dotted manifest path
# ---------------------------------------------------------------------------


class TestManifestNonDictIntermediateNode:
    def test_non_dict_intermediate_node_returns_error(self, tmp_path: Path):
        """If a dotted path traverses through a scalar instead of a dict,
        the validator should return a descriptive error."""
        # phases.intake is a string, not a dict — can't navigate .status
        manifest_data = {"phases": {"intake": "not-a-dict"}}
        fixture = make_fixture(
            files=["publishing-house/manifest.yaml"],
            manifest={"phases.intake.status": "completed"},
            design_spec_sections=["Overview"],
        )
        project = setup_project_dir(
            tmp_path,
            files=["publishing-house/manifest.yaml"],
            manifest_content=manifest_data,
            design_spec_content="## Overview\nContent.",
        )

        errors = validate(fixture, project)

        assert len(errors) >= 1
        assert any("phases.intake.status" in e for e in errors)
