"""
Tests for ph_test.fixtures — TDD (RED phase first).

Covers:
  - load_fixture returns a Fixture object
  - Fixture field types and non-empty invariants
  - Mode is constrained to valid values
  - expected_outcomes sub-fields validated
  - Missing required fields raise ValidationError
  - Path argument accepts str and Path
  - File not found raises FileNotFoundError
  - Invalid YAML raises an appropriate error
  - Edge cases: empty strings, wrong types
"""
import sys
import textwrap
from pathlib import Path

import pytest

# Make src/ importable when running from repo root or from test/
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pydantic import ValidationError

from ph_test.fixtures import Fixture, load_fixture

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ANSIBLE_FIXTURE = Path(__file__).parent / "fixtures" / "onboarded" / "ansible.yaml"


def write_yaml(tmp_path: Path, filename: str, content: str) -> Path:
    """Write a YAML string to a temp file and return its path."""
    p = tmp_path / filename
    p.write_text(textwrap.dedent(content))
    return p


# ---------------------------------------------------------------------------
# 1. Happy-path: load_fixture with the real ansible.yaml fixture
# ---------------------------------------------------------------------------


class TestLoadFixtureHappyPath:
    def test_returns_fixture_instance(self):
        fixture = load_fixture(ANSIBLE_FIXTURE)
        assert isinstance(fixture, Fixture)

    def test_accepts_str_path(self):
        fixture = load_fixture(str(ANSIBLE_FIXTURE))
        assert isinstance(fixture, Fixture)

    def test_accepts_pathlib_path(self):
        fixture = load_fixture(Path(ANSIBLE_FIXTURE))
        assert isinstance(fixture, Fixture)

    def test_initial_prompt_is_non_empty_string(self):
        fixture = load_fixture(ANSIBLE_FIXTURE)
        assert isinstance(fixture.initial_prompt, str)
        assert fixture.initial_prompt.strip() != ""

    def test_follow_up_details_is_non_empty_string(self):
        fixture = load_fixture(ANSIBLE_FIXTURE)
        assert isinstance(fixture.follow_up_details, str)
        assert fixture.follow_up_details.strip() != ""

    def test_mode_is_valid(self):
        fixture = load_fixture(ANSIBLE_FIXTURE)
        assert fixture.mode in {"onboarded", "express", "self-published"}

    def test_product_is_non_empty_string(self):
        fixture = load_fixture(ANSIBLE_FIXTURE)
        assert isinstance(fixture.product, str)
        assert fixture.product.strip() != ""

    def test_name_is_non_empty_string(self):
        fixture = load_fixture(ANSIBLE_FIXTURE)
        assert isinstance(fixture.name, str)
        assert fixture.name.strip() != ""


# ---------------------------------------------------------------------------
# 2. expected_outcomes structure
# ---------------------------------------------------------------------------


class TestExpectedOutcomes:
    def test_files_is_non_empty_list(self):
        fixture = load_fixture(ANSIBLE_FIXTURE)
        assert isinstance(fixture.expected_outcomes.files, list)
        assert len(fixture.expected_outcomes.files) > 0

    def test_files_contains_strings(self):
        fixture = load_fixture(ANSIBLE_FIXTURE)
        for f in fixture.expected_outcomes.files:
            assert isinstance(f, str)
            assert f.strip() != ""

    def test_manifest_is_dict(self):
        fixture = load_fixture(ANSIBLE_FIXTURE)
        assert isinstance(fixture.expected_outcomes.manifest, dict)

    def test_manifest_has_dotted_path_keys(self):
        fixture = load_fixture(ANSIBLE_FIXTURE)
        # At least one key must contain a dot (dotted-path convention)
        keys = list(fixture.expected_outcomes.manifest.keys())
        assert any("." in k for k in keys), f"No dotted keys found in manifest: {keys}"

    def test_manifest_values_are_strings(self):
        fixture = load_fixture(ANSIBLE_FIXTURE)
        for k, v in fixture.expected_outcomes.manifest.items():
            assert isinstance(v, str), f"Key '{k}' has non-string value: {v!r}"

    def test_design_spec_sections_is_non_empty_list(self):
        fixture = load_fixture(ANSIBLE_FIXTURE)
        assert isinstance(fixture.expected_outcomes.design_spec_sections, list)
        assert len(fixture.expected_outcomes.design_spec_sections) > 0

    def test_design_spec_sections_contains_strings(self):
        fixture = load_fixture(ANSIBLE_FIXTURE)
        for s in fixture.expected_outcomes.design_spec_sections:
            assert isinstance(s, str)
            assert s.strip() != ""


