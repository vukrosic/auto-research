#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# Multi-Agent Research Debate (Mixed models via Novita)
# ═══════════════════════════════════════════════════════════════════════
# Three debate types with different agent combinations:
#   direction — Architect + Explorer + Skeptic (new ideas)
#   scale     — Architect + Challenger + Optimizer (validate/full decisions)
#   pivot     — All 5 agents (strategic reassessment)
#
# Usage:
#   bash debate/debate.sh                              # direction debate, 3 rounds
#   bash debate/debate.sh "MoE budget" 3               # focused topic
#   bash debate/debate.sh "activation funcs" 3 scale   # scale debate
#   bash debate/debate.sh "are we stuck?" 3 pivot      # pivot debate
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"
source debate/creds.sh

TOPIC="${1:-Review all recent experiments and propose the next batch}"
ROUNDS="${2:-3}"
DEBATE_TYPE="${3:-direction}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT_DIR="debate/rounds/$TIMESTAMP"
PROMPT_DIR="$OUT_DIR/prompts"
mkdir -p "$OUT_DIR" "$PROMPT_DIR"

# Base Novita config
export ANTHROPIC_BASE_URL="$NOVITA_BASE_URL"
export ANTHROPIC_AUTH_TOKEN="$NOVITA_KEY"

# ─── Select agents based on debate type ─────────────────────────────

declare -a AGENTS=()
declare -A AGENT_MODELS=()
declare -A AGENT_PERSONAS=()

case "$DEBATE_TYPE" in
    direction)
        AGENTS=(architect explorer skeptic)
        AGENT_MODELS[architect]="$MODEL_ARCHITECT"
        AGENT_MODELS[explorer]="$MODEL_EXPLORER"
        AGENT_MODELS[skeptic]="$MODEL_SKEPTIC"
        AGENT_PERSONAS[architect]="debate/personas/architect.md"
        AGENT_PERSONAS[explorer]="debate/personas/explorer.md"
        AGENT_PERSONAS[skeptic]="debate/personas/skeptic.md"
        ;;
    scale)
        AGENTS=(architect challenger optimizer)
        AGENT_MODELS[architect]="$MODEL_ARCHITECT"
        AGENT_MODELS[challenger]="${MODEL_CHALLENGER:-$DEBATE_MODEL}"
        AGENT_MODELS[optimizer]="${MODEL_OPTIMIZER:-$DEBATE_MODEL}"
        AGENT_PERSONAS[architect]="debate/personas/architect.md"
        AGENT_PERSONAS[challenger]="debate/personas/challenger.md"
        AGENT_PERSONAS[optimizer]="debate/personas/optimizer.md"
        ;;
    pivot)
        AGENTS=(architect skeptic explorer challenger optimizer)
        AGENT_MODELS[architect]="$MODEL_ARCHITECT"
        AGENT_MODELS[skeptic]="$MODEL_SKEPTIC"
        AGENT_MODELS[explorer]="$MODEL_EXPLORER"
        AGENT_MODELS[challenger]="${MODEL_CHALLENGER:-$DEBATE_MODEL}"
        AGENT_MODELS[optimizer]="${MODEL_OPTIMIZER:-$DEBATE_MODEL}"
        AGENT_PERSONAS[architect]="debate/personas/architect.md"
        AGENT_PERSONAS[skeptic]="debate/personas/skeptic.md"
        AGENT_PERSONAS[explorer]="debate/personas/explorer.md"
        AGENT_PERSONAS[challenger]="debate/personas/challenger.md"
        AGENT_PERSONAS[optimizer]="debate/personas/optimizer.md"
        ;;
    *)
        echo "Unknown debate type: $DEBATE_TYPE (use: direction, scale, pivot)"
        exit 1
        ;;
esac

