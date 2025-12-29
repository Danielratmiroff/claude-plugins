"""
Pytest configuration and fixtures for claude-dotfiles test suite.

This file provides shared fixtures and configuration for all tests.
"""

import os
import sys
from pathlib import Path

import pytest

# Add the project root to Python path for imports
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def plugins_dir(project_root):
    """Return the plugins directory."""
    return project_root / "plugins"


@pytest.fixture
def temp_workdir(tmp_path):
    """Create a temporary working directory and change to it."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)


# ==============================================================================
# Pytest hooks for auto-marking tests
# ==============================================================================


def pytest_collection_modifyitems(config, items):
    """
    Automatically add markers to tests based on their location.
    This allows running tests by plugin with -m marker.
    """
    for item in items:
        # Get the file path relative to project root
        try:
            rel_path = Path(item.fspath).relative_to(PROJECT_ROOT)
        except (ValueError, TypeError):
            continue

        parts = rel_path.parts

        # Auto-mark based on directory structure
        # Tests are in tests/ directory: tests/bash-safety/, tests/notifications/, etc.
        path_str = str(rel_path)
        if "bash-safety" in parts or "bash_safety" in path_str:
            item.add_marker(pytest.mark.bash_safety)
        elif "notifications" in parts:
            item.add_marker(pytest.mark.notifications)
        elif "test-runner" in parts or "test_runner" in path_str:
            item.add_marker(pytest.mark.test_runner)
        elif "observability" in parts:
            item.add_marker(pytest.mark.observability)


# ==============================================================================
# Test result formatting
# ==============================================================================


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Register custom markers
    config.addinivalue_line(
        "markers", "bash_safety: tests for bash-safety plugin"
    )
    config.addinivalue_line(
        "markers", "notifications: tests for notifications plugin"
    )
    config.addinivalue_line(
        "markers", "test_runner: tests for test-runner plugin"
    )
    config.addinivalue_line(
        "markers", "observability: tests for observability module"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow"
    )
    config.addinivalue_line(
        "markers", "integration: integration tests"
    )
