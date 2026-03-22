# Auto-Research Startup Plan

## Goal

Accelerate open source AI research and democratize GPU access as much as possible.

The startup should help people do real AI research without needing a lab, a big team, or a closed platform.

## Product Thesis

Build an automation-first research platform where users can:

- run open research workflows
- use AI agents instead of human operators
- bring their own API keys
- bring their own GPUs over SSH
- use platform GPUs if they want convenience
- get automated planning, execution, analysis, and iteration

`auto-research` is the product control plane.

`parameter-golf` is the first research template.

## Non-Negotiables

1. Open source
2. Automation
3. Users should interact mainly with AIs, not humans.
4. Do not overbuild enterprise features before the core loop works.

---

## Pricing

| Tier | Price | Quick screens | Explore (500 steps) | Validate (3k steps) | Full (13k steps) |
|------|-------|--------------|---------------------|---------------------|------------------|
| Starter | $9/mo | 100 | 20 | 6 | 2 |
| Lab | $49/mo | unlimited | 150 | 50 | 15 |

---

## Ideas Backlog

### Discord Bot
- Add a Discord bot as a second interface alongside the web UI
- Users interact in a channel or DM: same chat loop, same actions, same experiment results
- Bot posts results as embeds or markdown blocks
- Pros: zero friction to try, lives where communities already are, viral sharing of results
- Cons: no streaming, markdown rendering limited, auth flow is awkward for paid tiers
- Implementation: `discord.py` bot that calls the existing `/api/chat/` endpoint, same backend

### User-Provided OpenRouter API Keys
- Let users bring their own OpenRouter API key for the LLM calls
- Store it encrypted in the DB, use it instead of the platform key
- Benefit: platform LLM cost goes to zero for that user; user gets unlimited chat
- Could be a perk for Lab tier or a standalone free tier

### User-Provided GPUs via Google Colab
- Let users paste a Colab notebook URL or run a provided notebook that exposes an SSH tunnel or ngrok endpoint
- Platform SSHes to their Colab GPU instead of a fleet GPU
- Benefit: runs cost $0 for the platform, democratizes access
- Cons: Colab kills sessions after ~12 hours, flaky for full runs; fine for quick screens