# Parameter Golf + Auto-Research Integration Plan

**Last Updated:** 2026-03-22
**Status:** Phase 2 (Web UI consolidation + research framework) complete; Phase 3 (specs & micro-lane) in progress

---

## Project Vision

Build a **rigorous micro-research platform** that combines:
1. **Fast 500-step exploration screening** on reduced-model "lanes" (nano, micro, full-width)
2. **Formal hypothesis testing** with pre-registered test plans to prevent p-hacking
3. **Publication-ready findings** backed by multi-seed validation
4. **Autonomous orchestration** via Claude skills (`/wave`, `/deploy`, `/collect`) for GPU fleet management
5. **Web UI** for visibility, queue control, and result comparison — without breaking the CLI-first workflow

**Single source of truth:** Git-controlled markdown files and JSON specs in parameter-golf, indexed into auto-research DB for fast queries.

---

## Architecture

### Two-Tier Research Pipeline

```
Curiosity / Idea
  │
  ├─→ [MICRO-LANE] 2-rung fast screen (nano 3L/128d, micro 5L/192d @ 500 steps)
  │      ├─ Cheap (&lt;$0.50/idea)
  │      ├─ Speed: 28min nano, ~60min micro per experiment
  │      ├─ Gate: Promotion policy (top-k + margin threshold)
  │      └─ Output: 4-8 ideas → Exploration stage
  │
  └─→ [EXPLORATION] Full-width 500-step screen (9L/384d @ 500 steps)
         ├─ Cost: ~$2/idea
         ├─ Speed: ~2 hrs per experiment
         ├─ Gate: >0.01 BPB improvement vs baseline
         ├─ Validation: Multi-seed (2 seeds × 2000-4000 steps)
         └─ Output: 1-2 winners → Hypothesis + Finding
              │
              └─→ [FULL RUN] 13780 steps for leaderboard submission
                    ├─ Cost: ~$12/seed pair
                    ├─ Gate: Beat 1.2244 BPB target
                    └─ Output: Publication-ready result

Wave Structure:
  Debate (agents) → Plan (markdown) → Approve (human) → Deploy (Claude skill) → Collect & Compare → X Post
```

### File Organization

