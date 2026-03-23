# Auto-Research — Startup Plan

## One-Liner

**Fully automated AI research platform. Ideas go in, validated improvements come out. No humans in the loop.**

goal: every company, frontier lab, phd studen and individual using this open source (self maintanance) or paid (1 click) version to accelerate humanity

---

## Vision

Build the world's best open-source automated AI research platform. Every company — OpenAI, Anthropic, DeepSeek, Moonshot, Microsoft, NVIDIA — should want to use this. We achieve that by being open source and making it genuinely the best tool for the job.

The core insight: most ML research is repetitive grunt work — generating ideas, running experiments, analyzing results, iterating. Humans are slow at this. An automated system can run 100x more experiments, 24/7, with perfect record-keeping. **The bottleneck in AI research is not compute — it's the speed of the human loop.**

We remove that bottleneck.

### What We Believe

- If you can't evaluate it, you can't auto-research it. **Measurable metrics are the prerequisite.**
- Small models are the perfect testbed — fast iteration, cheap experiments, results in minutes not days.
- The best ideas come from everywhere — arxiv papers, GitHub repos, random Discord users, and AI itself.
- Open source wins. The community will contribute ideas faster than any closed team.
- Money covers costs. The mission is impact, not margins.

---

## How It Works

### The Automated Research Loop Example

```
┌─────────────────────────────────────────────────┐
│                  IDEA SOURCES                    │
│                                                  │
│  🤖 Automated Scientist    👤 Human Researchers  │
│  (arxiv, github, remixes)  (Discord, web UI)     │
│                                                  │
└───────────────┬─────────────────┬───────────────┘
                │                 │
                ▼                 ▼
        ┌───────────────────────────────┐
        │        UNIFIED IDEA QUEUE      │
        │  Priority-ranked, deduplicated │
        │  Novelty-scored, tagged        │
        └───────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │          WORKERS              │
        │  GPU fleet pulls from queue   │
        │  Multi-stage elimination:     │
        │                               │
        │  Stage 1: 10 configs, 3 steps │
        │  Stage 2: top 5, 5 steps      │
        │  Stage 3: top 2, 7 steps      │
        │  Validate: 500-2000 steps     │
        │  Full run: 13000 steps        │
        │                               │
        └───────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │      RESULTS & KNOWLEDGE      │
        │  Winners → feature branch     │
        │  Losers → knowledge base      │
        │  Everything → analysis DB     │
        └───────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │      HUMAN OVERSIGHT          │
        │  Monitor feature branch       │
        │  Merge to main when ready     │
        │  Review automated decisions   │
        └───────────────────────────────┘
```

### Key Principles

1. **100% automate small-model research** — The system should run indefinitely without human intervention. Humans contribute ideas, but never block the pipeline.

2. **Remove researchers from the loop** — Researchers can submit ideas, but they should not be required to prompt, monitor, or interpret results. The system does all of that.

3. **Single unified idea queue** — Human ideas and AI-generated ideas compete on equal footing. Priority is based on novelty, expected impact, and cost.

4. **Workers pull and execute** — GPUs are workers. They pull the next item from the queue, run the multi-stage elimination, report results, and pull again. One experiment at a time per GPU.

5. **Winners go to feature branches** — Any config that beats the current best gets automatically committed to a feature branch with full provenance (what was tested, what it beat, by how much).

6. **Humans merge when ready** — The only human-required step is reviewing feature branches and merging to main. Everything else is automated.

7. **Can't evaluate = can't auto-research** — The system only works when there's a clear, measurable metric (like val_bpb). This is the fundamental constraint.

---

## The Automated Scientist

The AI agent that generates new ideas. It draws from:

### Input Sources
- **arxiv papers** — Scan new papers daily for applicable techniques. Extract the core idea, translate it into a testable config.
- **GitHub repos** — Monitor trending ML repos. When someone publishes a new activation function, normalization trick, or architecture variant, auto-generate an experiment.
- **Knowledge base** — The system's own history. What worked? What didn't? What combinations haven't been tried? The automated scientist remixes past successes.
- **Community ideas** — Ideas from Discord users, Skool members, web UI users. These go into the same queue.

