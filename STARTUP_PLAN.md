# Auto-Research — Startup Plan

## One-Liner

**Automated AI research platform. Ideas go in, validated improvements come out.**

Goal: every engineer, researcher, and hobbyist using this — open source (self-hosted) or paid (1-click) — to learn and do AI research faster than humanly possible.

---

## Product-Market Fit

### Who is the customer?

Engineers in the Skool community who are beginners and want to learn AI research. They don't have the ML expertise to design experiments, but they have ideas and curiosity. The platform lets them participate in real research without needing a PhD.

### What problem do we solve?

ML research has a brutal learning curve. You need to know what to try, how to set it up, how to interpret results, and how to iterate. Most beginners give up before getting a single meaningful result. Auto-research removes all of that — **you describe an idea, the system tests it, and tells you if it worked.**

### Why now?

- AI can code entire systems fast — one person + AI can build what took a team of 10
- GPU costs are dropping — cheap instances make experiment-as-a-service viable
- The parameter-golf competition provides a perfect, concrete evaluation metric (val_bpb)
- The Discord bot already works end-to-end as an MVP

### Distribution

- **Skool community**: Existing audience. Package as a course module — "run real AI research experiments"
- **Social media**: Users share results on Skool and Twitter/X — organic growth
- **Open source**: GitHub repo is the free tier. Self-hosters become evangelists
- **Discord**: Bot is the primary interface. Low friction, already familiar

### Validation plan

1. Ship Discord bot to Skool members as beta
2. Track: how many experiments run, retention, what ideas people submit
3. If members run experiments weekly and talk about results → PMF signal
4. If not → pivot the interface or audience before building more
- actually here i will build the project mainly for my own research and that way i will discover what others want as well

---

## How It Works

### The Research Loop

```
User describes idea (Discord bot or web)
        │
        ▼
AI translates idea → experiment config (8-10 variants)
        │
        ▼
Experiment runs through tiered elimination:
        │
        ├── Screen:   10 configs × 100 steps  (cheap, fast, kills bad ideas)
        ├── Explore:   top 5  × 300 steps  (confirm signal)
        └── Validate:  top 2  × 500 steps  (final confirmation)
        │
        ▼
Results returned to user with analysis
        │
        ▼
Winners → merged to best config
Losers  → knowledge base (never retry)
```

### What is "1 Experiment"?

A single experiment is the full tiered pipeline for one idea:

| Stage | Configs | Steps each | Purpose |
|-------|--------:|----------:|---------|
| Screen | 10 | 100 | Kill bad variants fast |
| Explore | top 5 | 300 | Confirm the signal is real |
| Validate | top 2 | 500 | Final confirmation before merge |

Total GPU time per experiment: ~30-60 min depending on hardware. The user submits one idea and gets back a full report — they never think about steps or configs.

### Key Principles

1. **Can't evaluate = can't auto-research.** Clear, measurable metric (val_bpb) is the prerequisite.
2. **Kill losers early.** Most ideas die at 100 steps. Only survivors get more compute.
3. **Single idea queue.** Human ideas and AI ideas compete equally. FIFO scheduling.
4. **Winners auto-merge.** Any config that beats current best gets merged to a feature branch. Admin (Vuk) merges to main.
5. **Everything is recorded.** Every experiment, win or lose, feeds the knowledge base.

---

## Architecture

### MVP (Now)

```
auto-research/
├── bot/              # Discord bot — primary user interface
├── api/              # FastAPI — auth, experiment dispatch, results
├── engine/           # Research engine — idea→config, queue, knowledge, AI agents
├── infra/            # GPU orchestration, SSH, scheduling
└── web/              # Minimal dashboard (later)

parameter-golf/       # Research template (the experiment codebase)
├── train_gpt.py      # Training script
├── infra/            # Experiment runners, tiered screening
└── results/          # All results by stage
```

### Discord Bot (MVP interface)

- DM support, no @mention needed
- User describes idea → bot queues experiment → runs it → returns results
- `/stop` to cancel running experiment
- Results as a formatted table (designed to screenshot and share on social media)
- Bot adds brief insight: idea was bad / near baseline (worth investigating) / winner
- 5 message limit per session
- Access gating: paid Skool members only

### Backend (FastAPI)

- **Auth**: Discord OAuth + Skool membership verification
- **Chat API**: LLM-powered experiment builder
- **Experiment API**: Submit, monitor, cancel
- **Results API**: Query, compare, export
- **Billing**: Stripe — experiment credits per plan

### GPU Fleet

- Workers connect via SSH through proxy
- One experiment per GPU, FIFO queue
- Auto-discovery of available GPUs
- Cost tracking per user
- Scheduler daemon pulls from queue, assigns to idle GPUs

### Idea Quality Control

MVP: ideas go straight to queue, no scoring gate. At $0.05/experiment the cost of a bad idea is negligible.

**Future (not MVP):** Debating agents — advocate/skeptic/judge panel scores ideas 1-10 before queuing. Checks: has this been tried? Does it contradict known failures? Is it testable? Expected impact? Score ≥5 → queue, <5 → rejected with explanation. Design this when bad ideas start wasting meaningful time or queue space.

---

## Knowledge Architecture

### The Problem with Current Design

KNOWLEDGE.md currently mixes three things that should be separate:

1. **Findings** — what worked, what failed (relu² beats relu, conv is dead)
2. **Methodology** — how the system works (tiered elimination, pipeline stages)
3. **State** — current best config, open questions, in-progress runs