# ---------------------------------------------------------------------------
# 3. Validation errors — missing required fields
# ---------------------------------------------------------------------------


class TestMissingRequiredFields:
    def test_missing_mode_raises_validation_error(self, tmp_path):
        yaml_file = write_yaml(
            tmp_path,
            "no_mode.yaml",
            """
            product: ansible
            name: test
            initial_prompt: "hello"
            follow_up_details: "world"
            expected_outcomes:
              files:
                - publishing-house/spec/design.md
              manifest:
                phases.intake.status: completed
              design_spec_sections:
                - Problem Statement
            """,
        )
        with pytest.raises(ValidationError):
            load_fixture(yaml_file)

    def test_missing_initial_prompt_raises_validation_error(self, tmp_path):
        yaml_file = write_yaml(
            tmp_path,
            "no_prompt.yaml",
            """
            mode: onboarded
            product: ansible
            name: test
            follow_up_details: "world"
            expected_outcomes:
              files:
                - publishing-house/spec/design.md
              manifest:
                phases.intake.status: completed
              design_spec_sections:
                - Problem Statement
            """,
        )
        with pytest.raises(ValidationError):
            load_fixture(yaml_file)

    def test_missing_follow_up_details_raises_validation_error(self, tmp_path):
        yaml_file = write_yaml(
            tmp_path,
            "no_followup.yaml",
            """
            mode: onboarded
            product: ansible
            name: test
            initial_prompt: "hello"
            expected_outcomes:
              files:
                - publishing-house/spec/design.md
              manifest:
                phases.intake.status: completed
              design_spec_sections:
                - Problem Statement
            """,
        )
        with pytest.raises(ValidationError):
            load_fixture(yaml_file)

    def test_missing_expected_outcomes_raises_validation_error(self, tmp_path):
        yaml_file = write_yaml(
            tmp_path,
            "no_outcomes.yaml",
            """
            mode: onboarded
            product: ansible
            name: test
            initial_prompt: "hello"
            follow_up_details: "world"
            """,
        )
        with pytest.raises(ValidationError):
            load_fixture(yaml_file)

    def test_missing_product_raises_validation_error(self, tmp_path):
        yaml_file = write_yaml(
            tmp_path,
            "no_product.yaml",
            """
            mode: onboarded
            name: test
            initial_prompt: "hello"
            follow_up_details: "world"
            expected_outcomes:
              files:
                - publishing-house/spec/design.md
              manifest:
                phases.intake.status: completed
              design_spec_sections:
                - Problem Statement
            """,
        )
        with pytest.raises(ValidationError):
            load_fixture(yaml_file)

    def test_missing_name_raises_validation_error(self, tmp_path):
        yaml_file = write_yaml(
            tmp_path,
            "no_name.yaml",
            """
            mode: onboarded
            product: ansible
            initial_prompt: "hello"
            follow_up_details: "world"
            expected_outcomes:
              files:
                - publishing-house/spec/design.md
              manifest:
                phases.intake.status: completed
              design_spec_sections:
                - Problem Statement
            """,
        )
        with pytest.raises(ValidationError):
            load_fixture(yaml_file)


