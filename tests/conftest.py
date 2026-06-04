"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from src.data.store import reset_store


@pytest.fixture(autouse=True)
def _reset_global_store():
    reset_store()
    yield
    reset_store()
