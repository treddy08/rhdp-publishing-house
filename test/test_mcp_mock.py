"""
Tests for MCPMock — ph-test harness MCP interceptor.

TDD: these tests are written BEFORE the implementation.
Run with: python -m pytest test/test_mcp_mock.py -v
"""

import pytest
from pathlib import Path

# Location of the YAML fixture relative to this file
MOCKS_DIR = Path(__file__).parent / "mocks"
MCP_RESPONSES_YAML = MOCKS_DIR / "mcp_responses.yaml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock(**kwargs):
    """Import and instantiate MCPMock, forwarding any kwargs."""
    from src.ph_test.mcp_mock import MCPMock
    return MCPMock(**kwargs)


# ===========================================================================
# 1. Initialisation
# ===========================================================================

class TestMCPMockInit:
    def test_loads_default_yaml_on_init(self):
        """MCPMock() with no args loads the bundled mcp_responses.yaml."""
        mock = make_mock()
        # Verify internal state is populated (not empty)
        assert mock._responses, "Expected non-empty responses after init"

    def test_accepts_explicit_responses_path(self):
        """MCPMock(responses_path=...) loads from the supplied path."""
        mock = make_mock(responses_path=MCP_RESPONSES_YAML)
        assert mock._responses, "Expected non-empty responses from explicit path"

    def test_explicit_path_as_string_is_accepted(self):
        """responses_path may be a plain string, not just a Path."""
        mock = make_mock(responses_path=str(MCP_RESPONSES_YAML))
        assert mock._responses

    def test_missing_yaml_raises_file_not_found(self):
        """Passing a non-existent path raises FileNotFoundError, not a silent failure."""
        with pytest.raises(FileNotFoundError):
            make_mock(responses_path="/does/not/exist/mcp_responses.yaml")


# ===========================================================================
# 2. Known-tool lookups
# ===========================================================================

class TestKnownToolLookups:
    @pytest.fixture(autouse=True)
    def mock(self):
        self._mock = make_mock()

    def test_ph_rcars_query_returns_dict(self):
        result = self._mock("ph_rcars_query", {})
        assert isinstance(result, dict)

    def test_ph_rcars_query_has_status_key(self):
        result = self._mock("ph_rcars_query", {})
        assert "status" in result

    def test_ph_rcars_query_has_recommendation_key(self):
        result = self._mock("ph_rcars_query", {})
        assert "recommendation" in result

    def test_ph_rcars_query_status_value(self):
        result = self._mock("ph_rcars_query", {})
        assert result["status"] == "complete"

    def test_ph_rcars_query_recommendation_value(self):
        result = self._mock("ph_rcars_query", {})
        assert result["recommendation"] == "proceed"

    def test_ph_sync_manifest_returns_dict(self):
        result = self._mock("ph_sync_manifest", {})
        assert isinstance(result, dict)

    def test_ph_sync_manifest_success_is_true(self):
        result = self._mock("ph_sync_manifest", {})
        assert result["success"] is True

    def test_ph_sync_manifest_has_project_id(self):
        result = self._mock("ph_sync_manifest", {})
        assert "project_id" in result

    def test_ph_store_intake_results_success_true(self):
        result = self._mock("ph_store_intake_results", {})
        assert result["success"] is True

    def test_ph_store_intake_results_has_session_id(self):
        result = self._mock("ph_store_intake_results", {})
        assert "session_id" in result

    def test_ph_list_intake_sessions_has_sessions_key(self):
        result = self._mock("ph_list_intake_sessions", {})
        assert "sessions" in result
        assert isinstance(result["sessions"], list)

    def test_ph_get_intake_results_has_owner_email(self):
        result = self._mock("ph_get_intake_results", {})
        assert "owner_email" in result

    def test_ph_list_projects_has_projects_key(self):
        result = self._mock("ph_list_projects", {})
        assert "projects" in result
        assert isinstance(result["projects"], list)

    def test_ph_rcars_catalog_search_has_items_and_total(self):
        result = self._mock("ph_rcars_catalog_search", {})
        assert "items" in result
        assert "total" in result

    def test_ph_record_express_run_success_true(self):
        result = self._mock("ph_record_express_run", {})
        assert result["success"] is True

    def test_ph_record_express_run_has_run_id(self):
        result = self._mock("ph_record_express_run", {})
        assert "run_id" in result


# ===========================================================================
# 3. Unknown-tool error behaviour
# ===========================================================================

