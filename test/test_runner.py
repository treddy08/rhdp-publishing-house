"""
Tests for ph_test.runner — TDD (RED phase first).

Covers:
  - RunResult dataclass fields: turns, termination_reason, conversation, errors
  - Loop terminates on APPROVAL_GATE_REACHED in tester response
  - Loop terminates at max_turns with termination_reason="max_turns"
  - First tester message is always fixture.initial_prompt
  - Tester receives orchestrator's last response in context each turn
  - run() raises ValueError when MAAS_API_KEY env var is not set
  - run() with mock_mcp=MCPMock() uses mocked MCP (not real portal)
  - Conversation log has correct turn structure
  - API error is captured in RunResult.errors and loop stops gracefully
"""
from __future__ import annotations

import os
import sys
import textwrap
from dataclasses import fields
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Make src/ importable when running from repo root or from test/
# conftest.py already inserts the repo root; we also ensure src/ is on path.
_repo_root = str(Path(__file__).parent.parent)
_src_dir = str(Path(__file__).parent.parent / "src")
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from ph_test.fixtures import Fixture, load_fixture
from ph_test.mcp_mock import MCPMock
from ph_test.runner import RunResult, run

# ---------------------------------------------------------------------------
# Shared helpers / fixtures
# ---------------------------------------------------------------------------

ANSIBLE_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "onboarded" / "ansible.yaml"
PROJECT_DIR = Path(__file__).parent.parent  # repo root as a stand-in


def _make_fixture(
    mode: str = "onboarded",
    product: str = "ansible",
    name: str = "test-run",
    initial_prompt: str = "Build me an EDA workshop.",
    follow_up_details: str = "Use AAP 2.5 with EDA controller.",
) -> Fixture:
    """Build a minimal valid Fixture for runner tests."""
    return Fixture(
        mode=mode,  # type: ignore[arg-type]
        product=product,
        name=name,
        initial_prompt=initial_prompt,
        follow_up_details=follow_up_details,
        expected_outcomes={
            "files": ["publishing-house/spec/design.md"],
            "manifest": {"phases.intake.status": "completed"},
            "design_spec_sections": ["Problem Statement"],
        },
    )


def _make_openai_message(text: str) -> MagicMock:
    """Return a minimal mock that looks like an OpenAI ChatCompletion response."""
    message = MagicMock()
    message.content = text
    choice = MagicMock()
    choice.message = message
    completion = MagicMock()
    completion.choices = [choice]
    return completion


def _make_client_mock(
    tester_responses: list[str],
    orchestrator_responses: list[str],
) -> MagicMock:
    """
    Build a mock openai.OpenAI where chat.completions.create alternates:
    odd calls → tester response, even calls → orchestrator response.

    The runner calls: tester, orchestrator, tester, orchestrator, ...
    So call index 0 → tester[0], 1 → orchestrator[0], 2 → tester[1], ...
    """
    call_count = [0]
    t_idx = [0]
    o_idx = [0]

    def _create(**kwargs: Any) -> MagicMock:
        turn = call_count[0]
        call_count[0] += 1
        # Determine which agent by checking system prompt content
        messages = kwargs.get("messages", [])
        system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
        if "automated tester" in system.lower() or "simulating a red hat" in system.lower():
            # tester call
            idx = t_idx[0]
            t_idx[0] += 1
            text = tester_responses[min(idx, len(tester_responses) - 1)]
        else:
            # orchestrator call
            idx = o_idx[0]
            o_idx[0] += 1
            text = orchestrator_responses[min(idx, len(orchestrator_responses) - 1)]
        return _make_openai_message(text)

    client = MagicMock()
    client.chat.completions.create.side_effect = _create
    return client


# ---------------------------------------------------------------------------
# 1. RunResult dataclass contract
# ---------------------------------------------------------------------------


