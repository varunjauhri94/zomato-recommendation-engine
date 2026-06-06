"""Load raw Zomato records from Hugging Face."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

from src.config import get_settings

logger = logging.getLogger(__name__)


class DatasetLoadError(Exception):
    """Raised when the Hugging Face dataset cannot be loaded."""


def _ensure_hf_cache() -> None:
    settings = get_settings()
    if settings.hf_home:
        os.environ["HF_HOME"] = settings.hf_home
    elif not os.environ.get("HF_HOME"):
        # On Railway/PaaS, project dir is read-only; use /tmp
        if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("PORT"):
            os.environ["HF_HOME"] = "/tmp/hf_cache"
        else:
            # Default to project-local cache for local development
            project_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..")
            )
            os.environ["HF_HOME"] = os.path.join(project_root, ".cache", "huggingface")


def load_raw_dataset(*, max_retries: int = 3) -> List[Dict[str, Any]]:
    """
    Fetch the Zomato dataset from Hugging Face.

    Returns:
        List of raw row dicts from the train split.

    Raises:
        DatasetLoadError: On network failure, empty dataset, or schema issues.
    """
    _ensure_hf_cache()
    settings = get_settings()

    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise DatasetLoadError(
            "The 'datasets' package is required. Run: pip install -r requirements.txt"
        ) from exc

    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "Loading dataset %s (attempt %d/%d)",
                settings.hf_dataset_id,
                attempt,
                max_retries,
            )
            start = time.perf_counter()
            dataset = load_dataset(settings.hf_dataset_id, split="train")
            elapsed_ms = (time.perf_counter() - start) * 1000

            if len(dataset) == 0:
                raise DatasetLoadError("Dataset returned zero rows.")

            records = [dict(row) for row in dataset]
            logger.info(
                "Dataset loaded: row_count=%d duration_ms=%.0f",
                len(records),
                elapsed_ms,
            )
            return records

        except DatasetLoadError:
            raise
        except Exception as exc:
            last_error = exc
            logger.warning("Dataset load attempt %d failed: %s", attempt, exc)
            if attempt < max_retries:
                time.sleep(2**attempt)

    raise DatasetLoadError(
        f"Unable to load dataset '{settings.hf_dataset_id}'. "
        "Check your internet connection and try again."
    ) from last_error
