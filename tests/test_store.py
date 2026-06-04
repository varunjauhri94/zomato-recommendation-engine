"""Unit tests for restaurant store (offline, no Hugging Face)."""

from __future__ import annotations

from src.data.preprocessor import preprocess_records
from src.data.store import RestaurantStore, get_store, initialize_store, reset_store
from src.models.restaurant import Restaurant


SAMPLE_ROWS = [
    {
        "name": "Alpha",
        "address": "Indiranagar, Bangalore",
        "location": "Indiranagar",
        "cuisines": "Italian",
        "rate": "4.5/5",
        "approx_cost(for two people)": "900",
    },
    {
        "name": "Beta",
        "address": "Connaught Place, New Delhi",
        "location": "CP",
        "cuisines": "Chinese",
        "rate": "4.0/5",
        "approx_cost(for two people)": "400",
    },
]


def test_store_by_city():
    restaurants, _ = preprocess_records(SAMPLE_ROWS)
    store = RestaurantStore(restaurants)
    assert store.by_city("Bangalore")[0].name == "Alpha"
    assert store.by_city("bengaluru")[0].name == "Alpha"
    assert len(store.by_city("Delhi")) == 1


def test_get_store_uses_manual_init(monkeypatch):
    reset_store()
    restaurants, _ = preprocess_records(SAMPLE_ROWS)
    store = RestaurantStore(restaurants)

    def fake_initialize(*, force_reload=False):
        return store

    monkeypatch.setattr("src.data.store.initialize_store", fake_initialize)
    assert get_store().count == 2
