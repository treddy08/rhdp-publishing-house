"""
MCPMock — ph-test harness MCP interceptor.

Intercepts MCP tool calls during testing and returns fixture responses
defined in test/mocks/mcp_responses.yaml instead of hitting the real portal.

Usage::

    from src.ph_test.mcp_mock import MCPMock

    mock = MCPMock()
    result = mock("ph_rcars_query", {"query": "content overlap check"})
    # Returns the fixture dict, never calls the portal.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

# Default fixture file shipped alongside the test harness.
# Resolved relative to this source file so it is cwd-independent.
_DEFAULT_RESPONSES_PATH = (
    Path(__file__).parent.parent.parent / "test" / "mocks" / "mcp_responses.yaml"
)


class MCPMock:
    """Callable MCP interceptor that returns fixture responses by tool name.

    Parameters
    ----------
    responses_path:
        Path to the YAML fixture file.  When *None* the bundled
        ``test/mocks/mcp_responses.yaml`` is used.

    Raises
    ------
    FileNotFoundError
        If the YAML file does not exist.
    """

    def __init__(
        self,
        responses_path: str | Path | None = None,
    ) -> None:
        path = Path(responses_path) if responses_path is not None else _DEFAULT_RESPONSES_PATH

        if not path.exists():
            raise FileNotFoundError(
                f"MCP responses fixture not found: {path}"
            )

        with path.open("r", encoding="utf-8") as fh:
            loaded = yaml.safe_load(fh)

        if not isinstance(loaded, dict):
            raise ValueError(
                f"Expected a YAML mapping at the top level in {path}, got {type(loaded).__name__}"
            )

        self._responses: dict[str, Any] = loaded

    # ------------------------------------------------------------------
    # Callable interface
    # ------------------------------------------------------------------

    def __call__(self, tool_name: str, params: dict) -> dict:  # noqa: ARG002
        """Return a deep copy of the fixture response for *tool_name*.

        Parameters
        ----------
        tool_name:
            The MCP tool identifier (e.g. ``"ph_rcars_query"``).
        params:
            The params dict the orchestrator would send to the real portal.
            Ignored — the mock always returns the fixture regardless of params.

        Returns
        -------
        dict
            A fresh deep copy of the fixture response so callers cannot
            pollute the fixture store through mutation.

        Raises
        ------
        KeyError
            If *tool_name* is not present in the fixture file.  This is
            intentional — unknown MCP calls must fail loudly in tests so
            that missing fixtures are caught immediately rather than
            silently producing empty or ``None`` results.
        """
        if tool_name not in self._responses:
            raise KeyError(
                f"MCPMock: no fixture defined for tool '{tool_name}'. "
                f"Add it to test/mocks/mcp_responses.yaml."
            )

        return copy.deepcopy(self._responses[tool_name])
