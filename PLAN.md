# Auto-Research Platform — Master Plan

## Vision

A self-funding autonomous AI research lab disguised as a platform. Users pay for access to automated ML research tools. Revenue funds open-source research at scale. **Vuk deals with zero people** — every human interaction is handled by AI.

## Core Principle: Zero Human Ops

Every interaction that would normally require a human operator is handled by AI agents:

| Interaction | Traditional | Auto-Research |
|-------------|-------------|---------------|
| User signup | Manual approval | AI agent processes Skool webhook, provisions account |
| Support tickets | Human responds | AI chatbot with full platform context answers |
| Onboarding | Tutorial calls | AI-guided interactive onboarding in the UI |
| Billing issues | Manual review | AI agent checks Skool status, resolves or escalates to email |
| Competition setup | Admin creates | AI proposes competitions from trending research, you approve with one click |
| Result disputes | Manual review | AI agent re-runs experiment, compares, auto-resolves |
| Community moderation | Human mod | AI moderator in Skool + platform comments |
| Partner outreach | Cold emails | AI drafts and sends partnership proposals (you approve) |
| Bug reports | Triage + fix | AI triages, creates GitHub issue, attempts auto-fix |

## Two Modes

### 1. Competition Mode
- Curated research challenges (parameter-golf is #1)
- Leaderboards, prizes (sponsored by GPU/LM providers)
- Time-boxed, community-driven
- Results become open-source research

### 2. Custom Research Mode
- Users define their own research problems
- Bring Your Own GPU/API or use hosted fleet
- Same automation pipeline (explore → validate → full)
- Private results by default, option to publish

**Both modes use the same engine.** Vuk uses Custom Research Mode for his own work. The platform IS his research tool.

## Architecture

```
auto-research/
├── PLAN.md                     # This file
├── CLAUDE.md                   # Dev instructions
├── requirements.txt
├── docker-compose.yml
│
├── api/                        # FastAPI backend
│   ├── main.py                 # App entry point
│   ├── config.py               # Settings, env vars
│   ├── models.py               # SQLAlchemy models
│   ├── database.py             # DB setup
│   │
│   ├── routers/
│   │   ├── auth.py             # Login, magic links, API keys
│   │   ├── experiments.py      # Submit, list, cancel experiments
│   │   ├── competitions.py     # Competition CRUD, leaderboards
│   │   ├── results.py          # View, compare, export results
│   │   ├── fleet.py            # GPU status (admin + user's own)
│   │   ├── chat.py             # AI research assistant
│   │   ├── webhooks.py         # Skool payment webhooks
│   │   └── admin.py            # Admin endpoints (your use)
│   │
│   ├── services/
│   │   ├── ai_support.py       # AI agent for all user-facing comms
│   │   ├── ai_onboarding.py    # Guided onboarding agent
│   │   ├── ai_moderator.py     # Community moderation agent
│   │   ├── experiment_runner.py # Queue management, GPU dispatch
│   │   ├── billing.py          # Usage tracking, tier enforcement
│   │   ├── notifications.py    # Email/webhook notifications
│   │   └── skool_sync.py       # Skool membership → platform accounts
│   │
│   └── templates/              # Research templates
│       └── parameter_golf/     # Symlink or config pointing to parameter-golf
│
├── web/                        # Next.js frontend
│   ├── app/
│   │   ├── page.tsx            # Landing page
│   │   ├── dashboard/          # Main dashboard
│   │   ├── experiment/         # Experiment submission + monitoring
│   │   ├── competitions/       # Browse, join, leaderboard
│   │   ├── results/            # View + compare results
│   │   ├── chat/               # AI research assistant
│   │   └── settings/           # Account, GPU credentials (BYOG)
│   ├── components/
│   └── lib/
│
├── agents/                     # AI agents that replace human ops
│   ├── support_agent.py        # Handles all support queries
│   ├── onboarding_agent.py     # Guides new users
│   ├── moderation_agent.py     # Moderates community content
│   ├── outreach_agent.py       # Drafts partner/sponsor emails
│   ├── competition_agent.py    # Proposes + manages competitions
│   └── ops_agent.py            # Monitors platform health, auto-fixes
│
├── engine/                     # Core research engine
│   ├── pipeline.py             # explore → validate → full
│   ├── orchestrator.py         # Multi-tenant GPU scheduling
│   ├── collector.py            # Pull results from GPUs
│   ├── analyzer.py             # Compare, rank, summarize
│   └── templates.py            # Template registry
│
└── infra/
    ├── Dockerfile
    ├── nginx.conf
    └── deploy.sh
```

## AI Agents — The "No People" Layer

### Support Agent (`agents/support_agent.py`)
- Receives all user messages (chat widget, email, Skool DMs)
- Has full context: user's tier, experiments, results, platform docs
- Answers 95% of questions autonomously
- Escalation = creates a GitHub issue tagged `needs-vuk`, sends you a one-line summary
- You check GitHub issues once/day max, respond by commenting (agent relays to user)

### Onboarding Agent (`agents/onboarding_agent.py`)
- Triggers when new account is provisioned
- Walks user through: what the platform does, how to submit first experiment, how to read results
- Interactive chat, not a static tutorial
- Tracks completion, nudges if user drops off

### Moderation Agent (`agents/moderation_agent.py`)
- Reviews competition submissions for rule violations
- Moderates comments/discussions
- Auto-removes spam, flags edge cases
- You never see community content unless flagged

### Competition Agent (`agents/competition_agent.py`)
- Monitors trending ML research (papers, Twitter, GitHub)
- Proposes new competition ideas weekly
- You approve/reject with one click in admin panel
- Handles competition lifecycle: announce → run → score → award

### Ops Agent (`agents/ops_agent.py`)
- Monitors GPU fleet health, API uptime, error rates
- Auto-restarts failed experiments
- Alerts you only for critical issues (>5 min downtime, budget alerts)
- Generates weekly ops summary (you skim in 2 min)

### Outreach Agent (`agents/outreach_agent.py`)
- Identifies potential GPU/LM provider sponsors
- Drafts partnership emails
- You approve with one click, agent sends
- Tracks responses, follows up automatically

## Skool Integration (Phase 1 — Manual-ish)

```
User pays on Skool
  → Skool sends webhook (or you check daily)
  → skool_sync.py matches Skool member to platform account
  → If new user: creates account, triggers onboarding agent
  → If existing: updates tier, resets run counts
  → User gets email: "You're in, click here to start"
```

Phase 1 reality: Skool may not have webhooks. Fallback:
- Cron job polls Skool API (or scrapes member list) every hour
- New paying members auto-provisioned
- You literally never touch it

## Connection to parameter-golf

```
auto-research/
  engine/templates.py  →  knows about /root/parameter-golf/
                           reads train_gpt.py, infra/, queues/
                           submits experiments via run_experiment.sh
                           collects results from results/
```

- parameter-golf is the first "research template"
- The platform wraps it: multi-tenant queue, user isolation, result attribution
- Your own research uses the same platform — you're just another user (admin tier)
- Future templates: add more repos, each with their own train script + config

## Pricing (Confirmed)

| Tier | Price/mo | Runs | Concurrent | Features |
|------|----------|------|------------|----------|
| **Starter** | $9 | 50 explore | 1 | Dashboard, chat, results |
| **Researcher** | $29 | 200 explore + 20 validate | 3 | Priority queue, full chat |
| **Pro** | $79 | Unlimited explore, 100 validate, 5 full | 5 | Dedicated slots, API |
| **Team** | $149 | Pro x3 seats | 5/seat | Shared workspace |

BYOG users: platform fee only (50% off tier price), no run limits.

## Exit Criteria

Kill it if any are true for 2+ months:
1. You dread opening the laptop — it feels like obligation
2. Zero research output — ops/support but no actual research
3. <10 active users after 6 months
4. You're subsidizing compute out of pocket
5. You're considering raising equity money

Scale up if:
1. Users generate findings you wouldn't have found alone
2. Revenue covers compute + gives freedom money
3. >50% of your time is research, <50% is ops
4. Competition results are getting shared/cited externally

## Phase 1 MVP — 4 Week Sprint

Week 1: Backend core
- FastAPI app, user model, auth (magic links)
- Experiment submission + queue management
- Connect to parameter-golf (submit experiments via SSH)

Week 2: Frontend core
- Next.js dashboard, experiment form, results viewer
- Live training view (WebSocket log streaming)
- Basic chat interface (Claude API)

Week 3: AI agents
- Support agent (handles all in-app support)
- Onboarding agent (guides new users)
- Skool sync (auto-provision accounts)

Week 4: Polish + launch
- Ops agent (monitoring, auto-recovery)
- Landing page
- Deploy to Railway/Hetzner
- Invite first 10 Skool members

## Long-Term Vision

```
Revenue from platform users
  → Buys more GPU compute
    → Funds autonomous AI research (competitions + your own)
      → Produces open-source findings, models, techniques
        → Attracts more users + sponsors
          → More revenue → more compute → more research
            → Virtuous cycle: money as a tool for open research
```

You are the curator. AI runs the platform. The community does the research. You do whatever you want.
