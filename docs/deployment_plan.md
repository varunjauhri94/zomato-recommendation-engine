# BiteAI Deployment Plan

> **Backend** → Railway (FastAPI + Uvicorn)
> **Frontend** → Vercel (Vite + React static build)

---

## Architecture Overview

```
┌──────────────────────┐       HTTPS        ┌──────────────────────────┐
│   Vercel (Frontend)  │ ───────────────────►│   Railway (Backend API)  │
│   Static React SPA   │   /api/* rewrite    │   FastAPI + Uvicorn      │
│   biteai.vercel.app  │ ◄─────────────────  │   biteai-api.up.railway  │
└──────────────────────┘       JSON          └──────────────────────────┘
                                                      │
                                                      │ On cold start
                                                      ▼
                                              ┌─────────────────┐
                                              │  Hugging Face    │
                                              │  Dataset API     │
                                              │  (12,137 rows)   │
                                              └─────────────────┘
```

---

## Part 1 — Backend on Railway

### 1.1 Prerequisites

- A Railway account (https://railway.com — free trial available; Hobby plan at $5/month recommended)
- The project pushed to a GitHub/GitLab repo

### 1.2 Files to Create / Modify

#### [NEW] `Procfile` (project root)

Railway uses a Procfile to know how to start the app:

```
web: uvicorn src.ui.api:app --host 0.0.0.0 --port $PORT
```

> **Why `$PORT`?** Railway dynamically assigns a port via the `PORT` env var. Hardcoding `8000` will not work.

#### [NEW] `runtime.txt` (project root — optional)

Pin the Python version:

```
python-3.11.9
```

#### [MODIFY] `src/ui/api.py` — CORS origins

Currently CORS is `allow_origins=["*"]`. For production, restrict to your Vercel domain:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://biteai.vercel.app",       # Production
        "http://localhost:5173",            # Local dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

> Replace `biteai.vercel.app` with your actual Vercel deployment URL.

### 1.3 Environment Variables on Railway

Go to **Railway Dashboard → Your Service → Variables** and set:

| Variable              | Value                                              | Notes                          |
| --------------------- | -------------------------------------------------- | ------------------------------ |
| `GROQ_API_KEY`        | `gsk_xxxxx`                                        | **Required** for LLM ranking   |
| `LLM_MODEL`           | `llama-3.3-70b-versatile`                          | Default is fine                 |
| `LLM_TEMPERATURE`     | `0.3`                                              | Default is fine                 |
| `HF_DATASET_ID`       | `ManikaSaini/zomato-restaurant-recommendation`     | Default is fine                 |
| `HF_HOME`             | `/tmp/hf_cache`                                    | Writable path on Railway        |
| `DATA_CACHE_PATH`     | `/tmp/data_cache/restaurants.pkl`                   | Writable path on Railway        |
| `USE_DATA_CACHE`      | `true`                                             | Avoids re-downloading on restarts |
| `TOP_N_CANDIDATES`    | `30`                                               | Default is fine                 |
| `TOP_K_RECOMMENDATIONS` | `5`                                              | Default is fine                 |

> [!CAUTION]
> Railway's filesystem is **ephemeral** — the pickle cache in `/tmp` will be lost on every deploy/restart. The first cold start will download 12,137 records from Hugging Face (~10-20s). Subsequent requests within the same container lifecycle will use the in-memory store.

### 1.4 Railway Deployment Steps

1. **Push code to GitHub** (ensure the repo includes the `Procfile` and `requirements.txt` at root)

2. **Create a new project on Railway:**
   - Go to https://railway.com/dashboard → **New Project** → **Deploy from GitHub Repo**
   - Select your repository
   - Railway auto-detects `requirements.txt` → Python Nixpack builder

3. **Configure the service:**
   - Set root directory to `/` (the project root, not `/frontend`)
   - Add all environment variables from the table above
   - Railway auto-assigns a domain like `biteai-api-production.up.railway.app`

4. **Verify deployment:**
   ```
   curl https://YOUR-RAILWAY-URL.up.railway.app/api/filters
   ```
   Should return `{"status":"success","locations":[...],"cuisines":[...]}`

5. **Note down your Railway URL** — you'll need it for the frontend Vercel config.

### 1.5 Railway Gotchas

| Issue | Solution |
|-------|----------|
| **Cold start slow** (~15-20s) | First request downloads HF dataset. Consider Railway's "Always On" option (Hobby plan). |
| **Ephemeral filesystem** | Pickle cache is lost on redeploy. The in-memory store rebuilds automatically. |
| **Memory limits** | 12,137 restaurant objects in memory ~50-80 MB. Railway free tier (512 MB) is sufficient. |
| **No `.env` file deployed** | Railway uses env vars from dashboard, not `.env` file. `.env` is gitignored. |

---

## Part 2 — Frontend on Vercel

### 2.1 Prerequisites

- A Vercel account (https://vercel.com — free Hobby tier works)
- Frontend code pushed to GitHub (can be the same repo as backend)

### 2.2 Files to Create / Modify

#### [NEW] `frontend/vercel.json`

This is the critical file. It tells Vercel to:
1. Rewrite all `/api/*` requests to your Railway backend
2. Serve the React SPA with proper fallback routing

```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://YOUR-RAILWAY-URL.up.railway.app/api/:path*"
    },
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        }
      ]
    }
  ]
}
```

> Replace `YOUR-RAILWAY-URL.up.railway.app` with the actual Railway deployment URL from Step 1.4.

#### [MODIFY] `frontend/vite.config.ts` — Keep proxy for local dev only

The existing Vite proxy (`/api → localhost:8000`) only works in `vite dev` mode. It is **not used** in production builds. No changes needed — the `vercel.json` rewrites handle production routing.

```ts
// vite.config.ts — NO CHANGES NEEDED
// The `server.proxy` block only applies during `npm run dev`
// Vercel's `vercel.json` rewrites handle production API routing
```

#### [NO CHANGE] `frontend/src/App.tsx`

The frontend already uses **relative paths** (`/api/filters`, `/api/recommend`). This works perfectly with both:
- **Local dev**: Vite proxy rewrites to `localhost:8000`
- **Vercel production**: `vercel.json` rewrites to Railway URL

### 2.3 Vercel Deployment Steps

1. **Go to Vercel dashboard** → **Add New Project** → **Import Git Repository**

2. **Configure the project:**

   | Setting            | Value            |
   | ------------------ | ---------------- |
   | **Framework Preset** | Vite             |
   | **Root Directory** | `frontend`       |
   | **Build Command**  | `npm run build`  |
   | **Output Directory** | `dist`          |
   | **Install Command** | `npm install`   |

   > [!IMPORTANT]
   > Set the **Root Directory** to `frontend` — this is a monorepo and the frontend is not at the project root.

3. **No environment variables needed** on Vercel — the frontend has no secrets. All API calls go through the `/api` rewrite.

4. **Deploy** — Vercel will run `tsc -b && vite build` and serve the static `dist/` folder.

5. **Verify:**
   - Visit `https://your-app.vercel.app/` → Should load the BiteAI UI
   - Click "Discover Restaurants" → Should call the Railway backend and return results

### 2.4 Vercel Gotchas

| Issue | Solution |
|-------|----------|
| **API calls return 404** | Check `vercel.json` rewrite URL matches your Railway domain exactly |
| **CORS errors in console** | Ensure Railway backend's CORS `allow_origins` includes your Vercel URL |
| **Build fails on TypeScript** | Run `cd frontend && npx tsc --noEmit` locally first to catch type errors |
| **Blank page after deploy** | Ensure Root Directory is set to `frontend`, not `/` |

---

## Part 3 — Deployment Checklist

### Pre-Deploy

- [ ] Push all code to GitHub (ensure `.env` is in `.gitignore`)
- [ ] Create `Procfile` at project root
- [ ] Create `frontend/vercel.json` with correct Railway URL
- [ ] Update CORS in `src/ui/api.py` with Vercel domain
- [ ] Test production build locally:
  ```bash
  # Backend
  uvicorn src.ui.api:app --host 0.0.0.0 --port 8000

  # Frontend (production build test)
  cd frontend && npm run build && npm run preview
  ```

### Deploy Backend (Railway)

- [ ] Create Railway project from GitHub repo
- [ ] Set root directory to `/`
- [ ] Add all environment variables (especially `GROQ_API_KEY`)
- [ ] Wait for deployment to succeed
- [ ] Test: `curl https://YOUR-RAILWAY-URL/api/filters`
- [ ] Copy the Railway URL

### Deploy Frontend (Vercel)

- [ ] Create Vercel project from same GitHub repo
- [ ] Set root directory to `frontend`
- [ ] Set framework preset to **Vite**
- [ ] Update `vercel.json` with the Railway URL from above
- [ ] Deploy and test the full flow

### Post-Deploy Verification

- [ ] Homepage loads with BiteAI branding
- [ ] Filter dropdowns populate (locations + cuisines from API)
- [ ] "Discover Restaurants" returns AI-ranked results
- [ ] Empty state shows diagnostic messages correctly
- [ ] No CORS errors in browser console

---

## Part 4 — Custom Domain (Optional)

### Vercel (Frontend)

1. Go to **Project Settings → Domains**
2. Add your custom domain (e.g., `biteai.yourdomain.com`)
3. Update DNS as instructed by Vercel

### Railway (Backend)

1. Go to **Service Settings → Networking → Custom Domain**
2. Add your API domain (e.g., `api.biteai.yourdomain.com`)
3. Update DNS as instructed by Railway

Then update:
- `vercel.json` rewrite destination → `https://api.biteai.yourdomain.com/api/:path*`
- `api.py` CORS origins → add `https://biteai.yourdomain.com`

---

## Part 5 — Cost Estimation

| Service   | Plan   | Monthly Cost | What You Get                          |
| --------- | ------ | ------------ | ------------------------------------- |
| Railway   | Hobby  | ~$5          | 8 GB RAM, 8 vCPU, always-on capable  |
| Vercel    | Hobby  | Free         | 100 GB bandwidth, auto SSL, CDN      |
| Groq API  | Free   | Free         | 14,400 requests/day, rate limited     |
| **Total** |        | **~$5/month**|                                       |

> [!TIP]
> Both Railway and Vercel offer free tiers that are sufficient for a portfolio project. The Railway free trial gives $5 of credits. Vercel Hobby is free for personal projects.

---

## Quick Reference — File Changes Summary

| File | Action | Purpose |
|------|--------|---------|
| `Procfile` | **CREATE** | Railway start command |
| `runtime.txt` | **CREATE** (optional) | Pin Python version |
| `src/ui/api.py` | **MODIFY** | Restrict CORS to Vercel domain |
| `frontend/vercel.json` | **CREATE** | API rewrite rules for production |
| `frontend/vite.config.ts` | No change | Proxy only used in local dev |
| `frontend/src/App.tsx` | No change | Already uses relative `/api` paths |