class TestRunResultDataclass:
    def test_has_turns_field(self):
        field_names = {f.name for f in fields(RunResult)}
        assert "turns" in field_names

    def test_has_termination_reason_field(self):
        field_names = {f.name for f in fields(RunResult)}
        assert "termination_reason" in field_names

    def test_has_conversation_field(self):
        field_names = {f.name for f in fields(RunResult)}
        assert "conversation" in field_names

    def test_has_errors_field(self):
        field_names = {f.name for f in fields(RunResult)}
        assert "errors" in field_names

    def test_can_instantiate_with_all_fields(self):
        result = RunResult(
            turns=3,
            termination_reason="approval_gate",
            conversation=[{"role": "tester", "content": "hello"}],
            errors=[],
        )
        assert result.turns == 3
        assert result.termination_reason == "approval_gate"
        assert result.conversation == [{"role": "tester", "content": "hello"}]
        assert result.errors == []

    def test_turns_is_int(self):
        result = RunResult(turns=5, termination_reason="max_turns", conversation=[], errors=[])
        assert isinstance(result.turns, int)

    def test_termination_reason_is_str(self):
        result = RunResult(turns=1, termination_reason="error", conversation=[], errors=[])
        assert isinstance(result.termination_reason, str)

    def test_conversation_is_list(self):
        result = RunResult(turns=0, termination_reason="error", conversation=[], errors=[])
        assert isinstance(result.conversation, list)

    def test_errors_is_list(self):
        result = RunResult(turns=0, termination_reason="error", conversation=[], errors=["oops"])
        assert isinstance(result.errors, list)


# ---------------------------------------------------------------------------
# 2. run() raises ValueError when MAAS_API_KEY is not set
# ---------------------------------------------------------------------------


