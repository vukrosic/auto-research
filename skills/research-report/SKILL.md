---
name: research-report
description: Use when asked to turn experiment results into an X post or short research report in vuk's automation-first style. Emphasize that automated AI research ran the experiments, that cheap small runs eliminate losers before scaling, keep all-lowercase, lead with experiment count plus model and hardware, include a markdown results table sorted by vs-baseline signal, then findings, next steps, and the standard CTA when the user wants a social post.
---

# Research Report

Use this skill for experiment-result writeups that should sound like the local `research-report` Claude command.

## Workflow

1. Read [references/original-claude-command.md](references/original-claude-command.md) when you need the exact framing, CTA, or reply block.
2. Extract the core facts first:
   - total experiment count
   - model and hardware
   - what was automated
   - baseline metric
   - best and worst outcomes
   - any reversals between cheap and expensive lanes
   - whether any runs are still in progress
3. Lead with automation:
   - automated ai research ran these
   - cheap small experiments were intentional so losers get eliminated before scale-up
4. Keep the voice tight:
   - all lowercase sentences
   - direct first person
   - no filler
   - no "i found that" or "we observed"
5. Default structure:
   - opener with `n experiments + model + hardware`
   - 1-2 lines on the automated system and why the small lane exists
   - markdown table sorted best to worst by vs-baseline result
   - 3-5 bullets on winners, reversals, and failures
   - 1-2 lines on what gets scaled next
6. If the user asks for a blog post instead of an X post:
   - keep the same opener, automation framing, and results table
   - expand the process and reversal sections
   - do not include the CTA unless the user explicitly wants the social version

## Output Rules

- bold the best and worst rows in the main table
- use `***`, `**`, `*`, or `n.s.` in the `signal` column
- if a result only survived a cheap screen and was not scaled, say that explicitly instead of pretending it is confirmed
- if timing mattered, include predicted vs actual runtime as part of the story
- if the hook is a reversal between cheap and expensive lanes, lead with that
