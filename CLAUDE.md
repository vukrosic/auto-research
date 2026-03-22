# Auto-Research Platform

## What This Is

A multi-tenant autonomous AI research platform. Users submit ML experiments, AI agents handle everything (support, onboarding, moderation, ops). Revenue funds open-source research.

## Project Structure

See `PLAN.md` for full architecture. Key directories:
- `api/` — FastAPI backend
- `web/` — Next.js frontend
- `agents/` — AI agents that replace all human ops
- `engine/` — Core research engine (wraps parameter-golf and future templates)

## Development

```bash
# Backend
cd api && pip install -r requirements.txt && uvicorn main:app --reload

# Frontend
cd web && npm install && npm run dev
```

## Connection to parameter-golf

This platform wraps `/root/parameter-golf` as its first research template. The engine submits experiments via parameter-golf's `infra/run_experiment.sh` and collects results from `results/`.

## Key Principle

**Zero human ops.** Every user-facing interaction is handled by AI agents. Vuk approves things with one click max. If something requires more than a click, build an agent for it.

## Conventions

- Python backend, TypeScript frontend
- All AI agents use Claude API
- `lab` branch for development
- Keep it simple — no over-engineering
