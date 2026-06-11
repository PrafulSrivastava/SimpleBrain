"""Smoke tests for the __main__ entry point."""
from __future__ import annotations
import subprocess
import sys


def test_help_exits_cleanly():
    """Running `python -m simplebrain --help` should exit with code 0."""
    result = subprocess.run(
        [sys.executable, "-m", "simplebrain", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"--help exited with code {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_help_mentions_flags():
    """--help output should document the main CLI flags."""
    result = subprocess.run(
        [sys.executable, "-m", "simplebrain", "--help"],
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    for flag in ("--setup", "--mcp", "--host", "--port"):
        assert flag in output, f"Expected '{flag}' in --help output"


def test_module_importable():
    """simplebrain package must be importable without side effects."""
    result = subprocess.run(
        [sys.executable, "-c", "import simplebrain; print('ok')"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"import simplebrain failed\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "ok" in result.stdout