These serve different audiences and change at different rates.

### Proposed Structure

```
research-template/
├── KNOWLEDGE.md          # Findings only — proven facts, failed approaches
│                         # Structured as claims with evidence
│                         # Machine-readable for AI agents
│
├── METHODOLOGY.md        # How the research system works
│                         # Tiered elimination rules
│                         # Pipeline stages and gate criteria
│                         # This rarely changes
│
├── STATE.md              # Current best config, open questions
│                         # What's running now, what's next
│                         # Updated constantly, ephemeral
│
├── FORBIDDEN.md          # Hard rules — things that must never be tested
│
└── findings/             # One file per major finding
    ├── activation_squaring.md
    ├── moe_scaling.md
    ├── untied_embeddings.md
    └── ...
```

### KNOWLEDGE.md redesign

Each entry should be a structured claim:

```markdown
## Proven: Squaring activations is the most impactful design choice

- **Effect**: +0.08-0.11 BPB penalty without squaring
- **Evidence**: 60+ runs, 500-13000 steps
- **Mechanism**: Quadratic shape matters, not just scale (2·relu ≠ relu²)
- **Confidence**: High (replicated across seeds, step counts, architectures)
- **Implications**: Any new activation must preserve squaring
```

vs failed approaches:

```markdown
## Failed: Depthwise convolution

- **Effect**: +0.025 to +0.174 BPB (always hurts)
- **Evidence**: All kernel sizes tested, combos tested
- **Why it fails**: Unknown — possibly kills gradient flow at this scale
- **Retry if**: Someone shows conv working at <20M params with a specific technique
```

This structure lets AI agents query: "has X been tried?" → grep for it. "What works?" → scan Proven entries. "What should I avoid?" → scan Failed entries + FORBIDDEN.md.

### STATE.md (new — replaces bottom of current KNOWLEDGE.md)

```markdown
# Current State

## Best Config
[current best architecture + BPB + submission size]

## In Progress
[what's running on which GPUs]

## Open Questions
[what we don't know yet]

## Next Up
[what's queued]
```

This file changes constantly and is not knowledge — it's operational state.

---

## Revenue Model

**No free tier.** Open source is the free tier — clone it and run it yourself.

| Plan | Price | Experiments/mo | What You Get |
|------|------:|---------------:|-------------|
| Basic | $9/mo | 40 | Discord bot access, 40 full experiments, results history |
| Pro | $49/mo | 200 | Everything in Basic, priority queue, export results, API access |

One "experiment" = one idea through the full pipeline (10×100 + 5×300 + 2×500 steps, ~10 min on GPU). User never thinks about steps or configs.

Additional:
- **Bring your own GPU**: Users provide SSH creds, we orchestrate (free compute for us)
- **Bring your own API key**: Users provide LLM key for chat (free LLM cost for us)

---

## Open Source Strategy

Everything is open source (MIT or Apache 2.0). Self-hosters clone the repo, set up their own GPUs, run everything themselves. We provide:
- GitHub repo with full code
- Setup docs
- No support (GitHub issues only)

**Why this works**: open source drives adoption and trust. Paid users pay for convenience (1-click, no GPU setup, no maintenance). The software is free. The service is paid.

---

## Phases

### Phase 1: MVP (NOW)

- Discord bot as primary interface (already working)
- Parameter-golf as only research template
- 2-4 cheap GPUs
- Skool community as paying beta testers
- Experiment = screen(100) → explore(300) → validate(500) pipeline
- Stripe billing, experiment credits
- Knowledge base: restructured KNOWLEDGE.md + STATE.md
- **Goal**: Skool members running experiments weekly, sharing results

### Phase 2: Platform (3-6 months)

- Web dashboard (live fleet, results explorer, experiment history)
- User-provided GPU support (paste SSH creds)
- Automated scientist v1 (arxiv scanning, GitHub monitoring, idea remixing)
- Public API for programmatic access
- Multiple research templates
- Open source launch
- **Goal**: Non-Skool users start self-hosting and paying

### Phase 3: Scale (6-12 months)

- Managed GPU fleet (rent and resell compute)
- Team accounts (shared queues, private results)
- Template marketplace
- Enterprise features (SLA, dedicated GPUs)
- **Goal**: Default tool for small-model research

---

## Immediate Next Steps

1. ~~Discord bot with DM support, image rendering, access gating~~ Done
2. ~~Elimination bracket with proper stage scaling~~ Done
3. ~~Training interrupt capability~~ Done
4. ~~Message limit with counter~~ Done
5. Restructure knowledge system (KNOWLEDGE.md → findings-only, add STATE.md, add METHODOLOGY.md)
6. Implement experiment packaging (1 experiment = screen→explore→validate pipeline)
7. Stripe integration for experiment credits
8. Open source prep — clean up, docs, license, README

---

## Resolved Questions

| Question | Decision |
|----------|----------|
| Evaluation scope | Parameter-golf only for now |
| GPU scheduling | FIFO first |
| Idea quality | Debating agents (advocate + skeptic + judge), no community voting |
| Feature branch workflow | Auto-merge when improvement > threshold, admin merges to main |
| Multi-GPU training | No, single-GPU only |
| Governance | Admin (Vuk) only |
| Free tier | No. Open source = free tier. All hosted usage is paid |
| Website | MVP later. Discord bot is the product for now |
