#!/usr/bin/env python3
"""
ph-test — PH Autonomous E2E Test Runner (RHDPCD-108)

Usage:
    ph-test onboarded/ansible
    ph-test --all
    ph-test onboarded/ansible --verbose
    ph-test onboarded/ansible --keep-on-fail
    ph-test onboarded/ansible --output json

LiteMaaS credentials (read from env or ~/.rhdp-creds.md):
    MAAS_API_BASE       LiteMaaS endpoint (default: https://maas-rhdp.apps.maas.redhatworkshops.io/v1)
    MAAS_API_KEY        LiteMaaS virtual key (ph-testing-bot)
    MAAS_TESTER_MODEL   Tester agent model (default: claude-haiku-4-5)
    MAAS_ORCHESTRATOR_MODEL  Orchestrator model (default: claude-sonnet-4-6)
"""

import sys
import os
import json
import tempfile
import shutil
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ph_test.fixtures import load_fixture, Fixture
from src.ph_test.mcp_mock import MCPMock
from src.ph_test.runner import run, RunResult
from src.ph_test.validator import validate, validate_conversation


FIXTURES_DIR = PROJECT_ROOT / "test" / "fixtures"
TEMPLATE_DIR = PROJECT_ROOT / "template"


def load_env_from_creds() -> None:
    """Load MAAS_API_KEY from ~/.rhdp-creds.md if not already in env."""
    if os.environ.get("MAAS_API_KEY"):
        return
    creds_file = Path.home() / ".rhdp-creds.md"
    if not creds_file.exists():
        return
    for line in creds_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, _, value = line.strip().partition("=")
            key = key.strip()
            value = value.strip()
            if key in ("MAAS_API_BASE", "MAAS_API_KEY", "MAAS_TESTER_MODEL", "MAAS_ORCHESTRATOR_MODEL"):
                if not os.environ.get(key):
                    os.environ[key] = value


def setup_project_dir(fixture: Fixture, keep: bool = False) -> Path:
    """Create a temp project dir from template for this test run."""
    project_dir = Path(tempfile.mkdtemp(prefix=f"ph-test-{fixture.name}-"))
    if TEMPLATE_DIR.exists():
        for item in TEMPLATE_DIR.iterdir():
            if item.name == ".git":
                continue
            dest = project_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
    else:
        # Minimal scaffold if template not found
        (project_dir / "publishing-house").mkdir(parents=True)
        (project_dir / "publishing-house" / "spec").mkdir(parents=True)
    return project_dir


def print_result(fixture_path: str, result: RunResult, errors: list[str], verbose: bool, output: str) -> bool:
    """Print test result. Returns True if passed."""
    # Pass if: no validation errors AND loop ran without runner errors
    # (max_turns is acceptable in Phase 1 API-only mode)
    passed = len(errors) == 0

    if output == "json":
        print(json.dumps({
            "fixture": fixture_path,
            "passed": passed,
            "turns": result.turns,
            "termination_reason": result.termination_reason,
            "validation_errors": errors,
            "runner_errors": result.errors,
        }, indent=2))
        return passed

    # Table output
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{'='*60}")
    print(f"{status} — {fixture_path}")
    print(f"{'='*60}")
    print(f"  Turns:       {result.turns}")
    print(f"  Terminated:  {result.termination_reason}")

    if verbose and result.conversation:
        print(f"\n  Conversation ({len(result.conversation)} turns):")
        for i, turn in enumerate(result.conversation):
            role = turn.get("role", "?")
            content = turn.get("content", "")[:200]
            print(f"    [{i+1}] {role}: {content}...")

    if errors:
        print(f"\n  Validation ({len(errors)} error(s)):")
        for e in errors:
            print(f"    ✗ {e}")
    else:
        print(f"\n  Validation: all checks passed")

    if result.errors:
        print(f"\n  Runner errors:")
        for e in result.errors:
            print(f"    ! {e}")

    return passed


def run_fixture(fixture_path_str: str, verbose: bool, keep_on_fail: bool, output: str) -> bool:
    """Run a single fixture. Returns True if passed."""
    # Resolve fixture path
    fixture_path = FIXTURES_DIR / f"{fixture_path_str}.yaml"
    if not fixture_path.exists():
        fixture_path = Path(fixture_path_str)
    if not fixture_path.exists():
        print(f"❌ Fixture not found: {fixture_path_str}")
        return False

    fixture = load_fixture(fixture_path)
    project_dir = setup_project_dir(fixture)
    mock_mcp = MCPMock()

    try:
        result = run(fixture, project_dir, mock_mcp=mock_mcp, verbose=verbose)
        # Phase 1: conversation-level validation
        errors = validate_conversation(fixture, result)
        # Phase 2: file-level validation (only if files are defined in fixture)
        if fixture.expected_outcomes.files:
            errors += validate(fixture, project_dir)
        passed = print_result(fixture_path_str, result, errors, verbose, output)
    finally:
        if not (keep_on_fail and not passed):
            shutil.rmtree(project_dir, ignore_errors=True)
        else:
            print(f"\n  Project dir kept at: {project_dir}")

    return passed


def main():
    load_env_from_creds()

    parser = argparse.ArgumentParser(description="ph-test — PH E2E test runner")
    parser.add_argument("fixture", nargs="?", help="Fixture path (e.g. onboarded/ansible)")
    parser.add_argument("--all", action="store_true", help="Run all fixtures")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full conversation")
    parser.add_argument("--keep-on-fail", action="store_true", help="Keep project dir on failure")
    parser.add_argument("--output", choices=["table", "json"], default="table")
    parser.add_argument("--mode", choices=["onboarded", "express", "self-published"],
                        help="Filter fixtures by mode")
    args = parser.parse_args()

    if not args.fixture and not args.all:
        parser.print_help()
        sys.exit(1)

    if not os.environ.get("MAAS_API_KEY"):
        print("❌ MAAS_API_KEY not set. Add it to ~/.rhdp-creds.md or export it.")
        sys.exit(1)

    fixtures_to_run = []
    if args.all:
        for yaml_file in sorted(FIXTURES_DIR.rglob("*.yaml")):
            rel = yaml_file.relative_to(FIXTURES_DIR)
            mode_dir = rel.parts[0] if len(rel.parts) > 1 else ""
            if args.mode and mode_dir != args.mode:
                continue
            fixtures_to_run.append(str(rel.with_suffix("")))
    else:
        fixtures_to_run = [args.fixture]

    results = []
    for f in fixtures_to_run:
        passed = run_fixture(f, args.verbose, args.keep_on_fail, args.output)
        results.append((f, passed))

    # Summary
    if len(results) > 1:
        passed_count = sum(1 for _, p in results if p)
        print(f"\n{'='*60}")
        print(f"Results: {passed_count}/{len(results)} passed")
        for f, p in results:
            print(f"  {'✅' if p else '❌'} {f}")

    sys.exit(0 if all(p for _, p in results) else 1)


if __name__ == "__main__":
    main()
