# Auto-Research SaaS Platform — Plan

## Overview

Turn the parameter-golf research automation into a multi-tenant SaaS where Skool community members subscribe, get a web UI to configure and monitor AI-driven ML experiments, and pay based on usage tiers.

## Repo Structure

**Separate repo** (`auto-research-platform` or similar). Reasons:
- parameter-golf is competition-specific, this is a product
- Different deploy targets, CI, secrets, user management
- parameter-golf becomes one "research template" the platform can run

```
auto-research-platform/
├── api/                    # Backend (FastAPI or similar)
│   ├── auth/               # User management, API keys
│   ├── experiments/        # Experiment CRUD, queue management
│   ├── billing/            # Usage tracking, tier enforcement
│   ├── fleet/              # GPU orchestration (extracted from parameter-golf)
│   └── websocket/          # Live log streaming
├── web/                    # Frontend (Next.js or similar)
│   ├── dashboard/          # Experiment status, results, cost
│   ├── chat/               # Chat interface to research agent
│   ├── results/            # Compare, visualize, export
│   └── settings/           # Account, billing, API keys
├── engine/                 # Research engine (core logic extracted from parameter-golf)
│   ├── templates/          # Research templates (parameter-golf = first one)
│   ├── skills/             # Reusable skills (deploy, collect, compare)
│   └── pipeline/           # Explore → validate → full pipeline
├── infra/                  # Deployment
│   ├── docker-compose.yml
│   ├── terraform/          # GPU provisioning (future)
│   └── nginx/
└── db/                     # Migrations, schema
```

## Pricing Tiers

Payments via Skool initially, manual user provisioning. Keep it cheap to build community.

| Tier | Price/mo | What they get |
|------|----------|---------------|
| **Starter** | $9 | 50 explore runs/mo, view results, basic chat, 1 experiment at a time |
| **Researcher** | $29 | 200 explore + 20 validate runs/mo, priority queue, full chat, 3 concurrent |
| **Pro** | $79 | Unlimited explore, 100 validate + 5 full runs/mo, dedicated GPU time slots, API access |
| **Team** | $149 | Everything in Pro, 3 seats, shared results, team dashboard |

> Actual GPU cost per run (legacy single-GPU reference): explore ~$0.50, validate ~$2-5, full ~$12.
> At these prices Starter/Researcher tiers are profitable even at full usage.
> Pro tier needs usage monitoring — heavy users could exceed margin.

### Usage tracking
- Count by **experiment runs** (not tokens — simpler mental model for users) [very good idea]
- Track GPU-minutes as internal cost metric
- Soft limits with warnings, hard limits block new submissions
- Unused runs do NOT roll over

## MVP Scope (Phase 1)

Goal: Get 10 paying Skool members using it within 4 weeks.

### Backend
- [ ] FastAPI app with SQLite (upgrade to Postgres later)
- [ ] User model: email, tier, runs_remaining, api_key
- [ ] Manual user provisioning endpoint (you add users after Skool payment)
- [ ] Experiment submission: user picks template, sets overrides, submits
- [ ] Queue management: tier-based priority, concurrency limits
- [ ] Results collection: poll GPUs, store results, associate with user
- [ ] WebSocket endpoint for live log streaming

### Frontend
- [ ] Login (magic link or simple password)
- [ ] Dashboard: active experiments, recent results, runs remaining
- [ ] New experiment form: template selector, parameter overrides, steps
- [ ] Results viewer: table ranked by val_bpb, expandable details
- [ ] Live training view: loss curve, step progress, ETA
- [ ] Simple chat: send messages to Claude API, get research suggestions

### Infrastructure
- [ ] Single VPS (Hetzner/Railway) for API + frontend
- [ ] GPUs stay as-is (SSH fleet from parameter-golf)
- [ ] Cron job to sync results every 2 hours (reuse gpu_sync_cron.sh)
- [ ] Basic rate limiting and auth middleware

### NOT in MVP
- Automated Stripe/payment integration (Skool handles this)
- Multi-template support (just parameter-golf for now)
- User-uploaded training scripts
- GPU auto-provisioning
- Team features

## Phase 2 (After 20+ users)

- [ ] Stripe integration, self-serve signup
- [ ] Postgres + proper migrations
- [ ] Multiple research templates (vision, RL, fine-tuning)
- [ ] User-defined training scripts (sandboxed)
- [ ] Automated GPU scaling (spin up/down based on queue depth)
- [ ] Result sharing / public leaderboard
- [ ] API for programmatic access
- [ ] Referral program tied to Skool

## Phase 3 (Scale)

- [ ] Multi-cloud GPU provisioning (Lambda, RunPod, etc.)
- [ ] Custom model templates marketplace
- [ ] Team workspaces with RBAC
- [ ] Webhook integrations (Slack, Discord notifications)
- [ ] White-label option for other communities

## Manual Onboarding Flow (Phase 1)

```
1. User joins Skool community, picks tier, pays via Skool
2. You get notified in Skool
3. Run: curl -X POST localhost:8000/admin/users \
     -d '{"email":"user@example.com","tier":"researcher"}'
4. User gets magic link email
5. User logs in, sees dashboard, starts submitting experiments
```

## Tech Stack Recommendation

| Layer | Choice | Why |
|-------|--------|-----|
| Backend | FastAPI (Python) | Same language as training code, easy to extract engine logic |
| Frontend | Next.js | Fast to build, good DX, SSR for dashboard |
| DB | SQLite → Postgres | Start simple, migrate when needed |
| Auth | Simple JWT + magic links | No OAuth complexity for MVP |
| Hosting | Railway or Hetzner VPS | Cheap, simple, good for MVP |
| Chat | Claude API direct | You already have the skills/prompts |
| Real-time | WebSockets | Live training logs |

## Key Decisions

1. **Separate repo** — parameter-golf stays as the research engine/template
2. **Experiment runs as billing unit** — not tokens, not GPU-minutes (user-facing simplicity)
3. **Skool for payments** — no Stripe integration until Phase 2
4. **Manual provisioning** — you add users, keeps MVP scope tiny
5. **Same GPU fleet** — no new infra, just multi-tenant queue management
6. **Priority queues by tier** — Pro users get scheduled before Starter

## Risks

- **GPU contention**: Multiple users competing for same fleet. Mitigation: tier-based scheduling, queue limits.
- **Cost overruns on Pro tier**: Heavy users could blow past margins. Mitigation: track GPU-minutes, set internal alerts.
- **Security**: Users submitting arbitrary training configs could be dangerous. Mitigation: whitelist allowed env vars, no arbitrary code execution in Phase 1.
- **Support burden**: Research is complex, users will need help. Mitigation: good defaults, templates, chat interface for guidance.
