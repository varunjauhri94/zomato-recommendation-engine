"""CLI entrypoint for data layer and filtering (Phases 1–2)."""

from __future__ import annotations

import argparse
import logging
import os

from src.data.store import initialize_store
from src.filtering.candidate_filter import filter_restaurants
from src.models.preferences import Budget, UserPreferences

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Zomato recommendation — data & filter smoke test (Phase 2)"
    )
    parser.add_argument("--city", default="Bangalore", help="City / location filter")
    parser.add_argument("--budget", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--cuisine", default="Italian", help="Cuisine filter (or 'any')")
    parser.add_argument("--min-rating", type=float, default=4.0, dest="min_rating")
    parser.add_argument("--reload", action="store_true", help="Force reload from Hugging Face")
    parser.add_argument(
        "--filter-only",
        action="store_true",
        help="Run filter demo (default when any filter args are used)",
    )
    parser.add_argument(
        "--data-only",
        action="store_true",
        help="Phase 1: show data stats and sample rows only",
    )
    args = parser.parse_args()

    if not os.environ.get("HF_HOME"):
        os.environ.setdefault("HF_HOME", os.path.join(os.getcwd(), ".cache", "huggingface"))

    store = initialize_store(force_reload=args.reload)

    # Default to filter demo unless --data-only
    run_filter = args.filter_only or not args.data_only

    if run_filter and not args.data_only:
        prefs = UserPreferences(
            location=args.city,
            budget=Budget(args.budget),
            cuisine=args.cuisine,
            min_rating=args.min_rating,
        )
        result = filter_restaurants(store.get_all(), prefs)
        print(
            f"Filter: {prefs.normalized_location} | {prefs.budget.value} | "
            f"{prefs.cuisine} | min_rating={prefs.min_rating}"
        )
        print(f"Candidates: {len(result.candidates)}")
        if result.message:
            print(f"Message: {result.message}")
        print(
            f"Metadata: after_budget={result.metadata.get('after_budget')} "
            f"top_n={result.metadata.get('top_n')}"
        )
        for r in result.candidates[:10]:
            cost = f"₹{r.cost_for_two}" if r.cost_for_two else "N/A"
            rating = f"{r.rating}" if r.rating is not None else "N/A"
            print(f"  - {r.name} | {r.cuisine} | ★{rating} | {cost} | {r.budget_band}")
        return

    sample = store.by_city(args.city)
    print(f"Total restaurants: {store.count}")
    print(f"Cities available: {', '.join(store.cities)}")
    if store.stats:
        s = store.stats
        print(
            f"Preprocess: input={s.input_rows} normalized={s.rows_normalized} "
            f"unique={s.output_rows} success_rate={s.success_rate:.1%} "
            f"collapsed_duplicates={s.collapsed_duplicates}"
        )
    print(f"Restaurants in {args.city}: {len(sample)}")
    for r in sample[:5]:
        cost = f"₹{r.cost_for_two}" if r.cost_for_two else "N/A"
        rating = f"{r.rating}" if r.rating is not None else "N/A"
        print(f"  - {r.name} | {r.cuisine} | ★{rating} | {cost} | {r.budget_band}")


if __name__ == "__main__":
    main()