class TestUnknownToolErrors:
    @pytest.fixture(autouse=True)
    def mock(self):
        self._mock = make_mock()

    def test_unknown_tool_raises_key_error(self):
        with pytest.raises(KeyError):
            self._mock("unknown_tool", {})

    def test_key_error_message_contains_tool_name(self):
        tool_name = "ph_does_not_exist"
        with pytest.raises(KeyError) as exc_info:
            self._mock(tool_name, {})
        assert tool_name in str(exc_info.value)

    def test_empty_string_tool_name_raises_key_error(self):
        with pytest.raises(KeyError):
            self._mock("", {})

    def test_none_tool_name_raises_key_error(self):
        """None is not a valid tool name — must not silently produce a result."""
        with pytest.raises((KeyError, TypeError)):
            self._mock(None, {})  # type: ignore[arg-type]


# ===========================================================================
# 4. Callable interface
# ===========================================================================

class TestCallableInterface:
    def test_mock_instance_is_callable(self):
        mock = make_mock()
        assert callable(mock)

    def test_call_with_params_dict_is_accepted(self):
        """params dict is forwarded without error (mock ignores params by design)."""
        mock = make_mock()
        result = mock("ph_rcars_query", {"query": "test content"})
        assert isinstance(result, dict)

    def test_call_with_empty_params_is_accepted(self):
        mock = make_mock()
        result = mock("ph_rcars_query", {})
        assert isinstance(result, dict)

    def test_params_do_not_alter_response(self):
        """The mock returns the same fixture regardless of what params are passed."""
        mock = make_mock()
        r1 = mock("ph_rcars_query", {})
        r2 = mock("ph_rcars_query", {"query": "something different"})
        assert r1 == r2


# ===========================================================================
# 5. Pydantic schema validation for ph_rcars_query response
# ===========================================================================

class TestRCARSQuerySchema:
    """Validate that ph_rcars_query response matches the expected Pydantic schema."""

    @pytest.fixture(autouse=True)
    def result(self):
        mock = make_mock()
        self._result = mock("ph_rcars_query", {})

    def test_status_is_string(self):
        assert isinstance(self._result["status"], str)

    def test_recommendation_is_string(self):
        assert isinstance(self._result["recommendation"], str)

    def test_findings_is_list(self):
        assert isinstance(self._result["findings"], list)

    def test_overlap_score_is_float(self):
        assert isinstance(self._result["overlap_score"], float)

    def test_overlap_score_in_range(self):
        score = self._result["overlap_score"]
        assert 0.0 <= score <= 1.0

    def test_similar_items_is_list(self):
        assert isinstance(self._result["similar_items"], list)


# ===========================================================================
# 6. Pydantic schema validation for ph_sync_manifest response
# ===========================================================================

class TestSyncManifestSchema:
    @pytest.fixture(autouse=True)
    def result(self):
        mock = make_mock()
        self._result = mock("ph_sync_manifest", {})

    def test_success_is_bool(self):
        assert isinstance(self._result["success"], bool)

    def test_project_id_is_string(self):
        assert isinstance(self._result["project_id"], str)

    def test_project_id_not_empty(self):
        assert self._result["project_id"] != ""


# ===========================================================================
# 7. Response immutability — caller cannot mutate the fixture store
# ===========================================================================

class TestResponseImmutability:
    def test_mutating_returned_dict_does_not_affect_next_call(self):
        """Each __call__ must return a fresh copy so callers cannot pollute state."""
        mock = make_mock()
        first = mock("ph_rcars_query", {})
        first["status"] = "MUTATED"
        second = mock("ph_rcars_query", {})
        assert second["status"] == "complete", (
            "Mutating the returned dict should not affect the next call's response"
        )


# ===========================================================================
# 8. Default path resolves relative to mcp_mock.py (not cwd)
# ===========================================================================

class TestDefaultPathResolution:
    def test_default_path_is_independent_of_cwd(self, tmp_path, monkeypatch):
        """MCPMock() must find mcp_responses.yaml even when cwd is changed."""
        monkeypatch.chdir(tmp_path)
        # If the default is hardcoded as a relative path this will fail.
        mock = make_mock()
        result = mock("ph_rcars_query", {})
        assert result["status"] == "complete"


# ===========================================================================
# 9. Malformed YAML guard
# ===========================================================================

class TestMalformedYaml:
    def test_non_mapping_yaml_raises_value_error(self, tmp_path):
        """A YAML file whose top-level is a list (not a mapping) raises ValueError."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("- item_one\n- item_two\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Expected a YAML mapping"):
            make_mock(responses_path=bad_yaml)
