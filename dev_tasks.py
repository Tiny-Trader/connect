"""Local developer task entry points wired via Poetry scripts."""

from __future__ import annotations

import subprocess


def _run(cmd: list[str]) -> None:
    """Execute a command and exit with its return code."""
    raise SystemExit(subprocess.run(cmd, check=False).returncode)


def lint() -> None:
    """Run Ruff lint checks."""
    _run(["ruff", "check", "tt_connect"])


def typecheck() -> None:
    """Run MyPy strict type checks for the core package."""
    _run(["mypy", "tt_connect/"])


def test() -> None:
    """Run default pytest collection (unit + integration via config)."""
    _run(["pytest"])


def test_fast() -> None:
    """Run explicit fast suites used for local pre-push and CI checks."""
    _run(["pytest", "-q", "tests/unit", "tests/integration"])


def coverage() -> None:
    """Run coverage gate command used in CI."""
    _run([
        "pytest",
        "tests/unit",
        "--cov=tt_connect",
        "--cov-report=xml",
        "--cov-fail-under=85",
    ])


def precommit_install() -> None:
    """Install local pre-commit and pre-push hooks."""
    _run(["pre-commit", "install", "--hook-type", "pre-commit", "--hook-type", "pre-push"])


def precommit_run() -> None:
    """Run all configured pre-commit hooks on all files."""
    _run(["pre-commit", "run", "--all-files"])
