# Volleyball AI

Volleyball AI is a full-stack project for analyzing full-match volleyball videos and surfacing setter-focused analytics in a web dashboard. The current scaffold covers Milestone 1 from the implementation plan: backend and frontend app shells, core schemas, and repo-level quality commands.

## Current Scope

- Full-match video workflow
- Fixed behind-the-court recordings
- User-selected `6-player` or `9-man` ruleset
- Both teams' setters when detectable
- Setter metrics centered on distribution, success, and tempo buckets

## Project Layout

- `backend/`: FastAPI-style backend scaffold, API routes, config, and schemas
- `frontend/`: React + TypeScript frontend scaffold built with Vite
- `tests/backend/`: backend unit tests
- `tests/frontend/`: frontend helper tests
- `docs/design.md`: product and technical design
- `plans/implementation-plan.md`: milestone plan

## Commands

- `make setup`: install backend and frontend dependencies
- `make lint`: run lightweight repository style checks
- `make typecheck`: compile backend Python modules and run frontend TypeScript checks
- `make test`: run backend unit tests and frontend Vitest tests
- `make analyze-local VIDEO_PATH=/abs/path/video.mp4 RULESET=6-player`: run local analysis and generate a static report
- `make run-backend`: start the backend locally without reload
- `make run-backend-reload`: start the backend locally with reload enabled
- `make run-frontend`: start the frontend locally

## Simple Local Workflow

If you want to avoid the webserver flow entirely, run the standalone local analysis script:

```bash
cd /Users/pengjujin/projects/volleyball_ai
python3 scripts/run_local_analysis.py \
  --video-path /Users/pengjujin/projects/volleyball_ai/data/short_game_data.mov \
  --ruleset 6-player \
  --title "Short Game Data"
```

Or analyze a YouTube video directly:

```bash
cd /Users/pengjujin/projects/volleyball_ai
python3 scripts/run_local_analysis.py \
  --youtube-url https://www.youtube.com/watch?v=abc123 \
  --ruleset 9-man \
  --title "YouTube Match"
```

Or with `make`:

```bash
cd /Users/pengjujin/projects/volleyball_ai
make analyze-local VIDEO_PATH=/Users/pengjujin/projects/volleyball_ai/data/short_game_data.mov RULESET=6-player TITLE="Short Game Data"
```

The script writes a static report site under `reports/<video-id>/` and prints a `file://.../index.html` link you can open directly in the browser.

## Local Dev

1. Start the backend with `make run-backend`.
2. Start the frontend with `make run-frontend`.
3. Open the frontend URL printed by Vite, usually `http://127.0.0.1:5173`.

In local dev, the Vite server proxies `/api` requests to `http://127.0.0.1:8000`, so the browser upload and job-status flow should now work end-to-end against the backend.

`make run-backend` is the recommended command for upload and background-processing tests because the app currently stores job state in memory. The reload variant is useful while editing code, but it can reset in-memory jobs and background threads.

If you need the frontend to talk to a different backend, set `VITE_API_BASE_URL` before starting Vite.

## Gemini Modes

The backend supports two processing modes:

- Default stub mode:
  - No Gemini key required
  - Useful for testing the local-path, upload, job polling, and dashboard flow end-to-end
- Live Gemini mode:
  - Set `GEMINI_API_KEY`
  - Set `VOLLEYBALL_AI_GEMINI_LIVE_ENABLED=true`
  - Uses the real Gemini SDK path for small clips and local videos

## Notes

- The backend includes a small compatibility shim so the scaffold can still import when `fastapi` is not installed yet.
- For the fastest local workflow, prefer `Local path` in the UI so the backend reads the video directly from disk without copying it into `/tmp`.
- YouTube ingestion is planned as best-effort support; local path and local upload are the primary paths.
# volleyball-ai-tinker