class TestAPIKeyRequired:
    def test_raises_value_error_when_no_api_key(self, tmp_path):
        fixture = _make_fixture()
        env = {k: v for k, v in os.environ.items() if k != "MAAS_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="MAAS_API_KEY"):
                run(fixture, project_dir=tmp_path)

    def test_raises_value_error_when_api_key_is_empty_string(self, tmp_path):
        fixture = _make_fixture()
        with patch.dict(os.environ, {"MAAS_API_KEY": ""}):
            with pytest.raises(ValueError, match="MAAS_API_KEY"):
                run(fixture, project_dir=tmp_path)


# ---------------------------------------------------------------------------
# 3. Termination: APPROVAL_GATE_REACHED in tester response
# ---------------------------------------------------------------------------


class TestApprovalGateTermination:
    def test_terminates_on_approval_gate_signal(self, tmp_path):
        fixture = _make_fixture()
        mock_client = _make_client_mock(
            tester_responses=["APPROVAL_GATE_REACHED"],
            orchestrator_responses=["Great, let's proceed!"],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock())
        assert result.termination_reason == "approval_gate"

    def test_approval_gate_termination_stops_loop_early(self, tmp_path):
        """Should stop after 1 tester response, not run all 20 turns."""
        fixture = _make_fixture()
        mock_client = _make_client_mock(
            tester_responses=["APPROVAL_GATE_REACHED"],
            orchestrator_responses=["Proceeding to phase 4"],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock())
        assert result.turns < 20

    def test_approval_gate_embedded_in_longer_response(self, tmp_path):
        """APPROVAL_GATE_REACHED anywhere in tester response should trigger."""
        fixture = _make_fixture()
        mock_client = _make_client_mock(
            tester_responses=["Looks great! APPROVAL_GATE_REACHED Thank you."],
            orchestrator_responses=["Moving forward."],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock())
        assert result.termination_reason == "approval_gate"

    def test_turns_count_on_approval_gate(self, tmp_path):
        """turns should reflect how many full tester+orchestrator pairs completed."""
        fixture = _make_fixture()
        mock_client = _make_client_mock(
            tester_responses=["Good progress.", "APPROVAL_GATE_REACHED"],
            orchestrator_responses=["What's the scope?", "Ready to move to writing"],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock())
        assert result.termination_reason == "approval_gate"
        assert result.turns >= 1


# ---------------------------------------------------------------------------
# 4. Termination: max_turns reached
# ---------------------------------------------------------------------------


class TestMaxTurnsTermination:
    def test_terminates_at_default_max_turns(self, tmp_path):
        fixture = _make_fixture()
        mock_client = _make_client_mock(
            tester_responses=["Keep going, not done yet."],
            orchestrator_responses=["Tell me more about your requirements."],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock())
        assert result.termination_reason == "max_turns"
        assert result.turns == 20

    def test_terminates_at_custom_max_turns(self, tmp_path):
        fixture = _make_fixture()
        mock_client = _make_client_mock(
            tester_responses=["Not done yet."],
            orchestrator_responses=["What's next?"],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock(), max_turns=3)
        assert result.termination_reason == "max_turns"
        assert result.turns == 3

    def test_max_turns_one_runs_exactly_one_turn(self, tmp_path):
        fixture = _make_fixture()
        mock_client = _make_client_mock(
            tester_responses=["Not done."],
            orchestrator_responses=["OK."],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock(), max_turns=1)
        assert result.turns == 1
        assert result.termination_reason == "max_turns"


# ---------------------------------------------------------------------------
# 5. First tester message is fixture.initial_prompt
# ---------------------------------------------------------------------------


class TestFirstTesterMessage:
    def test_first_conversation_entry_is_tester_with_initial_prompt(self, tmp_path):
        prompt = "Build me an EDA lab from scratch."
        fixture = _make_fixture(initial_prompt=prompt)
        mock_client = _make_client_mock(
            tester_responses=["APPROVAL_GATE_REACHED"],
            orchestrator_responses=["Let's start!"],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock(), max_turns=5)
        # First conversation entry must be tester role with initial_prompt
        first = result.conversation[0]
        assert first["role"] == "tester"
        assert first["content"] == prompt

    def test_initial_prompt_sent_in_first_api_call(self, tmp_path):
        prompt = "Build me a custom lab."
        fixture = _make_fixture(initial_prompt=prompt)
        call_args_list: list[dict] = []

        def _capture_create(**kwargs: Any) -> MagicMock:
            call_args_list.append(kwargs)
            messages = kwargs.get("messages", []); system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
            if "automated tester" in system.lower() or "simulating a red hat" in system.lower():
                return _make_openai_message("APPROVAL_GATE_REACHED")
            return _make_openai_message("Here is my plan.")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = _capture_create

        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                run(fixture, project_dir=tmp_path, mock_mcp=MCPMock(), max_turns=2)

        # First call should contain the initial_prompt in its messages
        first_call = call_args_list[0]
        messages = first_call.get("messages", [])
        all_content = " ".join(
            m.get("content", "") if isinstance(m.get("content"), str) else ""
            for m in messages
        )
        assert prompt in all_content


# ---------------------------------------------------------------------------
# 6. Tester receives orchestrator's last response in context each turn
# ---------------------------------------------------------------------------


class TestTesterReceivesOrchestratorContext:
    def test_orchestrator_response_appears_in_next_tester_call(self, tmp_path):
        fixture = _make_fixture()
        orchestrator_reply = "What is the target audience for this lab?"
        tester_calls: list[dict] = []

        call_count = [0]

        def _create(**kwargs: Any) -> MagicMock:
            messages = kwargs.get("messages", []); system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
            is_tester = (
                "automated tester" in system.lower()
                or "simulating a red hat" in system.lower()
            )
            if is_tester:
                tester_calls.append(kwargs)
                call_count[0] += 1
                if call_count[0] >= 2:
                    return _make_openai_message("APPROVAL_GATE_REACHED")
                return _make_openai_message("Ansible practitioners.")
            return _make_openai_message(orchestrator_reply)

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = _create

        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                run(fixture, project_dir=tmp_path, mock_mcp=MCPMock(), max_turns=5)

        # Second tester call (index 1) should include orchestrator's reply
        assert len(tester_calls) >= 2, "Expected at least 2 tester calls"
        second_call = tester_calls[1]
        messages = second_call.get("messages", [])
        all_content = " ".join(
            m.get("content", "") if isinstance(m.get("content"), str) else str(m.get("content", ""))
            for m in messages
        )
        assert orchestrator_reply in all_content


# ---------------------------------------------------------------------------
# 7. Conversation log structure
# ---------------------------------------------------------------------------


class TestConversationLogStructure:
    def test_conversation_entries_have_role_and_content(self, tmp_path):
        fixture = _make_fixture()
        mock_client = _make_client_mock(
            tester_responses=["APPROVAL_GATE_REACHED"],
            orchestrator_responses=["Here is my plan."],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock())
        for entry in result.conversation:
            assert "role" in entry, f"Missing 'role' in entry: {entry}"
            assert "content" in entry, f"Missing 'content' in entry: {entry}"

    def test_conversation_roles_are_tester_and_orchestrator(self, tmp_path):
        fixture = _make_fixture()
        mock_client = _make_client_mock(
            tester_responses=["Initial request.", "APPROVAL_GATE_REACHED"],
            orchestrator_responses=["Let me ask: what's the scope?", "Approved."],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock(), max_turns=5)
        roles = {entry["role"] for entry in result.conversation}
        assert roles.issubset({"tester", "orchestrator"}), f"Unexpected roles: {roles}"

    def test_conversation_alternates_tester_orchestrator(self, tmp_path):
        """Entries should interleave: tester, orchestrator, tester, orchestrator..."""
        fixture = _make_fixture()
        mock_client = _make_client_mock(
            tester_responses=["Turn 1 tester.", "APPROVAL_GATE_REACHED"],
            orchestrator_responses=["Turn 1 orch.", "Turn 2 orch."],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock(), max_turns=5)
        roles = [e["role"] for e in result.conversation]
        # Must start with tester
        assert roles[0] == "tester"
        # Must alternate
        for i in range(len(roles) - 1):
            assert roles[i] != roles[i + 1], f"Consecutive same role at positions {i},{i+1}: {roles}"

    def test_conversation_content_matches_api_responses(self, tmp_path):
        tester_msg = "Please build a 3-module lab."
        orch_msg = "What products are needed?"
        fixture = _make_fixture(initial_prompt=tester_msg)
        mock_client = _make_client_mock(
            tester_responses=[tester_msg, "APPROVAL_GATE_REACHED"],
            orchestrator_responses=[orch_msg],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock(), max_turns=3)

        all_content = [e["content"] for e in result.conversation]
        # Initial prompt must be in conversation content
        assert tester_msg in all_content


# ---------------------------------------------------------------------------
# 8. Error handling: API error captured in RunResult.errors, loop stops
# ---------------------------------------------------------------------------


class TestAPIErrorHandling:
    def test_api_error_captured_in_errors_list(self, tmp_path):
        fixture = _make_fixture()

        def _create(**kwargs: Any) -> MagicMock:
            raise RuntimeError("Simulated API failure")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = _create

        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock())

        assert len(result.errors) > 0

    def test_api_error_sets_termination_reason_to_error(self, tmp_path):
        fixture = _make_fixture()

        def _create(**kwargs: Any) -> MagicMock:
            raise RuntimeError("Simulated API failure")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = _create

        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock())

        assert result.termination_reason == "error"

    def test_api_error_returns_run_result_not_exception(self, tmp_path):
        """run() must not raise — it must return a RunResult with error info."""
        fixture = _make_fixture()

        def _create(**kwargs: Any) -> MagicMock:
            raise ConnectionError("Network failure")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = _create

        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock())

        assert isinstance(result, RunResult)

    def test_error_message_contains_exception_text(self, tmp_path):
        fixture = _make_fixture()
        error_text = "Service temporarily unavailable"

        def _create(**kwargs: Any) -> MagicMock:
            raise RuntimeError(error_text)

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = _create

        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock())

        assert any(error_text in err for err in result.errors)

    def test_api_error_on_second_turn_stops_gracefully(self, tmp_path):
        """Error on orchestrator's first call should still stop cleanly."""
        fixture = _make_fixture()
        call_count = [0]

        def _create(**kwargs: Any) -> MagicMock:
            messages = kwargs.get("messages", []); system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
            is_tester = (
                "automated tester" in system.lower()
                or "simulating a red hat" in system.lower()
            )
            if is_tester:
                return _make_openai_message("Here is my request.")
            raise RuntimeError("Orchestrator failed")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = _create

        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock())

        assert result.termination_reason == "error"
        assert len(result.errors) > 0