### How Ideas Become Experiments
1. AI agent reads a paper/repo/discussion
2. Extracts the core testable hypothesis
3. Translates it into 8-10 config variants (diverse bracket)
4. Scores it for novelty (has this been tried before?) and expected impact
5. Submits to the unified queue
6. Workers pick it up when a GPU is free

### The Knowledge Loop
Every experiment result feeds back into the knowledge base. The automated scientist uses this to:
- Avoid re-testing things that already failed
- Combine successful techniques in new ways
- Identify unexplored regions of the design space
- Learn which types of changes tend to help (e.g., "squared activations consistently beat linear ones")

---

## Architecture

### Components

```
auto-research/
├── api/              # FastAPI backend — auth, chat, experiment dispatch
├── bot/              # Discord bot — user-facing interface
├── web/              # Next.js frontend — dashboard, results, analytics
├── engine/           # Research engine — idea generation, queue management
├── agents/           # AI agents — scientist, analyst, optimizer
└── infra/            # GPU orchestration, SSH, monitoring

parameter-golf/       # Research template (first use case)
├── train_gpt.py      # Training script
├── infra/            # Experiment runners, tiered screening
├── screens/          # Screen configs
├── queues/           # Experiment queues
└── results/          # All results, organized by stage
```

### Backend (FastAPI)
- **Auth**: Magic link login, API keys, Discord OAuth
- **Chat API**: LLM-powered experiment builder with action blocks
- **Experiment API**: Submit, monitor, cancel experiments
- **Queue API**: View/manage the unified idea queue
- **Results API**: Query results, comparisons, analytics
- **User tiers**: Free (preview, 5 messages), Starter ($9/mo), Lab ($49/mo), Admin

### Frontend (Next.js)
- **Dashboard**: Live fleet status, experiment progress, cost tracking
- **Experiment builder**: Chat UI (same as Discord bot, but richer)
- **Results explorer**: Interactive tables, charts, comparisons
- **Queue viewer**: See what's coming up, submit ideas, vote
- **Knowledge base**: Searchable history of all experiments and findings

### Discord Bot
- Same capabilities as web UI
- DM support (no @mention needed)
- 5-message preview per conversation
- `/stop` to interrupt training
- Results rendered as images for clean formatting
- Access gating for non-Skool members

### GPU Fleet
- Workers connect via SSH through proxy
- One experiment at a time per GPU
- Auto-discovery of available GPUs
- Cost tracking and budget limits
- Scheduler daemon watches queue, assigns work to idle GPUs

---

## Scaling Plan

### Phase 1: Proof of Concept (NOW)
- Single research template (parameter-golf)
- 1-4 GPUs (H100s)
- Discord bot + basic web UI
- Manual idea queue + basic AI scientist
- Skool community as beta testers
- **Goal**: Demonstrate the loop works end-to-end

### Phase 2: Platform (3-6 months)
- Multi-template support (different research challenges)
- User-provided GPUs (SSH credentials or Colab tunnels)
- Full web dashboard
- Automated scientist v2 (arxiv scanning, GitHub monitoring)
- Public API for programmatic access
- Open source launch
- **Goal**: Other teams start using it for their own research

### Phase 3: Scale (6-12 months)
- Managed GPU fleet (rent and resell compute)
- Enterprise accounts (teams, shared queues, private results)
- Marketplace for research templates
- Plugin system for custom evaluation metrics
- Integration with MLflow, W&B, etc.
- **Goal**: Become the default tool for small-model research

### Phase 4: Generalize (12+ months)
- Support any ML training pipeline, not just small LMs
- Distributed training support
- AutoML-style search over full hyperparameter spaces
- Federated research (multiple orgs share anonymized findings)
- **Goal**: Every company uses this for automated ML research

---

## Revenue Model

**Goal: Cover costs, not maximize profit.** This is an open-source-first company.

