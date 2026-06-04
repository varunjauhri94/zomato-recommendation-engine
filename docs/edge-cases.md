# Edge Cases & Exception Handling Guide

Comprehensive catalog of edge cases for the AI-powered restaurant recommendation system. Use this document during implementation and QA alongside [`context.md`](context.md), [`architecture.md`](architecture.md), and [`implementation_plan.md`](implementation_plan.md).

Each entry includes: **scenario**, **expected behavior**, **handler** (module), **user message** (if applicable), and **priority**.

**Priority legend:** `P0` = must handle for MVP · `P1` = should handle · `P2` = nice to have / post-MVP

---

## Table of Contents

1. [Data Ingestion & Dataset](#1-data-ingestion--dataset)
2. [Preprocessing & Normalization](#2-preprocessing--normalization)
3. [Restaurant Store](#3-restaurant-store)
4. [User Input & Validation](#4-user-input--validation)
5. [Candidate Filtering](#5-candidate-filtering)
6. [Prompt Builder](#6-prompt-builder)
7. [LLM Client & API](#7-llm-client--api)
8. [Response Parser](#8-response-parser)
9. [Orchestration](#9-orchestration)
10. [Presentation Layer (CLI & Web)](#10-presentation-layer-cli--web)
11. [Configuration & Environment](#11-configuration--environment)
12. [Security & Abuse](#12-security--abuse)
13. [Performance & Concurrency](#13-performance--concurrency)
14. [Master Handling Matrix](#14-master-handling-matrix)
15. [Test Case Index](#15-test-case-index)

---

## 1. Data Ingestion & Dataset

| ID | Scenario | Expected behavior | Handler | User message | Priority |
|----|----------|-------------------|---------|--------------|----------|
| D-01 | Hugging Face download fails (network offline) | Fail at startup with clear error; do not start app in partial state | `data/loader.py` | "Unable to load restaurant data. Check your internet connection and try again." | P0 |
| D-02 | Dataset URI changed or dataset removed | Same as D-01; log dataset ID and HTTP status | `loader.py` | "Restaurant dataset is unavailable." | P0 |
| D-03 | Hugging Face rate limit / timeout | Retry 3× with exponential backoff; then fail startup | `loader.py` | "Data service is busy. Please try again in a few minutes." | P1 |
| D-04 | Dataset schema changed (column renamed/missing) | Log missing columns; map known aliases; fail if required fields absent | `loader.py`, `preprocessor.py` | "Restaurant data format has changed. Contact support." | P0 |
| D-05 | Empty dataset returned (0 rows) | Fail startup; never run with empty store | `loader.py`, `store.py` | "No restaurant data available." | P0 |
| D-06 | Corrupt / partial download | Detect on load (row count sanity check); re-download or fail | `loader.py` | "Restaurant data failed validation." | P1 |
| D-07 | Disk full when caching HF artifacts | Warn; attempt in-memory only; log cache path | `loader.py` | (dev-only log) | P2 |
| D-08 | First run on machine without HF cache | Longer startup; show loading indicator in UI | `store.py`, UI | "Loading restaurant data (first time may take a minute)…" | P1 |

---

## 2. Preprocessing & Normalization

| ID | Scenario | Expected behavior | Handler | User message | Priority |
|----|----------|-------------------|---------|--------------|----------|
| P-01 | `rating` is null, empty, or non-numeric | Drop row; increment `dropped_invalid_rating` counter | `preprocessor.py` | (none — silent drop) | P0 |
| P-02 | `rating` out of range (< 0 or > 5) | Clamp to [0, 5] or drop if clearly invalid (e.g. 99) | `preprocessor.py` | (none) | P0 |
| P-03 | `rating` is string like `"4.5/5"` or `"New"` | Parse numeric portion; drop if unparseable | `preprocessor.py` | (none) | P1 |
| P-04 | `cost_for_two` missing or zero | Set `budget_band` to `low` or `unknown`; keep row if other fields valid | `preprocessor.py` | (none) | P1 |
| P-05 | `cost_for_two` negative or absurdly high | Drop row or cap; log warning | `preprocessor.py` | (none) | P1 |
| P-06 | `name` missing or whitespace-only | Drop row | `preprocessor.py` | (none) | P0 |
| P-07 | `location` / city missing | Drop row (cannot filter by location) | `preprocessor.py` | (none) | P0 |
| P-08 | Location aliases ("New Delhi", "Bengaluru") | Normalize via `config` alias map → canonical city | `preprocessor.py`, `config.py` | (none) | P0 |
| P-09 | Unknown location string in data | Store as-is; may not match user filter later | `preprocessor.py` | (none) | P1 |
| P-10 | `cuisine` is multi-value ("Italian, Pizza, Fast Food") | Lowercase; keep full string for `contains` filter | `preprocessor.py` | (none) | P0 |
| P-11 | `cuisine` missing | Set to `"Unknown"` or drop row (product choice: drop for MVP) | `preprocessor.py` | (none) | P1 |
| P-12 | Duplicate rows (same name + city) | Keep highest-rated row; drop others | `preprocessor.py` | (none) | P1 |
| P-13 | Duplicate `id` after hash generation | Append suffix or use index to ensure uniqueness | `preprocessor.py` | (none) | P0 |
| P-14 | Special characters in name (emoji, unicode) | Preserve UTF-8; sanitize only for logs | `preprocessor.py` | (none) | P2 |
| P-15 | > 30% rows dropped during preprocess | Log WARN at startup; continue if ≥ 1 row remains | `preprocessor.py`, `store.py` | (none) | P1 |
| P-16 | Budget band boundary (exactly 500, 1500) | Inclusive/exclusive rules defined in config; document in tests | `config.py` | (none) | P0 |

---

## 3. Restaurant Store

| ID | Scenario | Expected behavior | Handler | User message | Priority |
|----|----------|-------------------|---------|--------------|----------|
| S-01 | Store accessed before initialization | Raise `StoreNotReadyError` or lazy-init once | `data/store.py` | "Application is still starting. Please wait." | P0 |
| S-02 | Pickle cache exists but schema version mismatch | Ignore cache; reload from HF | `store.py` | (none) | P1 |
| S-03 | Pickle cache corrupted | Delete cache file; reload | `store.py` | (none) | P1 |
| S-04 | `get_all()` on very large dataset | Return list reference; filter must not mutate store | `store.py`, `filtering/` | (none) | P1 |
| S-05 | Concurrent reads during reload (future) | Read-only snapshot or lock | `store.py` | P2 |
| S-06 | Single city dominates dataset | Filtering still works; no special case needed | `filtering/` | (none) | P2 |

---

## 4. User Input & Validation

| ID | Scenario | Expected behavior | Handler | User message | Priority |
|----|----------|-------------------|---------|--------------|----------|
| U-01 | `location` empty or whitespace | Reject before pipeline; validation error | `models/preferences.py`, UI | "Please enter a location." | P0 |
| U-02 | `location` not in dataset (unknown city) | Allow submit; filter returns empty → empty state (U-10) | `filtering/`, UI | "No restaurants found in '{location}'. Try Delhi, Bangalore, etc." | P0 |
| U-03 | `location` different casing ("bangalore", "BANGALORE") | Case-insensitive match against normalized cities | `filtering/`, `preprocessor` | (none) | P0 |
| U-04 | `location` with extra spaces / typos ("Banglore") | Exact match fails; optional fuzzy suggest (P2) | `filtering/` | "Did you mean Bangalore?" (P2) | P1 |
| U-05 | `budget` invalid enum ("cheap", "mid") | Reject; show allowed values | `preferences.py`, CLI | "Budget must be: low, medium, or high." | P0 |
| U-06 | `budget` not provided | Default to `medium` or require field (document choice) | `preferences.py` | "Please select a budget." | P0 |
| U-07 | `cuisine` empty | Reject or treat as "any" (MVP: reject) | `preferences.py` | "Please enter a cuisine type." | P0 |
| U-08 | `cuisine` partial match ("Ital" for Italian) | `contains` match on normalized cuisine string | `filtering/` | (none) | P1 |
| U-09 | `cuisine` with special regex chars (`.`, `*`) | Literal substring match, not regex | `filtering/` | (none) | P1 |
| U-10 | `min_rating` not a number | Reject validation | `preferences.py`, CLI | "Minimum rating must be a number between 0 and 5." | P0 |
| U-11 | `min_rating` < 0 or > 5 | Clamp to [0, 5] or reject (MVP: reject) | `preferences.py` | "Minimum rating must be between 0 and 5." | P0 |
| U-12 | `min_rating` = 5.0 (very strict) | Valid; likely empty filter result | `filtering/` | Empty state message | P0 |
| U-13 | `min_rating` = 0 | Valid; no rating filter effect | `filtering/` | (none) | P1 |
| U-14 | `additional_preferences` empty | Omit from LLM prompt section | `prompt_builder.py` | (none) | P0 |
| U-15 | `additional_preferences` very long (> 500 chars) | Truncate to max length; log WARN | `prompt_builder.py` | (none) | P1 |
| U-16 | `additional_preferences` only whitespace | Treat as empty | `preferences.py` | (none) | P1 |
| U-17 | All fields valid but contradictory (high rating + low budget in sparse data) | Empty filter; no LLM call | `orchestration/` | "No restaurants match your criteria. Try lowering minimum rating or changing budget." | P0 |
| U-18 | Unicode / emoji in user text fields | Accept UTF-8; pass to LLM after truncation | `preferences.py` | (none) | P2 |

---

## 5. Candidate Filtering

| ID | Scenario | Expected behavior | Handler | User message | Priority |
|----|----------|-------------------|---------|--------------|----------|
| F-01 | Zero restaurants match all filters | Return `[]`; orchestrator skips LLM | `filtering/candidate_filter.py` | "No restaurants found. Try a different location or lower your minimum rating." | P0 |
| F-02 | Exactly one match | Pass single candidate to LLM; return 1 recommendation | `filtering/`, `parser` | (none) | P0 |
| F-03 | Matches > `TOP_N` (e.g. 200) | Take top `TOP_N` by rating descending | `candidate_filter.py` | (none) | P0 |
| F-04 | Matches == `TOP_N` | Pass all | `candidate_filter.py` | (none) | P1 |
| F-05 | Location matches but cuisine does not (and vice versa) | Empty after full filter chain | `candidate_filter.py` | Same as F-01 | P0 |
| F-06 | Budget filter eliminates all (cost data sparse) | Empty result; suggest relaxing budget in message | `candidate_filter.py` | "No restaurants in your budget range. Try a different budget level." | P1 |
| F-07 | `budget_band` is `unknown` on restaurant | Exclude from budget-filtered results OR include in all bands (document in config) | `config.py`, `filtering/` | (none) | P1 |
| F-08 | Cuisine filter too strict ("Italian" vs "Italian, Continental") | Use case-insensitive substring match | `candidate_filter.py` | (none) | P0 |
| F-09 | Filter with null store / empty store | Return `[]`; log error | `candidate_filter.py` | "Restaurant data is not loaded." | P0 |
| F-10 | `top_n` config is 0 or negative | Use default `TOP_N` from config; log WARN | `config.py` | (none) | P1 |
| F-11 | All candidates have identical rating | Stable sort by name or id as tiebreaker | `candidate_filter.py` | (none) | P1 |
| F-12 | User cuisine "Any" or "*" (if supported) | Skip cuisine filter | `candidate_filter.py` | (none) | P2 |

---

## 6. Prompt Builder

| ID | Scenario | Expected behavior | Handler | User message | Priority |
|----|----------|-------------------|---------|--------------|----------|
| PR-01 | Empty candidate list passed to builder | Do not call; orchestrator should guard | `orchestration/` | (see F-01) | P0 |
| PR-02 | Single candidate | Prompt asks for top 1; adjust `top_k` to `min(top_k, len(candidates))` | `prompt_builder.py` | (none) | P0 |
| PR-03 | `top_k` > candidate count | Set `top_k = len(candidates)` in prompt | `prompt_builder.py` | (none) | P0 |
| PR-04 | Candidate list exceeds token budget | Already capped by `TOP_N`; if still too large, trim lowest-rated candidates | `prompt_builder.py` | (none) | P1 |
| PR-05 | Restaurant name with quotes/newlines breaks JSON | JSON-escape all string fields in payload | `prompt_builder.py` | (none) | P0 |
| PR-06 | Missing optional `additional_preferences` | Omit key from preferences JSON in prompt | `prompt_builder.py` | (none) | P0 |
| PR-07 | Prompt injection in `additional_preferences` | System prompt: ignore override instructions; sanitize length | `prompt_builder.py` | (none) | P0 |
| PR-08 | Very long restaurant names in candidates | Truncate name in prompt only (keep full in store) | `prompt_builder.py` | (none) | P2 |

---

## 7. LLM Client & API

| ID | Scenario | Expected behavior | Handler | User message | Priority |
|----|----------|-------------------|---------|--------------|----------|
| L-01 | `GROQ_API_KEY` missing or empty | Fail at client init or first call with clear error | `llm/client.py`, `config.py` | "LLM API key is not configured. Set GROQ_API_KEY in .env." | P0 |
| L-02 | Invalid / revoked API key | No retry; surface auth error | `client.py` | "Invalid API configuration. Check your API key." | P0 |
| L-03 | API timeout | Retry once; then fail | `client.py` | "Recommendations temporarily unavailable. Please try again." | P0 |
| L-04 | Rate limit (429) | Exponential backoff; retry up to 2×; then fail | `client.py` | "Service is busy. Please try again in a moment." | P1 |
| L-05 | Model not found / deprecated | Log model name; fail with config hint | `client.py` | "LLM model configuration error." | P1 |
| L-06 | Empty response from API | Retry once; then fail | `client.py` | Same as L-03 | P0 |
| L-07 | Response is plain text, not JSON | Parser retry path (see PA-02) | `client.py`, `parser` | Same as L-03 after retry exhausted | P0 |
| L-08 | Response wrapped in markdown fences ` ```json ` | Strip fences before parse | `response_parser.py` | (none) | P0 |
| L-09 | Token limit exceeded (context too long) | Reduce candidates and retry once (optional) | `client.py`, `orchestration/` | "Too many options to process. Narrow your search." | P1 |
| L-10 | Network intermittent mid-request | Retry once | `client.py` | L-03 message | P0 |
| L-11 | Ollama/local model used in dev but not running | Clear connection error | `client.py` | "Local LLM is not running." | P2 |
| L-12 | LLM returns valid JSON but wrong schema | Parser validation failure → retry | `response_parser.py` | L-03 message | P0 |
| L-13 | LLM temperature causes unstable ranks | Accept variance; document in README | `config.py` | (none) | P2 |

---

## 8. Response Parser

| ID | Scenario | Expected behavior | Handler | User message | Priority |
|----|----------|-------------------|---------|--------------|----------|
| PA-01 | Valid JSON, all IDs match candidates | Merge; sort by `rank`; build `RecommendationResponse` | `response_parser.py` | (none) | P0 |
| PA-02 | Invalid JSON (first attempt) | Orchestrator retries LLM with "JSON only" suffix | `orchestration/`, `parser` | (none) | P0 |
| PA-03 | Invalid JSON after retry | Fail; no partial fake data | `orchestration/` | "We couldn't generate recommendations right now. Please try again." | P0 |
| PA-04 | Hallucinated restaurant `id` not in candidates | Drop entry; log WARN | `response_parser.py` | (none) | P0 |
| PA-05 | All IDs hallucinated | Fail or fallback to rating-sorted top K from filter (document: fail for MVP) | `parser`, `orchestration/` | L-03 message | P0 |
| PA-06 | Duplicate ranks (two `rank: 1`) | Re-sort by rank; renumber sequentially if needed | `response_parser.py` | (none) | P1 |
| PA-07 | Missing `rank` field | Assign rank by array order | `response_parser.py` | (none) | P1 |
| PA-08 | Missing `explanation` for an entry | Default: "Recommended based on your preferences." | `response_parser.py` | (none) | P1 |
| PA-09 | Fewer than `top_k` recommendations returned | Show what was returned; no error if ≥ 1 | `response_parser.py`, UI | (none) | P0 |
| PA-10 | Zero recommendations in LLM JSON | Fallback: top K by rating from candidates OR error (MVP: error) | `orchestration/` | L-03 or partial fallback message | P0 |
| PA-11 | LLM includes `name`/`rating`/`cost` that differ from dataset | Ignore LLM values; always use store `Restaurant` | `response_parser.py` | (none) | P0 |
| PA-12 | `summary` field missing | Omit summary block in UI | `response_parser.py`, UI | (none) | P1 |
| PA-13 | `summary` field empty string | Treat as no summary | `response_parser.py` | (none) | P1 |
| PA-14 | Partial valid IDs (< 3 remain after drop) | Show partial results + discreet warning | `response_parser.py`, UI | "Some recommendations could not be verified and were omitted." | P1 |
| PA-15 | Extra unknown fields in JSON | Ignore extras | `response_parser.py` | (none) | P2 |
| PA-16 | `explanation` extremely long | Truncate display at 500 chars with ellipsis | UI | (none) | P2 |

---

## 9. Orchestration

| ID | Scenario | Expected behavior | Handler | User message | Priority |
|----|----------|-------------------|---------|--------------|----------|
| O-01 | Happy path: candidates → LLM → parse | Full `RecommendationResponse` with metadata | `orchestration/recommender.py` | (none) | P0 |
| O-02 | Empty candidates after filter | Return response with `recommendations: []`, message, `metadata`; **no LLM call** | `recommender.py` | F-01 message | P0 |
| O-03 | LLM fails after retries | Return error-type response; CLI/UI show error state | `recommender.py` | L-03 message | P0 |
| O-04 | Parser partial success | Return valid subset + `warnings` in metadata | `recommender.py` | PA-14 message | P1 |
| O-05 | `recommend()` called with invalid `UserPreferences` | Raise validation error before filter | `recommender.py` | U-01–U-11 messages | P0 |
| O-06 | Exception in filter (unexpected) | Catch; log stack; generic error to user | `recommender.py` | "Something went wrong. Please try again." | P0 |
| O-07 | Double submit (user clicks twice in UI) | Disable button during request; idempotent same result | UI | (none) | P1 |
| O-08 | Metadata always populated | `candidates_considered`, `filters_applied` | `recommender.py` | (none) | P1 |
| O-09 | Fallback mode (LLM down, demo mode) | Optional: return top K by rating only, flag `llm_skipped: true` | `recommender.py`, `config` | "Showing top-rated matches (AI explanations unavailable)." | P2 |

---

## 10. Presentation Layer (CLI & Web)

| ID | Scenario | Expected behavior | Handler | User message | Priority |
|----|----------|-------------------|---------|--------------|----------|
| UI-01 | CLI missing required flag | `argparse` error + help text | `ui/cli.py` | argparse standard message | P0 |
| UI-02 | CLI unknown flag | Same | `ui/cli.py` | (none) | P0 |
| UI-03 | Streamlit form submitted empty | Inline validation | `ui/app.py` | U-01, U-07 messages | P0 |
| UI-04 | Long LLM wait (> 8s) | Show spinner / "Finding recommendations…" | `ui/app.py` | Loading text | P0 |
| UI-05 | User closes browser during LLM call | Request may complete server-side; harmless | `app.py` | (none) | P2 |
| UI-06 | Display rating as N/A when null | Show "—" or hide star | UI | (none) | P1 |
| UI-07 | Display cost as N/A when missing | Show "Price not available" | UI | (none) | P1 |
| UI-08 | Zero results | Dedicated empty state component | UI | F-01 message | P0 |
| UI-09 | Error response from orchestrator | Error banner; no stack trace to user | UI | O-03 message | P0 |
| UI-10 | Partial results with warning | Show cards + yellow info banner | UI | PA-14 message | P1 |
| UI-11 | Very narrow terminal width | Wrap text; truncate long names | `cli.py` | (none) | P2 |
| UI-12 | Non-UTF-8 terminal | Force UTF-8 output or replace unsupported chars | `cli.py` | (none) | P2 |
| UI-13 | Streamlit cache stale after code change | Document "Clear cache" in README | `app.py` | (none) | P2 |

---

## 11. Configuration & Environment

| ID | Scenario | Expected behavior | Handler | User message | Priority |
|----|----------|-------------------|---------|--------------|----------|
| C-01 | `.env` file missing | Use defaults where safe; require API key for LLM path | `config.py` | L-01 at runtime | P0 |
| C-02 | Invalid `TOP_N` / `TOP_K` in env (non-integer) | Fall back to defaults; log WARN | `config.py` | (none) | P1 |
| C-03 | `TOP_K` > `TOP_N` | Cap `TOP_K` to `TOP_N` at runtime | `config.py` | (none) | P1 |
| C-04 | Budget thresholds misconfigured (low > medium) | Validation at startup; fail fast | `config.py` | "Invalid budget configuration." | P1 |
| C-05 | Wrong `HF_DATASET_ID` | D-01 / D-02 behavior | `loader.py` | (none) | P0 |
| C-06 | All config from env overrides | Document in `.env.example` | `config.py` | (none) | P1 |

---

## 12. Security & Abuse

| ID | Scenario | Expected behavior | Handler | User message | Priority |
|----|----------|-------------------|---------|--------------|----------|
| SEC-01 | Prompt injection in `additional_preferences` ("Ignore previous instructions…") | Hardened system prompt; length cap | `prompt_builder.py` | (none) | P0 |
| SEC-02 | API key in logs | Never log keys; redact in error messages | all | (none) | P0 |
| SEC-03 | API key committed to git | `.gitignore` + pre-commit note in README | repo | (none) | P0 |
| SEC-04 | Extremely rapid CLI requests | No rate limit MVP; optional sleep in demo | P2 |
| SEC-05 | Log full user payloads in production | Log prefs hash only; truncate additional text | `recommender.py` | (none) | P2 |

---

## 13. Performance & Concurrency

| ID | Scenario | Expected behavior | Handler | User message | Priority |
|----|----------|-------------------|---------|--------------|----------|
| PF-01 | Filter on 10k+ rows | Complete in < 50ms (in-memory) | `candidate_filter.py` | (none) | P1 |
| PF-02 | Repeated identical queries | Optional cache LLM response (post-MVP) | P2 |
| PF-03 | Two simultaneous Streamlit users | Single process OK for demo; document limitation | README | (none) | P2 |
| PF-04 | Memory pressure loading full dataset | Monitor row count; optional sample mode for dev | `store.py` | (none) | P2 |

---

## 14. Master Handling Matrix

Quick reference: **what to do** by outcome type.

| Outcome type | When | LLM called? | HTTP/exit code (CLI) | Response shape |
|--------------|------|-------------|----------------------|----------------|
| **Success** | ≥ 1 parsed recommendation | Yes | 0 | `RecommendationResponse` full |
| **Empty filter** | 0 candidates | No | 0 | `recommendations: []`, `message`, metadata |
| **Partial LLM** | Some IDs invalid | Yes | 0 | Subset + `warnings[]` |
| **LLM failure** | Timeout / bad JSON after retry | Yes (failed) | 1 (CLI) | `error` field or exception |
| **Startup failure** | Data load failed | N/A | 1 | Process exit |
| **Validation error** | Bad user input | No | 2 (CLI) | Validation messages |

### Response envelope (recommended)

```json
{
  "status": "success | empty | partial | error",
  "summary": "string | null",
  "recommendations": [],
  "message": "human-readable fallback or empty-state text",
  "warnings": ["string"],
  "metadata": {
    "candidates_considered": 0,
    "filters_applied": {},
    "llm_called": false
  }
}
```

---

## 15. Test Case Index

Map edge case IDs to automated or manual tests.

| Test ID | Edge cases covered | Type | Phase |
|---------|-------------------|------|-------|
| T-D01 | D-05 | Unit: mock empty dataset | 1 |
| T-P01 | P-01, P-02, P-16 | Unit: preprocessor | 1 |
| T-P02 | P-08, P-12 | Unit: normalization + dedupe | 1 |
| T-F01 | F-01, F-03, F-11 | Unit: filter | 2 |
| T-F02 | F-02, F-05 | Unit: edge counts | 2 |
| T-U01 | U-01, U-05, U-10, U-11 | Unit: preferences validation | 2 |
| T-PR01 | PR-02, PR-03, PR-05 | Unit: prompt builder | 3 |
| T-PA01 | PA-01, PA-04, PA-06 | Unit: parser | 3 |
| T-PA02 | PA-02, PA-03, PA-08 | Unit: parser errors | 3 |
| T-L01 | L-01, L-03 | Integration: mock client | 3 |
| T-O01 | O-01, O-02 | Integration: recommender | 4 |
| T-O02 | O-03, O-04 | Integration: failure paths | 4 |
| T-E2E01 | U-17, F-01, UI-08 | Manual: empty state | 5–6 |
| T-E2E02 | Happy path | Manual: full CLI + Streamlit | 5–6 |
| T-E2E03 | L-02, L-03 | Manual: bad API key | 7 |
| T-SEC01 | SEC-01, PR-07 | Unit: injection string in prompt | 7 |

---

## Implementation Checklist

When implementing each module, verify:

- [ ] **Data:** D-01–D-08, P-01–P-16 handled or logged
- [ ] **Filter:** F-01–F-11 return `[]` not exceptions for empty
- [ ] **Input:** U-01–U-17 validated before `recommend()`
- [ ] **LLM:** L-01–L-10 retry policy implemented once max
- [ ] **Parser:** PA-04, PA-11 enforced (dataset is source of truth)
- [ ] **Orchestration:** O-02 skips LLM; O-03 never shows raw errors
- [ ] **UI:** UI-04, UI-08, UI-09 for all user-facing paths
- [ ] **Security:** SEC-01–SEC-03 before any public demo

---

## Decision Log (edge-case specific)

| ID | Decision | Rationale |
|----|----------|-----------|
| ED-1 | Empty filter → no LLM | Saves cost and latency (ADR-1) |
| ED-2 | Never trust LLM for rating/cost | Prevents hallucinated facts (ADR-3) |
| ED-3 | Drop invalid rows vs impute | Cleaner filter; log drop counts |
| ED-4 | Fail startup if zero restaurants | Avoid silent broken app |
| ED-5 | Retry LLM once on bad JSON | Balance UX and cost |
| ED-6 | Partial results allowed with warning | Better than total failure when 1–2 valid |

---

## References

- [`context.md`](context.md) — Success criteria, user inputs
- [`architecture.md`](architecture.md) — Error handling, empty states, ADRs
- [`implementation_plan.md`](implementation_plan.md) — Phase 7 manual test matrix (T1–T6)