# ---------------------------------------------------------------------------
# 9. mock_mcp integration
# ---------------------------------------------------------------------------


class TestMCPMockIntegration:
    def test_run_with_mock_mcp_does_not_raise(self, tmp_path):
        fixture = _make_fixture()
        mock_client = _make_client_mock(
            tester_responses=["APPROVAL_GATE_REACHED"],
            orchestrator_responses=["All set."],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock())
        assert isinstance(result, RunResult)

    def test_run_without_mock_mcp_still_works_when_mocked(self, tmp_path):
        """mock_mcp=None is valid; the runner uses real MCP (mocked at Anthropic level)."""
        fixture = _make_fixture()
        mock_client = _make_client_mock(
            tester_responses=["APPROVAL_GATE_REACHED"],
            orchestrator_responses=["Done."],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=None)
        assert isinstance(result, RunResult)


# ---------------------------------------------------------------------------
# 10. Approval signal detection: various signal phrases
# ---------------------------------------------------------------------------


class TestApprovalSignalDetection:
    @pytest.mark.parametrize(
        "signal",
        [
            "APPROVAL_GATE_REACHED",
            "Do you approve the design spec?",
            "This is an approval gate. Please review.",
            "Phase 4 is ready to begin.",
            "proceed to writing the content",
            "Ready to move to writing",
        ],
    )
    def test_approval_signals_trigger_gate_termination(self, tmp_path, signal):
        """All listed approval signals in orchestrator output should prompt tester to reply APPROVAL_GATE_REACHED."""
        fixture = _make_fixture()
        # Tester sees orchestrator signal and replies APPROVAL_GATE_REACHED
        mock_client = _make_client_mock(
            tester_responses=["APPROVAL_GATE_REACHED"],
            orchestrator_responses=[signal],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock(), max_turns=5)
        assert result.termination_reason == "approval_gate"