```
parameter-golf/
├── train_gpt.py                    # THE competition training script (hard 1500-line limit)
├── infra/
│   ├── run_experiment.sh           # Entry point for all training
│   ├── gpu_creds.sh                # SSH credentials (auto-synced from DB)
│   ├── auto_research_adapter.py    # Subprocess bridge to auto-research
│   └── run_queue.sh                # Sequential queue runner
├── experiments/
│   └── specs/                      # Experiment definitions (JSON)
│       ├── TEMPLATE.json           # Schema + field documentation
│       ├── micro_wave0_*.json      # Calibration specs (16 total)
│       ├── rope_base_sweep_v1.json
│       ├── h001_squared_activation_repro_v1.json
│       └── ... (one spec per idea to test)
├── research/
│   ├── RESEARCH.md                 # Index: findings, hypotheses, explorations
│   ├── PIPELINE.md                 # Wave/debate structure & gates
│   ├── archive/                    # Old SAAS_PLAN, debate critiques (historical)
│   ├── findings/                   # Publication-ready micro-research
│   │   ├── F001_activation_design_rules.md
│   │   ├── F002_architecture_sweep.md
│   │   ├── F003_micro_lane_calibration.md
│   │   └── TEMPLATE.md
│   ├── hypotheses/                 # Pre-registered test plans
│   │   ├── H001_squared_activations.md
│   │   ├── H005_micro_surrogate_architecture.md
│   │   └── TEMPLATE.md
│   ├── explorations/               # Free-form 500-step probes
│   │   ├── 2026-03-22_rope_base_sweep.md
│   │   ├── 2026-03-22_head_count_sweep.md
│   │   ├── 2026-03-22_warmup_warmdown_sweep.md
│   │   └── TEMPLATE.md
│   ├── ideas/                      # Architecture brainstorm (Tier 1-3)
│   ├── papers/                     # Literature reviews
│   └── figures/                    # Plots & visualizations
├── queues/
│   ├── active.txt                  # Current queue (auto-synced to DB)
│   ├── micro_wave0_calibration.txt # Pre-wave 0 specs
│   ├── wave_30_plan.md             # Latest wave debate output
│   └── archive/                    # Old queues
├── results/
│   ├── explore/                    # ≤800 steps
│   ├── validate/                   # 801-5000 steps
│   ├── full/                       # &gt;5000 steps
│   ├── misc/
│   └── [individual result dirs with summary.json + metadata.json]
└── KNOWLEDGE.md                    # Persistent research memory (proven facts)

auto-research/
├── api/
│   ├── main.py                     # FastAPI entry point
│   ├── models.py                   # SQLAlchemy ORM (experiments, specs, gpus, users)
│   ├── config.py                   # Settings (tier limits, model URLs, paths)
│   ├── routers/
│   │   ├── auth.py                 # Login/API key
│   │   ├── experiments.py          # Submit, list, cancel experiments
│   │   ├── results.py              # View result JSON files
│   │   ├── chat.py                 # AI research assistant (Novita)
│   │   ├── research.py             # READ-ONLY research docs (read via adapter)
│   │   ├── specs.py                # READ-ONLY experiment specs (read via adapter)
│   │   ├── queues.py               # Queue file management
│   │   ├── fleet.py                # GPU management & SSH exec
│   │   ├── terminal.py             # WebSocket SSH terminal
│   │   └── admin.py                # Dashboard, user management
│   ├── adapters/
│   │   └── repo_adapter.py         # Subprocess bridge to parameter-golf/infra/auto_research_adapter.py
│   └── database.py                 # SQLite session + migrations
├── engine/
│   ├── scheduler.py                # Background: dispatch queued → idle GPUs every 30s
│   ├── collector.py                # Background: collect results from running exps every 60s
│   ├── sync.py                     # Bi-directional sync (specs, results, queue, creds)
│   ├── orchestrator.py             # Build SSH commands
│   └── templates.py                # Allowed parameter overrides per template
├── web/static/
│   └── index.html                  # Single-page app
│       ├── Chat tab                # AI research assistant
│       ├── Experiments tab         # Unified: stats + filter + sort + paginate
│       ├── Research tab            # READ-ONLY findings/hypotheses/explorations
│       ├── Deploy tab              # Queue editor + GPU status + wave plans
│       ├── Fleet tab (admin)       # GPU registration, status, SSH exec
│       ├── Terminals tab (admin)   # Multi-tab WebSocket SSH
│       └── Admin tab (admin)       # User management, dashboard
├── auto_research.db                # SQLite: users, experiments, specs, gpus, chat_messages
└── docker-compose.yml              # API + web deployment
```

---

## Data Models

### Experiment Spec (JSON, git-controlled)

```json
{
  "spec_id": "rope_base_sweep_v1",
  "name": "RoPE base frequency sweep",
  "spec_type": "exploration",
  "template": "parameter_golf",
  "stage": "explore",
  "lane": "micro_explore",
  "runner_profile": "micro_5L192",
  "baseline_spec_id": "micro_wave0_micro_baseline_v1",
  "steps": 500,
  "config_overrides": {
    "ROPE_BASE": "500"
  },
  "linked_docs": ["explorations/2026-03-22_rope_base_sweep.md"],
  "tags": ["rope", "position-embedding"],
  "notes": "Testing if lower ROPE_BASE helps short-sequence training",
  "promotion_policy": "top_k_plus_margin",
  "promotion_margin_bpb": 0.01,
  "promotion_max": 2,
  "desired_state": "queued",
  "content_hash": "sha256_of_payload",
  "source_path": "/root/parameter-golf/experiments/specs/rope_base_sweep_v1.json"
}
```

### Research Document (Markdown, git-controlled)

**Exploration Template:**
- Question, Setup, Raw Results, Observations, Next Steps
- Links to: spec_id, hypothesis it might spawn, why killed (if dead)

**Hypothesis Template:**
- Hypothesis, Prior Evidence, Pre-registered Test Plan (locked before results)
- Test plan includes: baseline config, treatment config, steps, seeds, success/kill criteria
- Results table with raw numbers and deltas
- Caveats + reproducibility commands

**Finding Template:**
- TL;DR, Key Result, Background, Method, Results (by hypothesis)
- Discussion + caveats, Effect sizes vs noise floor
- Reproducibility (exact configs, git commit, hardware, how to rerun)

---

## Workflow: Exploration → Hypothesis → Finding

