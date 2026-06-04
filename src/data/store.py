"""In-memory restaurant store with optional pickle cache."""

from __future__ import annotations

import logging
import os
import pickle
import time
from pathlib import Path
from typing import List, Optional

from src.config import get_settings
from src.data.export import (
    export_restaurants_to_csv,
    export_restaurants_to_parquet,
    preview_csv_path,
    preview_parquet_path,
)
from src.data.loader import DatasetLoadError, load_raw_dataset
from src.data.preprocessor import PreprocessStats, preprocess_records
from src.models.restaurant import Restaurant

logger = logging.getLogger(__name__)

STORE_VERSION = 1


class StoreNotReadyError(Exception):
    """Raised when the store is accessed before initialization."""


class RestaurantStore:
    """Holds preprocessed restaurants for fast filtering at request time."""

    def __init__(self, restaurants: List[Restaurant], stats: Optional[PreprocessStats] = None):
        self._restaurants = list(restaurants)
        self._stats = stats
        self._cities = sorted({r.city for r in self._restaurants})

    @property
    def count(self) -> int:
        return len(self._restaurants)

    @property
    def stats(self) -> Optional[PreprocessStats]:
        return self._stats

    @property
    def cities(self) -> List[str]:
        return list(self._cities)

    def get_all(self) -> List[Restaurant]:
        return list(self._restaurants)

    def by_city(self, city: str) -> List[Restaurant]:
        settings = get_settings()
        normalized = settings.normalize_location(city)
        target = normalized.lower()
        return [r for r in self._restaurants if r.city.lower() == target]


_store: Optional[RestaurantStore] = None


def _cache_path() -> Path:
    settings = get_settings()
    path = Path(settings.data_cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_from_cache() -> Optional[RestaurantStore]:
    settings = get_settings()
    if not settings.use_data_cache:
        return None

    cache_file = _cache_path()
    if not cache_file.exists():
        return None

    try:
        with cache_file.open("rb") as fh:
            payload = pickle.load(fh)
        if payload.get("version") != STORE_VERSION:
            logger.info("Cache version mismatch; reloading from Hugging Face.")
            return None
        restaurants = payload["restaurants"]
        stats = payload.get("stats")
        logger.info("Loaded %d restaurants from cache: %s", len(restaurants), cache_file)
        store = RestaurantStore(restaurants, stats=stats)
        _ensure_preview_exports(store, cache_file)
        return store
    except Exception as exc:
        logger.warning("Corrupt cache at %s (%s); will reload.", cache_file, exc)
        try:
            cache_file.unlink(missing_ok=True)
        except OSError:
            pass
        return None


def _ensure_preview_exports(store: RestaurantStore, pkl_file: Path) -> None:
    """Regenerate CSV/Parquet previews if missing or older than the pickle cache."""
    restaurants = store.get_all()
    pkl_mtime = pkl_file.stat().st_mtime

    for path, exporter in (
        (preview_csv_path(), export_restaurants_to_csv),
        (preview_parquet_path(), export_restaurants_to_parquet),
    ):
        try:
            if path.exists() and path.stat().st_mtime >= pkl_mtime:
                continue
            exporter(restaurants, path)
        except Exception as exc:
            logger.warning("Could not refresh preview %s: %s", path.name, exc)


def _save_to_cache(store: RestaurantStore) -> None:
    settings = get_settings()
    if not settings.use_data_cache:
        return

    cache_file = _cache_path()
    payload = {
        "version": STORE_VERSION,
        "restaurants": store.get_all(),
        "stats": store.stats,
    }
    with cache_file.open("wb") as fh:
        pickle.dump(payload, fh, protocol=pickle.HIGHEST_PROTOCOL)
    logger.info("Saved restaurant cache to %s", cache_file)

    # CSV / Parquet previews (pickle is not human-readable in the editor)
    _ensure_preview_exports(store, cache_file)


def initialize_store(*, force_reload: bool = False) -> RestaurantStore:
    """
    Load and preprocess the dataset, populate the global store.

    Uses local pickle cache when enabled to avoid repeated HF downloads.
    """
    global _store

    if _store is not None and not force_reload:
        return _store

    if not force_reload:
        cached = _load_from_cache()
        if cached is not None:
            _store = cached
            return _store

    start = time.perf_counter()
    raw_records = load_raw_dataset()
    restaurants, stats = preprocess_records(raw_records)
    elapsed_ms = (time.perf_counter() - start) * 1000

    _store = RestaurantStore(restaurants, stats=stats)
    _save_to_cache(_store)

    logger.info(
        "Store initialized: restaurants=%d cities=%s duration_ms=%.0f",
        _store.count,
        _store.cities,
        elapsed_ms,
    )
    return _store


def get_store() -> RestaurantStore:
    """Return the initialized store, loading on first access."""
    global _store
    if _store is None:
        try:
            return initialize_store()
        except DatasetLoadError:
            raise
        except Exception as exc:
            raise StoreNotReadyError(
                "Restaurant store failed to initialize."
            ) from exc
    return _store


def reset_store() -> None:
    """Clear the in-memory store (mainly for tests)."""
    global _store
    _store = None
