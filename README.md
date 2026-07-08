# Codeforces Companion Platform

A full-stack analytics and coaching platform for competitive programmers on [Codeforces](https://codeforces.com). It aggregates a user's profile, rating history, and submissions into a single dashboard, recommends a daily practice problem tailored to their weak spots, and generates AI-written performance summaries.

## Features

- **Unified analytics dashboard** — concurrently fetches profile, rating history, and submission data from the Codeforces public API (`asyncio.gather`) and aggregates it into one payload: rating history, verdict breakdown, and top attempted tags.
- **Problem of the Day (POTD) engine** — assigns a daily problem using a weighted day-of-week matrix (50% core-focus on weak tags, 30% breadth on under-explored tags, 20% speed on strong tags), with graceful fallback if filters return no matches.
- **POTD verification** — idempotently checks the user's recent Codeforces submissions to confirm the daily problem was solved and updates a persistent ledger.
- **AI Coach** — sends pre-computed performance metrics (not raw submission data) to Google's Gemini API to generate a personalized diagnostic summary, cached server-side to control latency and cost.
- **Handle ownership verification** — a TLE-based proof-of-ownership challenge confirms a user controls the Codeforces handle they're logging in with, issuing a JWT on success.

## Tech Stack

**Backend:** FastAPI, Python, SQLAlchemy 2.0 (async), PostgreSQL (Supabase), httpx, python-jose (JWT)
**Frontend:** React 19, TanStack Start / Router / Query, TypeScript, Vite, Tailwind CSS, Radix UI, Recharts

## Project Structure

```
CodeforcesProject/
├── Server/           FastAPI backend
│   ├── server.py           API routes & app entrypoint
│   ├── auth.py / auth_router.py   JWT auth & handle-verification challenge
│   ├── codeforces_helper.py       Codeforces API client
│   ├── data_transformer.py        Raw data -> analytics aggregation
│   ├── potd_service.py            POTD recommendation + verification engine
│   ├── summary_service.py         Gemini AI Coach integration
│   ├── database.py / models.py    Async SQLAlchemy models & session
│   └── init_db.py                 Table provisioning script
├── Frontend/         React (TanStack Start) app
│   └── src/
│       ├── routes/                Pages (index, login)
│       ├── components/dashboard/  Dashboard UI (rating chart, POTD card, coach card, ...)
│       └── lib/api.ts              Typed API client
└── requirements.txt  Backend dependencies
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ (or Bun)
- A PostgreSQL database (e.g. [Supabase](https://supabase.com))
- A Google Gemini API key

### Backend setup

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
cp .env.example .env            # fill in your DATABASE_URL, GOOGLE_API_KEY, JWT_SECRET_KEY
python Server/init_db.py        # provisions tables
python Server/server.py         # starts the API on http://127.0.0.1:8000
```

API docs are available at `/docs` once running.

### Frontend setup

```bash
cd Frontend
npm install     # or: bun install
npm run dev     # or: bun run dev
```

## Environment Variables

See [.env.example](.env.example) for the full list (Google Gemini key, database URL, JWT secret/algorithm/expiry, challenge expiry window).

## API Overview

| Method | Endpoint                              | Description                                  |
| ------ | -------------------------------------- | --------------------------------------------- |
| POST   | `/api/v1/auth/challenge/{handle}`      | Issue a TLE ownership challenge for a handle  |
| POST   | `/api/v1/auth/verify/{handle}`         | Verify the challenge and issue a JWT          |
| GET    | `/api/v1/auth/me`                      | Get the authenticated user                    |
| POST   | `/api/v1/sync/{handle}`                | Fetch fresh Codeforces data and persist it    |
| GET    | `/api/v1/summary/{handle}`             | Get cached analytics summary                  |
| GET    | `/api/v1/summary/{handle}/ai-coach`    | Generate an AI Coach diagnostic summary       |
| GET    | `/api/v1/stats/{handle}`               | Get aggregated profile/rating/submission data |
| GET    | `/api/v1/potd/{handle}`                | Get (or generate) today's assigned problem    |
| POST   | `/api/v1/potd/{handle}/verify`         | Verify whether today's POTD was solved        |
