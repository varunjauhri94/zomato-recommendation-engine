"""Integration tests against live Hugging Face dataset (optional, slow)."""

from __future__ import annotations

import os

import pytest

from src.data.store import initialize_store, reset_store

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION") != "1",
    reason="Set RUN_INTEGRATION=1 to run live Hugging Face tests",
)
def test_load_full_dataset():
    reset_store()
    os.environ.setdefault("HF_HOME", os.path.join(os.getcwd(), ".cache", "huggingface"))
    store = initialize_store(force_reload=True)
    assert store.count > 10_000
    assert "Bangalore" in store.cities
    bangalore = store.by_city("Bangalore")
    assert len(bangalore) > 10_000
    assert store.stats is not None
    assert store.stats.success_rate >= 0.9
