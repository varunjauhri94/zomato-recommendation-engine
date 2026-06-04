# Project Context: AI-Powered Restaurant Recommendation System

## Overview

Build an **AI-powered restaurant recommendation service** inspired by **Zomato**. The system suggests restaurants based on user preferences by combining **structured restaurant data** with a **Large Language Model (LLM)** to produce personalized, human-like recommendations.

---

## Objective

Design and implement an application that:

1. Accepts user preferences (location, budget, cuisine, ratings, and more)
2. Uses a real-world restaurant dataset
3. Leverages an LLM to generate personalized, natural-language recommendations
4. Displays clear, useful results to the user

---

## Data Source

| Item | Detail |
|------|--------|
| **Dataset** | Zomato restaurant data on Hugging Face |
| **URL** | https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation |
| **Key fields** | Restaurant name, location, cuisine, cost, rating, and related attributes |

### Data Ingestion Responsibilities

- Load and preprocess the dataset from Hugging Face
- Extract relevant fields: name, location, cuisine, cost, rating, etc.
- Prepare data for filtering and LLM consumption

---

## User Input

Collect the following preferences from the user:

| Preference | Examples / Notes |
|------------|------------------|
| **Location** | Delhi, Bangalore, etc. |
| **Budget** | low, medium, high |
| **Cuisine** | Italian, Chinese, etc. |
| **Minimum rating** | Numeric or threshold filter |
| **Additional preferences** | family-friendly, quick service, etc. (free-form or structured) |

---

## System Workflow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Data Ingestion │ ──► │   User Input     │ ──► │ Integration Layer   │
│  (Hugging Face) │     │  (preferences)   │     │ (filter + prompt)   │
└─────────────────┘     └──────────────────┘     └──────────┬──────────┘
                                                            │
                                                            ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ Output Display  │ ◄── │ Recommendation   │ ◄── │ Recommendation      │
│ (top picks)     │     │ Engine (LLM)     │     │ Engine (LLM)        │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
```

### 1. Data Ingestion

- Load Zomato dataset from Hugging Face
- Preprocess and normalize fields for search and filtering

### 2. User Input

- Capture location, budget, cuisine, minimum rating, and optional extra preferences

### 3. Integration Layer

- Filter restaurant data according to user input
- Prepare a structured subset for the LLM
- Build a prompt that enables the LLM to **reason** and **rank** options

### 4. Recommendation Engine (LLM)

The LLM should:

- **Rank** restaurants by fit to user preferences
- **Explain** why each recommendation matches (per-restaurant rationale)
- **Optionally summarize** the overall set of choices

### 5. Output Display

Present top recommendations in a user-friendly format with:

- Restaurant name
- Cuisine
- Rating
- Estimated cost
- AI-generated explanation (why it was recommended)

---

## Technical Components (Implied)

| Component | Role |
|-----------|------|
| **Dataset loader** | Fetch and parse Hugging Face Zomato data |
| **Preprocessor / filter** | Apply user constraints on structured data |
| **Prompt builder** | Format filtered results + user prefs for the LLM |
| **LLM client** | Call model API for ranking and explanations |
| **UI / presentation layer** | Show ranked results with metadata and explanations |

---

## Success Criteria

- Recommendations reflect user-stated location, budget, cuisine, and rating constraints
- Output is readable and actionable (name, cuisine, rating, cost, explanation)
- LLM adds value beyond raw filtering (ranking, reasoning, optional summary)
- End-to-end flow: ingest → input → filter → LLM → display

---

## Constraints & Assumptions

- Dataset is the primary source of truth for restaurant attributes
- LLM is used for ranking and natural-language output, not as the sole data store
- User preferences drive both structured filtering and LLM context
- “Zomato-inspired” means similar UX goals (personalized dining suggestions), not necessarily production Zomato APIs

---

## Reference

Full problem statement: `docs/problem_statement.txt`
