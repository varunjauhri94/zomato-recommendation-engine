"""Export restaurant data to preview-friendly formats (CSV / JSON)."""

from __future__ import annotations

import csv
import json
import logging
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import get_settings
from src.models.restaurant import Restaurant

logger = logging.getLogger(__name__)

PREVIEW_COLUMNS = [
    "id",
    "name",
    "location",
    "city",
    "cuisine",
    "rating",
    "cost_for_two",
    "budget_band",
]


def restaurant_to_row(restaurant: Restaurant) -> Dict[str, Any]:
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "location": restaurant.location,
        "city": restaurant.city,
        "cuisine": restaurant.cuisine,
        "rating": restaurant.rating,
        "cost_for_two": restaurant.cost_for_two,
        "budget_band": restaurant.budget_band,
    }


def export_restaurants_to_csv(
    restaurants: List[Restaurant],
    csv_path: Path,
) -> Path:
    """Write restaurants to CSV for IDE table preview."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=PREVIEW_COLUMNS)
        writer.writeheader()
        for restaurant in restaurants:
            writer.writerow(restaurant_to_row(restaurant))
    logger.info("Exported %d rows to %s", len(restaurants), csv_path)
    return csv_path


def export_restaurants_to_json(
    restaurants: List[Restaurant],
    json_path: Path,
    *,
    limit: Optional[int] = None,
) -> Path:
    """Write restaurants to JSON (optional row limit for quick inspection)."""
    json_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [restaurant_to_row(r) for r in restaurants]
    if limit is not None:
        rows = rows[:limit]
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=2)
    logger.info("Exported %d rows to %s", len(rows), json_path)
    return json_path


def preview_csv_path() -> Path:
    settings = get_settings()
    pkl = Path(settings.data_cache_path)
    return pkl.with_suffix(".csv")


def preview_json_path() -> Path:
    settings = get_settings()
    pkl = Path(settings.data_cache_path)
    return pkl.with_name(pkl.stem + "_preview.json")


def preview_parquet_path() -> Path:
    settings = get_settings()
    pkl = Path(settings.data_cache_path)
    return pkl.with_suffix(".parquet")


def export_restaurants_to_parquet(
    restaurants: List[Restaurant],
    parquet_path: Path,
) -> Path:
    """Write restaurants to Parquet for efficient storage and data tools."""
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "Parquet export requires pandas. Run: pip install pandas pyarrow"
        ) from exc

    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [restaurant_to_row(r) for r in restaurants]
    df = pd.DataFrame(rows, columns=PREVIEW_COLUMNS)
    df.to_parquet(parquet_path, index=False, engine="pyarrow")
    logger.info("Exported %d rows to %s", len(restaurants), parquet_path)
    return parquet_path


def export_cache_preview(
    *,
    pkl_path: Optional[Path] = None,
    csv_path: Optional[Path] = None,
    json_sample: int = 100,
) -> Dict[str, Path]:
    """
    Export pickle cache to CSV, Parquet (full), and JSON (sample) for preview.

    Returns paths written.
    """
    pkl_path = pkl_path or Path(get_settings().data_cache_path)
    if not pkl_path.exists():
        raise FileNotFoundError(f"Cache not found: {pkl_path}")

    with pkl_path.open("rb") as fh:
        payload = pickle.load(fh)

    restaurants: List[Restaurant] = payload["restaurants"]
    out_csv = csv_path or preview_csv_path()
    out_parquet = preview_parquet_path()
    out_json = preview_json_path()

    export_restaurants_to_csv(restaurants, out_csv)
    export_restaurants_to_parquet(restaurants, out_parquet)
    export_restaurants_to_json(restaurants, out_json, limit=json_sample)

    return {"csv": out_csv, "parquet": out_parquet, "json": out_json, "pkl": pkl_path}


def main() -> None:
    """CLI: python -m src.data.export"""
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Export restaurants.pkl to CSV, Parquet, and JSON preview"
    )
    parser.add_argument(
        "--pkl",
        default=None,
        help="Path to restaurants.pkl (default: from config)",
    )
    parser.add_argument("--csv", default=None, help="Output CSV path")
    parser.add_argument("--json-sample", type=int, default=100, help="JSON preview row limit")
    args = parser.parse_args()

    pkl = Path(args.pkl) if args.pkl else None
    csv = Path(args.csv) if args.csv else None
    paths = export_cache_preview(pkl_path=pkl, csv_path=csv, json_sample=args.json_sample)
    print(
        "Preview ready:\n"
        f"  CSV:     {paths['csv']}\n"
        f"  Parquet: {paths['parquet']}\n"
        f"  JSON:    {paths['json']} (sample)"
    )


if __name__ == "__main__":
    main()