### 1. Exploration (Free-Form)
- **Trigger:** Curiosity about an architecture idea or hyperparameter
- **How:** Create `research/explorations/{date}_{idea}.md`, set status=ACTIVE
- **Experiments:** Run 500-step probes on a few ideas using micro-lane or full-width explore
- **Gate:** If pattern emerges, propose hypothesis; if all noise, mark complete
- **Cost:** ~$0.50 (micro) or ~$2 (full-width) per idea

### 2. Hypothesis (Formal)
- **Trigger:** Promising exploration result worth rigorously testing
- **How:** Create `research/hypotheses/H{NNN}_{claim}.md`
- **Test Plan:** Write BEFORE running experiments (prevents p-hacking)
  - Exact baseline config
  - Exact treatment config (only one variable changes)
  - Steps required (minimum to see effect)
  - Seeds and success criterion (e.g., ">0.005 BPB on 2+ seeds")
- **Create specs:** Define as JSON experiments in `experiments/specs/`
- **Run:** Multi-seed validation at 2000-4000 steps
- **Gate:** Confirmed (effect survives multi-seed) / Falsified / Inconclusive
- **Cost:** ~$4-8 per hypothesis (2 seeds × 2000-4000 steps)

### 3. Finding (Publication-Ready)
- **Trigger:** Hypothesis confirmed + effect size matters
- **How:** Create `research/findings/F{NNN}_{title}.md`
- **Content:** TL;DR, key result table, method, all evidence, discussion of what it means
- **Review:** Rigorous; caveats explicit; comparable to external work
- **Output:** Draft X/Twitter thread, blog post, or paper section
- **Reuse:** Reference in future waves, cite in KNOWLEDGE.md

---

## Gates & Quality Control

### Noise Floor
- Single GPU at 500 steps: noise ≈ ±0.003 BPB
- Single GPU at 2000 steps: noise ≈ ±0.002 BPB
- Threshold for "real effect": **≥0.005 BPB across 2+ independent seeds**

### Exploration → Validate Gate
- Result: ≥0.01 BPB improvement at 500 steps vs baseline
- If <0.005: mark "promising but noisy" and collect more seeds

### Validate → Full Gate
- Improvement ≥0.005 BPB holds across 2 seeds at 2000-4000 steps
- Effect size reproducible (not seed-specific fluke)

### Publication Gate
- Finding backed by ≥1 confirmed hypothesis
- Effect sizes reported relative to noise floor
- Caveats explicit (e.g., "only tested at 9L/384d scale")
- Comparable to prior work or new if novel

---

## Spec Lifecycle

1. **Author** — Write JSON spec in `experiments/specs/`, link to hypothesis/exploration in `linked_docs`
2. **Index** — Auto-indexed into DB every 5 min via `sync_specs_to_db()`
3. **Queue** — Set `desired_state: "queued"` in JSON or add to `queues/active.txt` via web/CLI
4. **Schedule** — Scheduler picks up every 30s, assigns to idle GPU, runs
5. **Collect** — Collector polls every 60s, extracts results from `summary.json`, updates DB
6. **Compare** — `/compare` skill ranks results, `/post` drafts X thread
7. **Archive** — Old specs moved to `archive/` or marked `desired_state: "archived"`

---

## How Auto-Research Fits In

### What it Does
- **Web UI** for humans: Dashboard (stats), Experiments (filter/sort), Research (preview), Deploy (queue editor), Fleet (GPU status)
- **DB Index** for fast queries: 285 historical experiments, specs from disk
- **Background Tasks** for automation: Scheduler (dispatch), Collector (results), Sync (specs/results/creds/queue)
- **API** for integrations: `/experiments/`, `/specs/`, `/research/`, `/queues/`, `/fleet/`
- **Chat** AI research assistant for brainstorming ideas

### What it DOESN'T Do
- **Does not replace CLI workflow** — parameter-golf is the source of truth, DB is a cache
- **Does not own experiment definitions** — specs are in Git, not DB
- **Does not edit research docs** — those live in Git, viewed read-only in web
- **Does not control GPUs directly** — SSH via credentials stored in `infra/gpu_creds.sh` (synced from DB)

### Read-Only Research & Specs Routers
New design (post-user changes):
- `/research/` → read specs from `research/{explorations,hypotheses,findings}/*.md` via adapter
- `/specs/` → read experiment definitions from `experiments/specs/*.json` via adapter
- **No PUT/POST/DELETE** — return 405. Edits happen in Git or via `infra/auto_research_adapter.py`
- Web UI shows these as **read-only previews** (linked docs, promotion policies, desired_state)