# ---------------------------------------------------------------------------
# 10b. Branch coverage — internal helpers and verbose paths
# ---------------------------------------------------------------------------


class TestBranchCoverage:
    def test_extract_text_returns_empty_when_no_text_attr(self, tmp_path):
        """_extract_text returns '' for empty choices list (OpenAI format)."""
        from ph_test.runner import _extract_text

        msg = MagicMock()
        msg.choices = []  # empty choices → IndexError → returns ""
        assert _extract_text(msg) == ""

    def test_load_skill_md_fallback_when_file_missing(self, tmp_path):
        """_load_skill_md returns placeholder when SKILL.md does not exist."""
        from ph_test import runner as runner_mod
        from pathlib import Path

        original = runner_mod._SKILL_MD_PATH
        try:
            runner_mod._SKILL_MD_PATH = tmp_path / "nonexistent.md"
            result = runner_mod._load_skill_md()
            assert "Orchestrator" in result
        finally:
            runner_mod._SKILL_MD_PATH = original

    def test_read_manifest_returns_empty_when_missing(self, tmp_path):
        """_read_manifest returns '' when manifest.yaml does not exist."""
        from ph_test.runner import _read_manifest

        result = _read_manifest(tmp_path)
        assert result == ""

    def test_read_manifest_returns_content_when_present(self, tmp_path):
        """_read_manifest returns file content when manifest.yaml exists."""
        from ph_test.runner import _read_manifest

        manifest_dir = tmp_path / "publishing-house"
        manifest_dir.mkdir()
        manifest_file = manifest_dir / "manifest.yaml"
        manifest_file.write_text("project:\n  name: test\n", encoding="utf-8")

        result = _read_manifest(tmp_path)
        assert "project" in result

    def test_verbose_mode_orchestrator_error_path(self, tmp_path, capsys):
        """verbose=True prints error message when orchestrator call fails."""
        fixture = _make_fixture()

        def _create(**kwargs: Any) -> MagicMock:
            raise RuntimeError("orch error verbose test")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = _create

        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(
                    fixture, project_dir=tmp_path, mock_mcp=MCPMock(), verbose=True
                )

        assert result.termination_reason == "error"
        captured = capsys.readouterr()
        assert "ERROR" in captured.out or "error" in captured.out.lower()

    def test_tester_api_error_stops_gracefully(self, tmp_path):
        """Error on tester's call (after orchestrator succeeded) sets termination_reason=error."""
        fixture = _make_fixture()

        def _create(**kwargs: Any) -> MagicMock:
            messages = kwargs.get("messages", []); system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
            is_tester = (
                "automated tester" in system.lower()
                or "simulating a red hat" in system.lower()
            )
            if is_tester:
                raise RuntimeError("Tester API failure")
            return _make_openai_message("What is the scope?")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = _create

        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock())

        assert result.termination_reason == "error"
        assert len(result.errors) > 0
        assert any("tester" in e.lower() or "Tester" in e for e in result.errors)

    def test_verbose_tester_error_path_prints_error(self, tmp_path, capsys):
        """verbose=True prints error when tester API call fails."""
        fixture = _make_fixture()

        def _create(**kwargs: Any) -> MagicMock:
            messages = kwargs.get("messages", []); system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
            is_tester = (
                "automated tester" in system.lower()
                or "simulating a red hat" in system.lower()
            )
            if is_tester:
                raise RuntimeError("tester verbose error")
            return _make_openai_message("What do you need?")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = _create

        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(
                    fixture, project_dir=tmp_path, mock_mcp=MCPMock(), verbose=True
                )

        assert result.termination_reason == "error"
        captured = capsys.readouterr()
        assert "ERROR" in captured.out

    def test_verbose_mode_prints_tester_and_orchestrator_content(self, tmp_path, capsys):
        """verbose=True prints turn content to stdout."""
        fixture = _make_fixture()
        mock_client = _make_client_mock(
            tester_responses=["APPROVAL_GATE_REACHED"],
            orchestrator_responses=["Ready to move to writing"],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                run(fixture, project_dir=tmp_path, mock_mcp=MCPMock(), verbose=True)

        captured = capsys.readouterr()
        assert len(captured.out) > 0


# ---------------------------------------------------------------------------
# 11. run() signature and default parameters
# ---------------------------------------------------------------------------


class TestRunSignature:
    def test_default_max_turns_is_20(self, tmp_path):
        fixture = _make_fixture()
        mock_client = _make_client_mock(
            tester_responses=["Not done."],
            orchestrator_responses=["Continue."],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock())
        assert result.turns == 20

    def test_verbose_flag_accepted_without_error(self, tmp_path):
        fixture = _make_fixture()
        mock_client = _make_client_mock(
            tester_responses=["APPROVAL_GATE_REACHED"],
            orchestrator_responses=["OK."],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock(), verbose=True)
        assert isinstance(result, RunResult)

    def test_errors_empty_on_successful_run(self, tmp_path):
        fixture = _make_fixture()
        mock_client = _make_client_mock(
            tester_responses=["APPROVAL_GATE_REACHED"],
            orchestrator_responses=["Proceeding."],
        )
        with patch.dict(os.environ, {"MAAS_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                result = run(fixture, project_dir=tmp_path, mock_mcp=MCPMock())
        assert result.errors == []
