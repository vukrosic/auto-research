# AI Research Service — Plan

## Value Proposition

An AI research copilot that knows what works and what doesn't. Members describe experiments in plain English, AI validates feasibility, runs tiered screens, and returns results. The AI has a memory of all past experiments (KNOWLEDGE.md) so it steers members away from dead ends and toward promising directions.

**What people pay for:** Access to an AI that can actually run ML experiments for them, tell them what's already been tried, and explain results — not just chat about theory.

## How It Works

1. AI suggests experiment categories to the member
2. Member describes what they want in chat: "try recursive layers" / "make MLP wider"
3. AI checks: already tried? fits size limit? too expensive? makes sense?
4. If viable → generates config → runs tiered screen (500 steps → eliminate bad ones → scale winners → full run)
5. Member gets report with results and plain-English explanation

## Tiers

| Tier | Price | What They Get |
|------|------:|---------------|
| Observer | $9/mo | Weekly research feed, vote on directions, results archive |
| Researcher | $49/mo | Chat with AI, 4 screens/mo, 1 validation run, name on findings |

## Costs & Margins

| Stage | Cost |
|-------|------|
| Tiered screen (local) | ~$0 |
| Explore 500 steps | ~$0.50 |
| Validate 2000-4000 steps | $2-8 |
| Full 13k steps | ~$12 |

Screens are free. Most member activity = screens. $49 member costs ~$2-4/mo in GPU.
**Margin: ~92-96% on Researcher tier, ~100% on Observer.**

10 Researchers = $490 revenue, ~$35 GPU cost, ~$455 profit.

## Architecture

**Chat layer:** Novita mimo-v2-flash ($0.10/M input, $0.30/M output — essentially free). Already built in auto-research/api/routers/chat.py. Handles member conversation, intent parsing, feasibility checks.

**Execution layer:** Chat backend calls `tiered_screen.py` directly via subprocess when member confirms an experiment. No Claude Code in the loop — it's too expensive for member requests. Claude Code stays as the operator tool (for Vuk only).

**Context injection:** System prompt gets KNOWLEDGE.md summary + current experiment status + member quota. The cheap model doesn't need to be smart — it just needs to know what's been tried and route to the right script.

**DB:** auto_research.db (SQLite, already exists). Tracks users, chat history, experiment runs, quotas.

## Flow

1. Member opens web chat, AI suggests experiment directions based on KNOWLEDGE.md
2. Member says "I want recursive layer experiments, make second layer recursive"
3. AI asks clarifying questions: how many layers recursive? what sharing pattern?
4. AI checks feasibility: param count, already tried?, cost tier
5. AI generates screen config, shows it to member for confirmation
6. On confirm → backend runs `python3 infra/tiered_screen.py --screen <generated_config>`
7. Results posted back to chat with plain-English explanation

## Why Not Claude Code in the Loop

- `claude -p` pipe mode works but costs ~$0.01-0.10 per invocation (Claude API credits)
- `tmux send-keys` to a Claude Code session is fragile and hard to parse output
- Direct subprocess to tiered_screen.py is free, reliable, and fast
- Claude Code is the power tool for Vuk's own research, not for member requests