| Tier | Price | What You Get |
|------|-------|-------------|
| Free (Preview) | $0 | 5 messages/conversation, community queue, view results |
| Starter | $9/mo | 100 screens, 20 explore runs, 6 validate, 2 full |
| Lab | $49/mo | Unlimited screens, 150 explore, 50 validate, 15 full |
| Team | $199/mo | Shared queue, private results, priority GPU access |
| Enterprise | Custom | Dedicated GPUs, custom templates, SLA |

Additional revenue:
- **Bring your own GPU**: Users provide compute, we provide orchestration (free for us)
- **Bring your own API key**: Users provide LLM API key for chat (free for us)
- **Managed compute**: Mark up GPU rental for convenience

---

## Open Source Strategy

### What's Open Source
- Everything. The entire platform, all agents, all templates, all infrastructure code.
- MIT or Apache 2.0 license.

### Why Open Source Works For Us
1. **Contributions**: The community generates ideas, finds bugs, adds features faster than we ever could.
2. **Trust**: Companies won't use a closed-source tool to run their research.
3. **Adoption**: Zero friction to try. Clone it, run it, see if it works.
4. **Network effects**: More users → more experiment data → better automated scientist → more users.

### How We Still Make Money
- **Hosted version**: We run the servers, manage the GPUs, handle auth. Pay for convenience.
- **Managed compute**: GPU access without SSH setup.
- **Support & SLA**: Enterprise customers need guarantees.
- The software is free. The service is paid.

---

## Research Organization as Markdown

A research organization is a set of markdown files that define all the rules and how everything connects:

```
KNOWLEDGE.md      — What we know: proven facts, failed approaches, open questions
PIPELINE.md       — The research loop: stages, gate criteria, promotion rules
FORBIDDEN.md      — What not to do (e.g., no LR-only tuning)
CLAUDE.md         — How the AI assistant should behave in this repo
queues/active.txt — The current work queue
screens/*.py      — Screen configurations (what to test)
results/**/*.md   — Experiment results with full provenance
```

This is powerful because:
- It's version controlled (git history shows how thinking evolved)
- It's human-readable (anyone can understand the research state)
- It's machine-readable (AI agents parse and act on it)
- It's the single source of truth

---

## Where Improvements Come From

Based on our history, the biggest gains come from:

1. **Architecture changes** — New activation functions, attention variants, normalization tricks
2. **Combinations** — Taking two things that work individually and combining them
3. **Scaling patterns** — More layers vs wider layers, depth vs width tradeoffs
4. **Training dynamics** — Warmup/warmdown schedules, gradient handling
5. **Stolen ideas** — Techniques from papers applied to our specific setting

The automated scientist should do more of what works: scan for new architecture papers, generate combination experiments, and explore the interaction space between proven techniques.

---

## Immediate Next Steps

1. ~~Discord bot with DM support, image rendering, access gating~~ ✅
2. ~~Elimination bracket (10→5→2) with proper stage scaling~~ ✅
3. ~~Training interrupt capability~~ ✅
4. ~~5-message conversation limit with counter~~ ✅
5. Web dashboard (Next.js) — live fleet view, results explorer
6. Automated scientist v1 — arxiv RSS → idea extraction → queue submission
7. Queue API — unified queue with priority scoring
8. User-provided GPU support — paste SSH creds, we orchestrate
9. Open source prep — clean up, docs, license, launch README

---

## Questions to Resolve

- **Evaluation scope**: What other research challenges beyond parameter-golf? How do we generalize the evaluation? - let's focus on this one only for now
- **GPU scheduling**: FIFO queue or priority-based? Should paying users get priority? - fifo first
- **Idea quality**: How do we prevent the queue from filling with garbage ideas? Novelty scoring? Community voting? - no community voting, we will setup debating agents, think of architecture for this, how we would do it
- **Feature branch workflow**: Auto-merge if improvement > X%? Or always require human review? - have automerge as well.
- **Multi-GPU training**: Do we ever need data parallelism for the small models, or is single-GPU always enough? - no multigpu for now
- **Community governance**: Who decides what gets merged to main? Core team only, or contributor votes? - only me the admin

focus on building architecture, expand architecture, don't write redundand stuff, if there is redundancy in this file, delete it