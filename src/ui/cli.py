"""CLI Presentation Layer for restaurant recommendations (Phase 5)."""

from __future__ import annotations

import argparse
import sys
import os
import logging
from pydantic import ValidationError

from src.config import get_settings
from src.data.store import initialize_store, DatasetLoadError, StoreNotReadyError
from src.models.preferences import Budget, UserPreferences
from src.orchestration.recommender import RecommenderService


def setup_logging():
    # Only show INFO/WARNING logs in the CLI unless DEBUG is desired.
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI-Powered Zomato Restaurant Recommendation System"
    )
    parser.add_argument(
        "--location",
        required=True,
        help="City or area (e.g., Bangalore, Delhi, Mumbai)",
    )
    parser.add_argument(
        "--budget",
        required=True,
        choices=["low", "medium", "high"],
        help="Budget category (low, medium, high)",
    )
    parser.add_argument(
        "--cuisine",
        required=True,
        help="Cuisine style (e.g., Italian, Chinese, North Indian, or 'any')",
    )
    parser.add_argument(
        "--min-rating",
        type=float,
        default=0.0,
        help="Minimum restaurant rating (0.0 to 5.0)",
    )
    parser.add_argument(
        "--additional",
        default=None,
        help="Additional free-text preferences (e.g., 'family-friendly', 'outdoor seating')",
    )
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()

    # Configure HF_HOME if not already present
    if not os.environ.get("HF_HOME"):
        os.environ.setdefault("HF_HOME", os.path.join(os.getcwd(), ".cache", "huggingface"))

    # 1. Validate input and construct UserPreferences
    try:
        prefs = UserPreferences(
            location=args.location,
            budget=Budget(args.budget),
            cuisine=args.cuisine,
            min_rating=args.min_rating,
            additional_preferences=args.additional,
        )
    except ValidationError as exc:
        print("\nInput Validation Error:", file=sys.stderr)
        for error in exc.errors():
            loc = " -> ".join(str(l) for l in error["loc"])
            print(f"  * {loc}: {error['msg']}", file=sys.stderr)
        sys.exit(2)
    except ValueError as exc:
        print(f"\nInput Error: {exc}", file=sys.stderr)
        sys.exit(2)

    # 2. Load data store (Startup Phase)
    print("Initializing restaurant database...", end="", flush=True)
    try:
        store = initialize_store()
        print(" [Ready]")
    except (DatasetLoadError, StoreNotReadyError, Exception) as exc:
        print(" [Failed]")
        print(f"Error: Unable to load restaurant data. Check your internet connection and try again.", file=sys.stderr)
        print(f"Details: {exc}", file=sys.stderr)
        sys.exit(1)

    # 3. Call Recommender Service
    print("Consulting AI recommendation engine... (this may take a few seconds)")
    service = RecommenderService(store=store)
    response = service.recommend(prefs)

    # 4. Handle Outcomes
    if response.status == "empty":
        print("\n" + "=" * 50)
        print("NO RECOMMENDATIONS FOUND")
        print("=" * 50)
        print(response.message or "No restaurants matched your criteria.")
        print("-" * 50)
        print("Suggestions:")
        print("  1. Try a different location (Bangalore has the most coverage).")
        print("  2. Lower your minimum rating threshold.")
        print("  3. Relax your budget constraint.")
        sys.exit(0)

    elif response.status == "error":
        print("\n" * 2 + "!" * 50)
        print("RECOMMENDATION FAILURE")
        print("!" * 50)
        print(f"Error: {response.message}", file=sys.stderr)
        sys.exit(1)

    # Success (or partial success)
    print("\n" + "=" * 60)
    print("AI-POWERED DINING RECOMMENDATIONS")
    print("=" * 60)
    
    if response.summary:
        print(f"\nSummary:\n{response.summary}\n")
        print("-" * 60)

    for rec in response.recommendations:
        rest = rec.restaurant
        cost_str = f"₹{rest.cost_for_two}" if rest.cost_for_two else "Price not available"
        rating_str = f"★ {rest.rating:.1f}" if rest.rating is not None else "—"
        
        print(f"\n#{rec.rank} {rest.name} ({rating_str})")
        print(f"   Cuisine: {rest.cuisine}")
        print(f"   Location: {rest.location}, {rest.city}")
        print(f"   Estimated Cost: {cost_str} for two")
        print(f"\n   AI Insight: {rec.explanation}")
        print("-" * 60)

    if response.warnings:
        print("\nWarnings:")
        for warning in response.warnings:
            print(f"  * {warning}")

    sys.exit(0)


if __name__ == "__main__":
    main()
