"""FastAPI API server for BiteAI recommendations."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.data.store import initialize_store
from src.models.preferences import UserPreferences
from src.orchestration.recommender import RecommenderService

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Module-level store reference — populated during startup
store = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the restaurant store on startup (after port is bound)."""
    global store
    try:
        store = initialize_store()
        logger.info("RestaurantStore initialized successfully: %d restaurants", store.count)
    except Exception as exc:
        logger.error("Failed to initialize RestaurantStore: %s", exc)
        store = None
    yield


app = FastAPI(
    title="BiteAI Backend API",
    description="REST API for Zomato AI Recommendation Engine",
    lifespan=lifespan,
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
    return {"status": "ok", "store_ready": store is not None}


@app.get("/api/filters")
def get_filters():
    """Extracts unique areas in Bangalore and unique cuisines from the dataset."""
    if store is None:
        raise HTTPException(status_code=503, detail="Database store is still initializing. Please retry in a few seconds.")

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
        raise HTTPException(status_code=503, detail="Database store is still initializing. Please retry in a few seconds.")

    try:
        service = RecommenderService(store=store)
        response = service.recommend(prefs)
        # Pydantic models are serialized to JSON automatically by FastAPI
        return response
    except Exception as exc:
        logger.exception("Error running recommendation: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
