"""FastAPI API server for BiteAI recommendations."""

import logging
import threading
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.data.store import initialize_store
from src.models.preferences import UserPreferences
from src.orchestration.recommender import RecommenderService

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Module-level store reference — populated by background thread
store = None
store_error = None


def _load_store_background():
    """Load the restaurant store in a background thread so the server can start immediately."""
    global store, store_error
    try:
        logger.info("Background store initialization starting...")
        store = initialize_store()
        logger.info("RestaurantStore initialized successfully: %d restaurants", store.count)
    except Exception as exc:
        logger.error("Failed to initialize RestaurantStore: %s", exc)
        store_error = str(exc)


# Start background loading immediately — server binds the port first, data loads in parallel
_init_thread = threading.Thread(target=_load_store_background, daemon=True)
_init_thread.start()


app = FastAPI(
    title="BiteAI Backend API",
    description="REST API for Zomato AI Recommendation Engine",
)

# CORS middleware — restrict origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://frontend-eta-steel-46.vercel.app",  # Vercel production
        "http://localhost:5173",              # Local Vite dev server
        "http://localhost:4173",              # Local Vite preview server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """Health check endpoint for Railway."""
    return {
        "status": "ok",
        "store_ready": store is not None,
        "store_error": store_error,
    }


@app.get("/api/filters")
def get_filters():
    """Extracts unique areas in Bangalore and unique cuisines from the dataset."""
    if store is None:
        if store_error:
            raise HTTPException(status_code=500, detail=f"Store initialization failed: {store_error}")
        raise HTTPException(status_code=503, detail="Database store is still loading (~30s on first boot). Please retry shortly.")

    try:
        all_restaurants = store.get_all()

        # Bangalore locations
        bangalore_areas = sorted(list({
            r.location for r in all_restaurants
            if r.city and r.city.lower() == "bangalore" and r.location
        }))

        # Unique cuisines
        cuisines_set = set()
        for r in all_restaurants:
            if r.cuisine:
                parts = [c.strip().title() for c in r.cuisine.split(",")]
                cuisines_set.update(parts)
        cuisines_list = sorted(list(cuisines_set))
        cuisines_list.insert(0, "Any")

        return {
            "status": "success",
            "locations": bangalore_areas,
            "cuisines": cuisines_list
        }
    except Exception as exc:
        logger.exception("Error loading filters: %s", exc)
        raise HTTPException(status_code=500, detail=f"Error loading filters: {exc}")


@app.post("/api/recommend")
def recommend(prefs: UserPreferences):
    """Orchestrates recommendation filtering and AI-powered ranking."""
    if store is None:
        if store_error:
            raise HTTPException(status_code=500, detail=f"Store initialization failed: {store_error}")
        raise HTTPException(status_code=503, detail="Database store is still loading (~30s on first boot). Please retry shortly.")

    try:
        service = RecommenderService(store=store)
        response = service.recommend(prefs)
        return response
    except Exception as exc:
        logger.exception("Error running recommendation: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
