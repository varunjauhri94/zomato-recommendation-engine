# AI-Powered Restaurant Recommendation System

Zomato-inspired restaurant recommendations combining structured data from Hugging Face with LLM-powered ranking and explanations.

## Documentation

| Document | Description |
|----------|-------------|
| [`context.md`](context.md) | Product context and goals |
| [`architecture.md`](architecture.md) | System design |
| [`implementation_plan.md`](implementation_plan.md) | Phase-wise build plan |
| [`edge-cases.md`](edge-cases.md) | Edge cases and error handling |

## Setup

### 1. Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env as needed (LLM keys are for Phase 3, not yet implemented)
```

Set `HF_HOME=.cache/huggingface` (default) to cache the dataset inside the project.

### 3. Verify installation

```bash
python -c "import src; from src.config import settings; print(settings.hf_dataset_id)"
```

## Phase 1: Data layer smoke test

Downloads the Zomato dataset on first run (~51k rows), preprocesses, and caches to `data/cache/restaurants.pkl`.

**Preview the data (table view):** Pickle files are binary and cannot be opened as a table in the editor. Open the auto-generated CSV instead:

```text
data/cache/restaurants.csv      # table preview in editor
data/cache/restaurants.parquet  # compact columnar format (pandas / DuckDB)
```

Regenerate previews from an existing `.pkl`:

```bash
python -m src.data.export
```

```bash
python -m src --city Bangalore
python -m src --reload   # force re-download from Hugging Face
```

## Phase 2: Filtering smoke test

```bash
python -m src --filter-only --city Bangalore --budget medium --cuisine Italian --min-rating 4.0
# Or run filter by default:
python -m src --city Bangalore --budget medium --cuisine Italian --min-rating 4.0
python -m src --data-only --city Bangalore   # Phase 1 data stats only
```

## Phase 5: CLI Presentation (AI-Powered)

Runs the complete pipeline (candidate filter -> LLM reasoning/ranking):

```bash
python -m src.ui.cli --location Bangalore --budget medium --cuisine Italian --min-rating 4.0 --additional "quiet place, outdoor seating"
```

## Phase 6: Web UI (React + FastAPI)

Launch the backend API server:

```bash
.venv/bin/python -m uvicorn src.ui.api:app --reload --port 8000
```

Launch the Vite React development server:

```bash
cd frontend
npm run dev
```

Open the local URL `http://localhost:5173` to test preference selections, view dynamic result cards, and see AI insights. The frontend automatically proxies `/api` requests to the FastAPI backend.

## Dataset notes

- **Source:** [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)
- **Columns used:** `name`, `address`, `location`, `cuisines`, `rate`, `approx_cost(for two people)`
- **City:** Extracted from `address`; rows without a city token default to **Bangalore** (dataset is ~96% Bangalore)
- **Rating:** Parsed from `4.1/5` format; `NEW`/missing kept as `null`
- **Dedup:** Dataset contains repeated rows; unique key is `(name, city, location)` (~12k unique venues)
- **Budget bands:** low ≤ ₹500, medium ≤ ₹1500, high > ₹1500 (configurable via `.env`)

## Project structure

```
src/
├── config.py           # Settings and budget thresholds
├── models/             # Restaurant, preferences, recommendation DTOs
├── data/               # Loader, preprocessor, store
├── filtering/          # Phase 2 candidate filter
├── llm/                # Phase 3 prompt builder, client, parser
├── orchestration/      # Phase 4 RecommenderService pipeline
└── ui/                 # Phase 5 CLI & Phase 6 FastAPI API Server
frontend/               # Phase 6 React Vite client application
tests/
```

## Run tests

```bash
pytest -v
```

Integration test against live Hugging Face (optional):

```bash
pytest -v -m integration
```

## Implementation status

- [x] Phase 0 — Project setup
- [x] Phase 1 — Data foundation
- [x] Phase 2 — Filtering & preferences
- [x] Phase 3 — LLM recommendation engine
- [x] Phase 4 — Orchestration pipeline
- [x] Phase 5 — CLI presentation
- [x] Phase 6 — Web UI (React + FastAPI) **(current)**
- [ ] Phase 7 — Hardening

