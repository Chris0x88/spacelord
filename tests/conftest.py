"""
Spacelord pytest configuration.

Convention
----------
- Files matching `test_*.py` are collected by pytest. They MUST be safe to run
  in CI: simulation mode, no real broadcasts, no real key material.
- Live-broadcast verifiers keep their `verify_*.py` / `live_test_*.py` prefix so
  pytest does NOT collect them. Run those manually as scripts when you need to
  exercise real on-chain flows.

This conftest provides two safety nets so test authors don't have to repeat
boilerplate in every file:

1. `pythonpath = ["."]` in `pyproject.toml` puts the project root on sys.path,
   so `from src.X import ...` works without manual sys.path mangling.
2. The `_force_simulation_mode` autouse fixture below forces SPACELORD_SIMULATE
   and SPACELORD_CONFIRM env vars before every test, so a test that forgets to
   set them still cannot accidentally trigger a live broadcast.
"""
from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _force_simulation_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force simulation + no-confirm for every collected test.

    Defense in depth: even if a `test_*.py` file forgets to set these, pytest
    still cannot trigger a live broadcast. To opt out (e.g. for a test that
    explicitly verifies non-sim behaviour with mocks), use
    `monkeypatch.delenv("SPACELORD_SIMULATE", raising=False)` inside the test.
    """
    monkeypatch.setenv("SPACELORD_SIMULATE", "true")
    monkeypatch.setenv("SPACELORD_CONFIRM", "false")
    # Clean any inherited operator credentials so a stray import that reads them
    # gets a deterministic empty value rather than the developer's real keys.
    for var in ("OPERATOR_KEY", "OPERATOR_ID", "OPERATOR_EVM_ADDRESS"):
        if var in os.environ:
            monkeypatch.delenv(var, raising=False)
