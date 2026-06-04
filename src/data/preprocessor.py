"""Normalize raw Zomato rows into canonical Restaurant entities."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.config import get_settings
from src.models.restaurant import Restaurant

logger = logging.getLogger(__name__)

# Dataset column mapping (ManikaSaini/zomato-restaurant-recommendation)
COL_NAME = "name"
COL_ADDRESS = "address"
COL_LOCATION = "location"
COL_CUISINES = "cuisines"
COL_RATE = "rate"
COL_COST = "approx_cost(for two people)"

KNOWN_CITIES = [
    "New Delhi",
    "Bangalore",
    "Bengaluru",
    "Mumbai",
    "Hyderabad",
    "Chennai",
    "Kolkata",
    "Pune",
    "Gurgaon",
    "Gurugram",
    "Noida",
]

# This dataset is predominantly Bangalore; rows without a city token still belong there.
DEFAULT_CITY = "Bangalore"


@dataclass
class PreprocessStats:
    input_rows: int = 0
    output_rows: int = 0
    rows_normalized: int = 0
    dropped_missing_name: int = 0
    collapsed_duplicates: int = 0
    defaulted_city: int = 0

    @property
    def dropped_total(self) -> int:
        return self.dropped_missing_name

    @property
    def success_rate(self) -> float:
        """Share of input rows that normalized successfully (before dedupe)."""
        if self.input_rows == 0:
            return 0.0
        return self.rows_normalized / self.input_rows


def parse_rating(value: Any) -> Optional[float]:
    """Parse rating from values like '4.1/5', 'NEW', None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in {"NEW", "-", "NAN", "NONE"}:
        return None

    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None

    rating = float(match.group(1))
    if rating < 0 or rating > 5:
        if rating > 5 and rating <= 10:
            rating = rating / 2  # handle rare x/10 style
        else:
            return None
    return round(rating, 2)


def parse_cost(value: Any) -> Optional[int]:
    """Parse cost for two from strings like '800', '1,200'."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in {"-", "NONE"}:
        return None
    digits = re.sub(r"[^\d]", "", text)
    if not digits:
        return None
    cost = int(digits)
    if cost < 0 or cost > 100_000:
        return None
    return cost


def extract_city_from_address(address: str) -> Optional[str]:
    """Extract canonical city name from full address string."""
    if not address:
        return None
    address_lower = address.lower()
    settings = get_settings()

    for city in sorted(KNOWN_CITIES, key=len, reverse=True):
        if city.lower() in address_lower:
            normalized = settings.normalize_location(city)
            if city.lower() in ("bengaluru",):
                return "Bangalore"
            return normalized

    return None


def normalize_cuisine(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    return text


def _stable_id(name: str, city: str, location: str, index: int) -> str:
    key = f"{name}|{city}|{location}|{index}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def preprocess_row(row: Dict[str, Any], index: int, stats: PreprocessStats) -> Optional[Restaurant]:
    settings = get_settings()

    name = (row.get(COL_NAME) or "").strip()
    if not name:
        stats.dropped_missing_name += 1
        return None

    address = (row.get(COL_ADDRESS) or "").strip()
    neighborhood = (row.get(COL_LOCATION) or "").strip()
    city = extract_city_from_address(address)
    if not city:
        city = DEFAULT_CITY
        stats.defaulted_city += 1

    cuisine = normalize_cuisine(row.get(COL_CUISINES)) or "unknown"

    rating = parse_rating(row.get(COL_RATE))
    # Keep rows without a parseable rating (e.g. "NEW"); min_rating filter handles them later.

    cost = parse_cost(row.get(COL_COST))
    budget_band = settings.cost_to_budget_band(cost)

    location = neighborhood or city
    restaurant_id = _stable_id(name, city, location, index)

    return Restaurant(
        id=restaurant_id,
        name=name,
        location=location,
        city=city,
        cuisine=cuisine,
        rating=rating,
        cost_for_two=cost,
        budget_band=budget_band,
        raw=row,
    )


def preprocess_records(
    records: Iterable[Dict[str, Any]],
) -> Tuple[List[Restaurant], PreprocessStats]:
    """
    Convert raw dataset rows to Restaurant entities.

    Drops invalid rows and deduplicates by (name, city).
    Keeps the highest-rated duplicate.
    """
    stats = PreprocessStats()
    best_by_key: Dict[Tuple[str, str], Restaurant] = {}

    for index, row in enumerate(records):
        stats.input_rows += 1
        restaurant = preprocess_row(row, index, stats)
        if restaurant is None:
            continue

        stats.rows_normalized += 1
        dedupe_key = (
            restaurant.name.lower(),
            restaurant.city.lower(),
            restaurant.location.lower(),
        )
        existing = best_by_key.get(dedupe_key)
        if existing is None:
            best_by_key[dedupe_key] = restaurant
        else:
            stats.collapsed_duplicates += 1
            if (restaurant.rating or 0) > (existing.rating or 0):
                best_by_key[dedupe_key] = restaurant

    restaurants = list(best_by_key.values())
    stats.output_rows = len(restaurants)

    if stats.input_rows > 0 and stats.success_rate < 0.9:
        logger.warning(
            "Preprocess success rate %.1f%% (<90%% normalized). dropped_name=%d",
            stats.success_rate * 100,
            stats.dropped_missing_name,
        )

    if not restaurants:
        raise ValueError("No valid restaurants after preprocessing.")

    logger.info(
        "Preprocess complete: input=%d normalized=%d unique=%d "
        "collapsed_duplicates=%d defaulted_city=%d",
        stats.input_rows,
        stats.rows_normalized,
        stats.output_rows,
        stats.collapsed_duplicates,
        stats.defaulted_city,
    )
    return restaurants, stats
