"""
Pytest configuration and shared fixtures.
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_midi_path(temp_dir: Path) -> Path:
    """Path for a temporary MIDI file."""
    return temp_dir / "test.mid"