AGENT_COUNT=${#AGENTS[@]}

# ─── Display ────────────────────────────────────────────────────────

echo "╔═══════════════════════════════════════════════╗"
echo "║         MULTI-AGENT RESEARCH DEBATE           ║"
echo "╠═══════════════════════════════════════════════╣"
echo "║ Type:   $DEBATE_TYPE"
echo "║ Topic:  $(echo "$TOPIC" | head -c 43)"
echo "║ Rounds: $ROUNDS"
echo "║ Output: $OUT_DIR/"
echo "║                                               ║"
echo "║ Agents:                                       ║"
for agent in "${AGENTS[@]}"; do
    printf "║   %-12s — %s\n" "$(echo "$agent" | sed 's/./\U&/')" "${AGENT_MODELS[$agent]}"
done
echo "╚═══════════════════════════════════════════════╝"
echo ""

# ─── Load debate type instructions ──────────────────────────────────

DEBATE_TYPE_INSTRUCTIONS=""
if [ -f "debate/types/${DEBATE_TYPE}.md" ]; then
    DEBATE_TYPE_INSTRUCTIONS=$(cat "debate/types/${DEBATE_TYPE}.md")
fi

# ─── Build context snapshot ─────────────────────────────────────────

KNOWLEDGE=$(cat KNOWLEDGE.md 2>/dev/null | head -300 || echo "(KNOWLEDGE.md not found)")
QUEUE=$(cat queues/active.txt 2>/dev/null || echo "(no active queue)")
CONCLUSIONS=$(tail -80 debate/CONCLUSIONS.md 2>/dev/null || echo "(no previous debates)")

RESULTS=""
for f in $(ls -t results/*/summary.txt results/*/summary.json 2>/dev/null | head -10); do
    RESULTS+="── $(dirname "$f" | sed 's|results/||') ──
$(head -20 "$f")

"
done
[ -z "$RESULTS" ] && RESULTS="(no results found)"

CONTEXT="## Debate Type Instructions
$DEBATE_TYPE_INSTRUCTIONS

## Project Context
You are working on the Parameter Golf challenge: train the best 16MB language model in <10 min on 8xH100s. Scored by val_bpb (bits per byte, lower = better). Current leaderboard: 1.2244 BPB. Our best: 1.2498 BPB.

## Your Task
$TOPIC

## KNOWLEDGE.md (source of truth)
$KNOWLEDGE

## Latest Results
$RESULTS

## Current Queue
$QUEUE

## Previous Debate Conclusions
$CONCLUSIONS

## Rules
- NEVER propose something in KNOWLEDGE.md's Failed Approaches without explaining why this time is different
- All experiments must include exact env var configs for: infra/run_experiment.sh <name> <steps>
- Respect the 16 MB int8 zlib-compressed submission limit
- Noise floor at 500 steps is ~0.003 BPB. Do not claim significance below that.
- Name experiments in snake_case"

# ─── Helper: pipe prompt to claude with model override ──────────────

run_agent() {
    local prompt_file="$1"
    local output_file="$2"
    local model="${3:-$DEBATE_MODEL}"
    local err_file="${output_file%.md}.err"
    export ANTHROPIC_MODEL="$model"
    export ANTHROPIC_SMALL_FAST_MODEL="$model"
    cat "$prompt_file" | claude -p > "$output_file" 2>"$err_file"
}

# ═══════════════════════════════════════════════════════════════════════
# ROUND 1: Independent Reviews (parallel)
# ═══════════════════════════════════════════════════════════════════════

echo "━━━ ROUND 1: Independent Reviews ━━━"
echo ""

R1_SUFFIX="

$CONTEXT

This is Round 1 — your independent review. No other agents have spoken yet. Provide your full analysis following your output format."

# Write prompt files and launch agents
declare -a R1_PIDS=()
for agent in "${AGENTS[@]}"; do
    cat "${AGENT_PERSONAS[$agent]}" > "$PROMPT_DIR/r1_${agent}.txt"
    echo "$R1_SUFFIX" >> "$PROMPT_DIR/r1_${agent}.txt"

    echo "  Launching $(echo "$agent" | sed 's/./\U&/') (${AGENT_MODELS[$agent]})..."
    run_agent "$PROMPT_DIR/r1_${agent}.txt" "$OUT_DIR/r1_${agent}.md" "${AGENT_MODELS[$agent]}" &
    R1_PIDS+=($!)
done

echo ""
echo "  Waiting for Round 1..."
echo ""

# Progress display
while true; do
    all_done=true
    for pid in "${R1_PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            all_done=false
            break
        fi
    done
    $all_done && break

    line="  "
    for agent in "${AGENTS[@]}"; do
        local_n=$(wc -l < "$OUT_DIR/r1_${agent}.md" 2>/dev/null || echo 0)
        line+="$(echo "$agent" | sed 's/./\U&/'): ${local_n} lines | "
    done
    printf "\r%s" "${line%| }"
    sleep 10
done
echo ""

for i in "${!AGENTS[@]}"; do
    agent="${AGENTS[$i]}"
    wait "${R1_PIDS[$i]}" && echo "  ✓ $(echo "$agent" | sed 's/./\U&/') done ($(wc -l < "$OUT_DIR/r1_${agent}.md") lines)" || echo "  ✗ $(echo "$agent" | sed 's/./\U&/') failed (see $OUT_DIR/r1_${agent}.err)"
done

[ "$ROUNDS" -le 1 ] && { echo ""; echo "Single-round mode. Outputs in $OUT_DIR/"; exit 0; }

# ═══════════════════════════════════════════════════════════════════════
# ROUND 2: Cross-Examination (parallel)
# ═══════════════════════════════════════════════════════════════════════

echo ""
echo "━━━ ROUND 2: Cross-Examination ━━━"
echo ""

CROSS_INSTRUCTIONS="This is Round 2 — Cross-Examination. Below are the other agents' Round 1 reviews.

Your job:
1. Challenge: Pick the weakest claim from each other agent and explain why it is wrong or unsupported
2. Support: Pick the strongest claim from each other agent and add evidence for it
3. Revise: Update your top 3 experiment proposals based on what you have learned
4. Hill to die on: State your single biggest disagreement with the group"

declare -a R2_PIDS=()
for agent in "${AGENTS[@]}"; do
    {
        cat "${AGENT_PERSONAS[$agent]}"
        echo ""
        echo "$CROSS_INSTRUCTIONS"
        echo ""
        # Show all OTHER agents' round 1 output
        for other in "${AGENTS[@]}"; do
            [ "$other" = "$agent" ] && continue
            echo "══════════════════════════════════════"
            echo "Review by: THE $(echo "$other" | tr '[:lower:]' '[:upper:]')"
            echo "══════════════════════════════════════"
            cat "$OUT_DIR/r1_${other}.md" 2>/dev/null || echo "(output not available)"
            echo ""
        done
    } > "$PROMPT_DIR/r2_${agent}.txt"

    echo "  $(echo "$agent" | sed 's/./\U&/') responding (${AGENT_MODELS[$agent]})..."
    run_agent "$PROMPT_DIR/r2_${agent}.txt" "$OUT_DIR/r2_${agent}.md" "${AGENT_MODELS[$agent]}" &
    R2_PIDS+=($!)
done

echo ""
echo "  Waiting for Round 2..."
echo ""

while true; do
    all_done=true
    for pid in "${R2_PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            all_done=false
            break
        fi
    done
    $all_done && break

    line="  "
    for agent in "${AGENTS[@]}"; do
        local_n=$(wc -l < "$OUT_DIR/r2_${agent}.md" 2>/dev/null || echo 0)
        line+="$(echo "$agent" | sed 's/./\U&/'): ${local_n} lines | "
    done
    printf "\r%s" "${line%| }"
    sleep 10
done
echo ""

for i in "${!AGENTS[@]}"; do
    agent="${AGENTS[$i]}"
    wait "${R2_PIDS[$i]}" && echo "  ✓ $(echo "$agent" | sed 's/./\U&/') R2 done" || echo "  ✗ $(echo "$agent" | sed 's/./\U&/') R2 failed (see $OUT_DIR/r2_${agent}.err)"
done

[ "$ROUNDS" -le 2 ] && { echo ""; echo "Two-round mode. Outputs in $OUT_DIR/"; exit 0; }

# ═══════════════════════════════════════════════════════════════════════
# ROUND 3: Synthesis
# ═══════════════════════════════════════════════════════════════════════

echo ""
echo "━━━ ROUND 3: Synthesis ━━━"
echo ""

{
    echo "You are the Synthesis Agent. ${AGENT_COUNT} AI researchers debated over 2 rounds about the Parameter Golf challenge."
    echo "Debate type: ${DEBATE_TYPE}"
    echo ""
    echo "Produce the FINAL ACTIONABLE OUTPUT the human researcher will use."
    echo ""
    for ROUND in r1 r2; do
        for agent in "${AGENTS[@]}"; do
            F="$OUT_DIR/${ROUND}_${agent}.md"
            if [ -s "$F" ]; then
                echo "╔══════════════════════════════════════╗"
                echo "  ${ROUND^^}: THE $(echo "$agent" | tr '[:lower:]' '[:upper:]')"
                echo "╚══════════════════════════════════════╝"
                cat "$F"
                echo ""
            fi
        done
    done
    cat <<'SYNTH_FORMAT'

Output this exact structure:

## Consensus
What all agents agree on. High-confidence bets.

## Key Disputes
Unresolved disagreements. For each: what, who has stronger evidence, what experiment settles it.

## Experiment Queue (RANKED)
Top 5-8 experiments, ranked by expected impact / cost.

For EACH:
```bash
# <name> — <description>
# Hypothesis: <what we expect>
# Proposed by: <agent(s)>
# Risk: <what could go wrong>
ENV=val ENV2=val infra/run_experiment.sh name <steps>
```

## Do NOT Run
Rejected proposals and why.

## Strategic Assessment
One paragraph: position vs leaderboard, most promising path, biggest risk.
SYNTH_FORMAT
} > "$PROMPT_DIR/synthesis.txt"

echo "  Synthesizing ($MODEL_SYNTHESIS)..."
run_agent "$PROMPT_DIR/synthesis.txt" "$OUT_DIR/synthesis.md" "$MODEL_SYNTHESIS"
echo "  ✓ Synthesis done"

# ═══════════════════════════════════════════════════════════════════════
# Save metadata
# ═══════════════════════════════════════════════════════════════════════

cat > "$OUT_DIR/metadata.json" <<METAEOF
{
    "timestamp": "$TIMESTAMP",
    "topic": "$TOPIC",
    "debate_type": "$DEBATE_TYPE",
    "rounds": $ROUNDS,
    "agents": [$(printf '"%s",' "${AGENTS[@]}" | sed 's/,$//')],
    "models": {$(for a in "${AGENTS[@]}"; do printf '"%s":"%s",' "$a" "${AGENT_MODELS[$a]}"; done | sed 's/,$//')}
}
METAEOF

# ═══════════════════════════════════════════════════════════════════════
echo ""
echo "╔═══════════════════════════════════════════════╗"
echo "║              DEBATE COMPLETE                  ║"
echo "╠═══════════════════════════════════════════════╣"
printf "║   Type: %-37s ║\n" "$DEBATE_TYPE"
for F in "$OUT_DIR"/*.md; do
    SIZE=$(wc -l < "$F")
    NAME=$(basename "$F")
    printf "║   %-30s %4d lines  ║\n" "$NAME" "$SIZE"
done
echo "╚═══════════════════════════════════════════════╝"
echo ""
echo "━━━ SYNTHESIS ━━━"
echo ""
cat "$OUT_DIR/synthesis.md"

# Append to persistent conclusions log
{
    echo ""
    echo "---"
    echo ""
    echo "## $(date '+%Y-%m-%d %H:%M') — [$DEBATE_TYPE] $TOPIC"
    echo ""
    echo "**Type:** $DEBATE_TYPE | **Agents:** ${AGENTS[*]} | **Rounds:** $ROUNDS"
    echo "**Models:** $(for a in "${AGENTS[@]}"; do echo -n "$a=${AGENT_MODELS[$a]} "; done)"
    echo "**Full output:** $OUT_DIR/"
    echo ""
    cat "$OUT_DIR/synthesis.md"
    echo ""
} >> debate/CONCLUSIONS.md
echo ""
echo "Appended to debate/CONCLUSIONS.md"