# ---------------------------------------------------------------------------
# 4. Validation errors — invalid field values
# ---------------------------------------------------------------------------


class TestInvalidFieldValues:
    def test_invalid_mode_raises_validation_error(self, tmp_path):
        yaml_file = write_yaml(
            tmp_path,
            "bad_mode.yaml",
            """
            mode: invalid-mode
            product: ansible
            name: test
            initial_prompt: "hello"
            follow_up_details: "world"
            expected_outcomes:
              files:
                - publishing-house/spec/design.md
              manifest:
                phases.intake.status: completed
              design_spec_sections:
                - Problem Statement
            """,
        )
        with pytest.raises(ValidationError):
            load_fixture(yaml_file)

    def test_empty_initial_prompt_raises_validation_error(self, tmp_path):
        yaml_file = write_yaml(
            tmp_path,
            "empty_prompt.yaml",
            """
            mode: onboarded
            product: ansible
            name: test
            initial_prompt: "   "
            follow_up_details: "world"
            expected_outcomes:
              files:
                - publishing-house/spec/design.md
              manifest:
                phases.intake.status: completed
              design_spec_sections:
                - Problem Statement
            """,
        )
        with pytest.raises(ValidationError):
            load_fixture(yaml_file)

    def test_empty_follow_up_details_raises_validation_error(self, tmp_path):
        yaml_file = write_yaml(
            tmp_path,
            "empty_followup.yaml",
            """
            mode: onboarded
            product: ansible
            name: test
            initial_prompt: "hello"
            follow_up_details: "   "
            expected_outcomes:
              files:
                - publishing-house/spec/design.md
              manifest:
                phases.intake.status: completed
              design_spec_sections:
                - Problem Statement
            """,
        )
        with pytest.raises(ValidationError):
            load_fixture(yaml_file)

    def test_empty_files_list_raises_validation_error(self, tmp_path):
        yaml_file = write_yaml(
            tmp_path,
            "empty_files.yaml",
            """
            mode: onboarded
            product: ansible
            name: test
            initial_prompt: "hello"
            follow_up_details: "world"
            expected_outcomes:
              files: []
              manifest:
                phases.intake.status: completed
              design_spec_sections:
                - Problem Statement
            """,
        )
        with pytest.raises(ValidationError):
            load_fixture(yaml_file)

    def test_empty_design_spec_sections_raises_validation_error(self, tmp_path):
        yaml_file = write_yaml(
            tmp_path,
            "empty_sections.yaml",
            """
            mode: onboarded
            product: ansible
            name: test
            initial_prompt: "hello"
            follow_up_details: "world"
            expected_outcomes:
              files:
                - publishing-house/spec/design.md
              manifest:
                phases.intake.status: completed
              design_spec_sections: []
            """,
        )
        with pytest.raises(ValidationError):
            load_fixture(yaml_file)

    def test_whitespace_only_product_raises_validation_error(self, tmp_path):
        yaml_file = write_yaml(
            tmp_path,
            "blank_product.yaml",
            """
            mode: onboarded
            product: "   "
            name: test
            initial_prompt: "hello"
            follow_up_details: "world"
            expected_outcomes:
              files:
                - publishing-house/spec/design.md
              manifest:
                phases.intake.status: completed
              design_spec_sections:
                - Problem Statement
            """,
        )
        with pytest.raises(ValidationError):
            load_fixture(yaml_file)

    def test_whitespace_only_name_raises_validation_error(self, tmp_path):
        yaml_file = write_yaml(
            tmp_path,
            "blank_name.yaml",
            """
            mode: onboarded
            product: ansible
            name: "   "
            initial_prompt: "hello"
            follow_up_details: "world"
            expected_outcomes:
              files:
                - publishing-house/spec/design.md
              manifest:
                phases.intake.status: completed
              design_spec_sections:
                - Problem Statement
            """,
        )
        with pytest.raises(ValidationError):
            load_fixture(yaml_file)

    def test_files_not_a_list_raises_validation_error(self, tmp_path):
        yaml_file = write_yaml(
            tmp_path,
            "files_not_list.yaml",
            """
            mode: onboarded
            product: ansible
            name: test
            initial_prompt: "hello"
            follow_up_details: "world"
            expected_outcomes:
              files: "not-a-list"
              manifest:
                phases.intake.status: completed
              design_spec_sections:
                - Problem Statement
            """,
        )
        with pytest.raises(ValidationError):
            load_fixture(yaml_file)

    def test_manifest_not_a_dict_raises_validation_error(self, tmp_path):
        yaml_file = write_yaml(
            tmp_path,
            "manifest_not_dict.yaml",
            """
            mode: onboarded
            product: ansible
            name: test
            initial_prompt: "hello"
            follow_up_details: "world"
            expected_outcomes:
              files:
                - publishing-house/spec/design.md
              manifest: "not-a-dict"
              design_spec_sections:
                - Problem Statement
            """,
        )
        with pytest.raises(ValidationError):
            load_fixture(yaml_file)

    def test_files_containing_blank_string_raises_validation_error(self, tmp_path):
        """A list with a whitespace-only file path must be rejected."""
        yaml_file = write_yaml(
            tmp_path,
            "blank_file_item.yaml",
            """
            mode: onboarded
            product: ansible
            name: test
            initial_prompt: "hello"
            follow_up_details: "world"
            expected_outcomes:
              files:
                - "   "
              manifest:
                phases.intake.status: completed
              design_spec_sections:
                - Problem Statement
            """,
        )
        with pytest.raises(ValidationError):
            load_fixture(yaml_file)

    def test_design_spec_sections_containing_blank_string_raises_validation_error(
        self, tmp_path
    ):
        """A list with a whitespace-only section name must be rejected."""
        yaml_file = write_yaml(
            tmp_path,
            "blank_section_item.yaml",
            """
            mode: onboarded
            product: ansible
            name: test
            initial_prompt: "hello"
            follow_up_details: "world"
            expected_outcomes:
              files:
                - publishing-house/spec/design.md
              manifest:
                phases.intake.status: completed
              design_spec_sections:
                - "   "
            """,
        )
        with pytest.raises(ValidationError):
            load_fixture(yaml_file)