---

## Current Status

### Completed
✅ Phase 1: Delete dead code (competitions, agents, webhooks, stale files)
✅ Phase 2: Consolidate tabs (Dashboard + Experiments + Results → single Experiments tab with stats + filter/sort/paginate)
✅ Phase 3: Add Deploy tab (queue editor + GPU status cards + kill buttons)
✅ Phase 4: Create test explorations (rope_base_sweep, head_count_sweep, warmup_warmdown_sweep in explorations/)

### In Progress
🟡 **Web UI Research Tab**: Currently write-enabled but router returns 405. Need to:
   - Remove Save/Delete/Create buttons
   - Show as read-only preview (split view → full-width markdown)
   - Fix template endpoint (404 or static fallback)

🟡 **Specs UI Integration**: Deploy tab shows raw queue, should also show:
   - Spec list with linked hypothesis/finding
   - Desired state selector (draft/queued/paused/archived)
   - Promotion policy summary
   - Link to lane (micro vs full-width)

### Next Priority
1. **Fix research tab** (make read-only) — critical to prevent 405 errors
2. **Integrate specs into Deploy tab** — show spec name, linked docs, desired_state
3. **Run micro_wave0 calibration** — validate the 2-rung screening against known controls
4. **Document promotion policies** — clarify how "top_k + margin" selects winners
5. **Add `/post` skill** for automatic X thread drafting from findings

---

## Key Principles

1. **Git is the source of truth** — All research docs, specs, queues are version-controlled
2. **DB is a cache** — Synced every 5 min, rebuilds from Git if lost
3. **CLI-first, web-second** — Parameter-golf works standalone; auto-research adds visibility
4. **Pre-registered hypotheses** — Test plans locked before results to prevent p-hacking
5. **Effect size discipline** — Report vs noise floor; explicit caveats on what doesn't generalize
6. **Multi-seed validation** — 500-step ranking unreliable; 2+ seeds at 2000+ steps required
7. **Fast lane discipline** — Micro-lane is calibration only; must match full-width ranking to trust

---

## Commands for Common Tasks

### Create a new exploration
```bash
# Write to research/explorations/2026-03-22_idea_name.md
# Set status: ACTIVE, leave experiments: []
# Web UI: Experiments tab → + New Research doc (auto-fills template)
```

### Propose a hypothesis
```bash
# Write to research/hypotheses/H{NNN}_claim.md
# Lock test plan BEFORE experiments
# Create 1+ specs in experiments/specs/ linking this hypothesis
```

### Queue experiments
```bash
# Add to queues/active.txt or web UI Deploy tab → paste specs
# OR set desired_state: "queued" in specs/*.json
# Scheduler picks up every 30s
```

### Check results
```bash
/compare <spec1_slug> <spec2_slug>
# Ranked by val_bpb, shows delta vs baseline
```

### Publish a finding
```bash
# Write to research/findings/F{NNN}_title.md
# Link to hypotheses: [H001, H002]
# Run /post to draft X thread
```

---

## Budget & Timeline

| Phase | Duration | Cost | Output |
|-------|----------|------|--------|
| Micro-lane calibration (Wave 0) | 3-4 hrs | $8-10 | Validation of screening efficacy |
| Explore wave (4-6 ideas) | 6-12 hrs | $2-4/idea | Winners for validation |
| Validate (2-3 seeds × 2-4k steps) | 6-12 hrs | $4-8/idea | Confirmed hypotheses |
| Full run (2 seeds × 13.8k) | 24-30 hrs | $12/pair | Leaderboard submission |

**Total budget:** $40 (hard cap across all phases)

---

## Success Metrics

1. **Research rigor**: ≥80% of findings backed by pre-registered hypotheses
2. **Publication quality**: Each finding ≥3 hypotheses, explicit caveats, effect sizes vs noise floor
3. **Micro-lane accuracy**: Top-k recall ≥2/3 (ideas that win at micro also win full-width)
4. **Training efficiency**: Micro baseline ≥2x speedup vs full-width at 500 steps
5. **Leaderboard**: Beat 1.2244 BPB target (current best: 1.2475 BPB @ 4000 steps)
6. **Social reach**: Each finding drafted as X thread, shared with research community
