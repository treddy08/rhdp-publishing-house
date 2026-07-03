"""
ph_test.runner — Two-agent simulation loop for the PH autonomous E2E test harness.

Drives a conversation between:
  - Agent 1 (Tester): simulates a Red Hat content developer, guided by a fixture
  - Agent 2 (PH Orchestrator): runs under the PH orchestrator SKILL.md system prompt

The loop continues until one of three termination conditions:
  - "APPROVAL_GATE_REACHED" appears in the tester's response  → termination_reason="approval_gate"
  - max_turns is reached                                        → termination_reason="max_turns"
  - An API exception is raised                                  → termination_reason="error"
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import openai

from .fixtures import Fixture
from .mcp_mock import MCPMock

# ---------------------------------------------------------------------------
# Environment / model configuration
# ---------------------------------------------------------------------------

_MAAS_API_BASE = os.environ.get(
    "MAAS_API_BASE", "https://maas-rhdp.apps.maas.redhatworkshops.io/v1"
)
_TESTER_MODEL = os.environ.get("MAAS_TESTER_MODEL", "claude-haiku-4-5")
_ORCHESTRATOR_MODEL = os.environ.get("MAAS_ORCHESTRATOR_MODEL", "claude-sonnet-4-6")

# Path to the orchestrator skill definition
_SKILL_MD_PATH = (
    Path(__file__).parent.parent.parent / "skills-plugin" / "skills" / "orchestrator" / "SKILL.md"
)

# Approval-gate keywords — if the orchestrator says any of these, the tester
# should reply APPROVAL_GATE_REACHED (tester system prompt instructs this).
_APPROVAL_SIGNALS = [
    "APPROVAL_GATE_REACHED",
    "Do you approve",
    "approval gate",
    "Phase 4",
    "proceed to writing",
    "Ready to move to writing",
]


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass
class RunResult:
    """Outcome of a single harness run."""

    turns: int
    termination_reason: str  # "approval_gate" | "max_turns" | "error"
    conversation: list[dict]
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_skill_md() -> str:
    """Return the orchestrator SKILL.md content, or a placeholder if absent."""
    if _SKILL_MD_PATH.exists():
        return _SKILL_MD_PATH.read_text(encoding="utf-8")
    return "# PH Orchestrator\nYou are the RHDP Publishing House orchestrator."


def _tester_system_prompt(fixture: Fixture) -> str:
    return (
        "You are an automated tester simulating a Red Hat content developer using the PH Orchestrator.\n"
        f"Mode: {fixture.mode} | Product: {fixture.product}\n"
        "\n"
        "Initial Prompt (what you said to start):\n"
        f"{fixture.initial_prompt}\n"
        "\n"
        "Follow-up Details (use these to answer questions):\n"
        f"{fixture.follow_up_details}\n"
        "\n"
        "Rules:\n"
        "- Reply naturally as a developer would\n"
        "- Do NOT reveal you are a tester or AI\n"
        "- If the orchestrator asks something not in Follow-up Details, make a reasonable choice\n"
        "- When you see approval gate signals, reply exactly: APPROVAL_GATE_REACHED\n"
        'Approval signals: "Do you approve", "approval gate", "Phase 4", '
        '"proceed to writing", "Ready to move to writing"'
    )


def _orchestrator_system_prompt(manifest_state: str, project_dir: Path) -> str:
    skill_md = _load_skill_md()
    manifest_path = project_dir / "publishing-house" / "manifest.yaml"
    return (
        f"{skill_md}\n\n"
        "---\n"
        "## TEST HARNESS CONTEXT\n\n"
        f"The user's project is already initialized at: `{project_dir}`\n"
        f"Manifest is at: `{manifest_path}`\n"
        "The user has already cloned the template and is ready to begin intake.\n"
        "Do NOT ask them to clone a repo or run any shell commands.\n"
        "The user is talking to you directly — begin intake now.\n\n"
        "## Current manifest.yaml state\n\n"
        f"{manifest_state if manifest_state else '(empty — fresh project, start intake)'}\n"
    )


def _extract_text(message) -> str:
    """Pull plain text from an OpenAI-compatible chat completion response."""
    try:
        return message.choices[0].message.content or ""
    except (AttributeError, IndexError):
        return ""


def _contains_approval_gate(text: str) -> bool:
    return "APPROVAL_GATE_REACHED" in text


def _read_manifest(project_dir: Path) -> str:
    """Read publishing-house/manifest.yaml if it exists; return empty string otherwise."""
    manifest_path = project_dir / "publishing-house" / "manifest.yaml"
    if manifest_path.exists():
        return manifest_path.read_text(encoding="utf-8")
    return ""


# ---------------------------------------------------------------------------
# Public run() entry point
# ---------------------------------------------------------------------------


def run(
    fixture: Fixture,
    project_dir: Path,
    mock_mcp: MCPMock | None = None,
    max_turns: int = 20,
    verbose: bool = False,
) -> RunResult:
    """Execute a two-agent simulation loop.

    Parameters
    ----------
    fixture:
        The test scenario driving the tester agent.
    project_dir:
        Root directory of the PH project.  Used to read manifest.yaml.
    mock_mcp:
        If provided, MCP tool calls are intercepted via this mock.
        If None, real MCP calls are attempted (useful for integration runs).
    max_turns:
        Maximum number of tester→orchestrator round trips before stopping.
    verbose:
        If True, print each turn's content to stdout.

    Returns
    -------
    RunResult
        Summary of the run including all turns, termination reason,
        full conversation log, and any captured errors.

    Raises
    ------
    ValueError
        If MAAS_API_KEY is not set in the environment.
    """
    api_key = os.environ.get("MAAS_API_KEY")
    if not api_key:
        raise ValueError(
            "MAAS_API_KEY environment variable is not set. "
            "Export it before running the harness."
        )

    client = openai.OpenAI(
        api_key=api_key,
        base_url=os.environ.get("MAAS_API_BASE", _MAAS_API_BASE),
    )

    conversation: list[dict] = []
    errors: list[str] = []
    tester_system = _tester_system_prompt(fixture)

    # Turn 0: tester sends the initial_prompt directly (no API call needed for
    # the very first user message — it IS the initial_prompt).
    current_tester_message = fixture.initial_prompt
    conversation.append({"role": "tester", "content": current_tester_message})

    if verbose:
        print(f"[Turn 0] TESTER: {current_tester_message[:120]}")

    for turn in range(1, max_turns + 1):
        # --- Orchestrator call ---
        manifest_state = _read_manifest(project_dir)
        orch_system = _orchestrator_system_prompt(manifest_state, project_dir)
        orch_messages = [{"role": "user", "content": current_tester_message}]

        orch_text = ""
        for attempt in range(3):
            try:
                orch_response = client.chat.completions.create(
                    model=os.environ.get("MAAS_ORCHESTRATOR_MODEL", _ORCHESTRATOR_MODEL),
                    max_tokens=1024,
                    messages=[{"role": "system", "content": orch_system}] + orch_messages,
                )
                orch_text = _extract_text(orch_response)
                break
            except Exception as exc:
                if attempt == 2:
                    err = f"Turn {turn} orchestrator API error: {exc}"
                    errors.append(err)
                    if verbose:
                        print(f"[ERROR] {err}")
                    return RunResult(
                        turns=turn - 1,
                        termination_reason="error",
                        conversation=conversation,
                        errors=errors,
                    )
                import time; time.sleep(3)

        conversation.append({"role": "orchestrator", "content": orch_text})
        if verbose:
            print(f"[Turn {turn}] ORCHESTRATOR: {orch_text[:120]}")

        # --- Tester call ---
        # Build tester messages: include orchestrator's reply as context.
        tester_messages = [
            {"role": "user", "content": (
                f"The orchestrator responded:\n\n{orch_text}\n\n"
                "Please reply as the content developer."
            )},
        ]

        tester_text = ""
        for attempt in range(3):
            try:
                tester_response = client.chat.completions.create(
                    model=os.environ.get("MAAS_TESTER_MODEL", _TESTER_MODEL),
                    max_tokens=1024,
                    messages=[{"role": "system", "content": tester_system}] + tester_messages,
                )
                tester_text = _extract_text(tester_response)
                break
            except Exception as exc:
                if attempt == 2:
                    err = f"Turn {turn} tester API error: {exc}"
                    errors.append(err)
                    if verbose:
                        print(f"[ERROR] {err}")
                    return RunResult(
                        turns=turn,
                        termination_reason="error",
                        conversation=conversation,
                        errors=errors,
                    )
                import time; time.sleep(3)

        conversation.append({"role": "tester", "content": tester_text})
        if verbose:
            print(f"[Turn {turn}] TESTER: {tester_text[:120]}")

        # Check approval gate in tester reply
        if _contains_approval_gate(tester_text):
            return RunResult(
                turns=turn,
                termination_reason="approval_gate",
                conversation=conversation,
                errors=errors,
            )

        current_tester_message = tester_text

    # Exhausted max_turns
    return RunResult(
        turns=max_turns,
        termination_reason="max_turns",
        conversation=conversation,
        errors=errors,
    )