# ---------------------------------------------------------------------------
# 5. File I/O errors
# ---------------------------------------------------------------------------


class TestFileErrors:
    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_fixture(tmp_path / "does_not_exist.yaml")

    def test_invalid_yaml_raises_error(self, tmp_path):
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("mode: onboarded\n  bad indent: [unclosed")
        with pytest.raises(Exception):
            load_fixture(bad_yaml)


# ---------------------------------------------------------------------------
# 6. All three modes accepted
# ---------------------------------------------------------------------------


class TestAllModesAccepted:
    @pytest.mark.parametrize("mode", ["onboarded", "express", "self-published"])
    def test_valid_modes(self, tmp_path, mode):
        yaml_file = write_yaml(
            tmp_path,
            f"mode_{mode}.yaml",
            f"""
            mode: {mode}
            product: ansible
            name: test
            initial_prompt: "hello"
            follow_up_details: "world"
            expected_outcomes:
              files:
                - publishing-house/spec/design.md
              manifest:
                phases.intake.status: completed
              design_spec_sections:
                - Problem Statement
            """,
        )
        fixture = load_fixture(yaml_file)
        assert fixture.mode == mode


# ---------------------------------------------------------------------------
# 7. Immutability — Fixture is frozen (cannot mutate after creation)
# ---------------------------------------------------------------------------


class TestFixtureImmutability:
    def test_fixture_is_immutable(self):
        fixture = load_fixture(ANSIBLE_FIXTURE)
        with pytest.raises(Exception):
            fixture.mode = "express"  # type: ignore[misc]
