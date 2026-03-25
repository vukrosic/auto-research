#!/bin/bash
# Quick single-round review — all 3 personas in parallel, then synthesis
# Usage: bash debate/quick_review.sh ["optional prompt"]

set -euo pipefail
cd "$(dirname "$0")/.."
source debate/creds.sh

export ANTHROPIC_BASE_URL="$NOVITA_BASE_URL"
export ANTHROPIC_AUTH_TOKEN="$NOVITA_KEY"

PROMPT="${1:-Read KNOWLEDGE.md and the latest results. What are the 3 highest-value experiments to run next? Be specific with env var configs.}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT_DIR="debate/rounds/$TIMESTAMP"
PROMPT_DIR="$OUT_DIR/prompts"
mkdir -p "$OUT_DIR" "$PROMPT_DIR"

echo "=== Quick Review ==="
echo "  Architect: $MODEL_ARCHITECT"
echo "  Skeptic:   $MODEL_SKEPTIC"
echo "  Explorer:  $MODEL_EXPLORER"
echo "  Synthesis: $MODEL_SYNTHESIS"
echo ""

# Build context snapshot
KNOWLEDGE=$(cat KNOWLEDGE.md 2>/dev/null | head -300 || echo "(not found)")
QUEUE=$(cat queues/active.txt 2>/dev/null || echo "(no active queue)")
CONCLUSIONS=$(tail -80 debate/CONCLUSIONS.md 2>/dev/null || echo "(no previous debates)")
RESULTS=""
for f in $(ls -t results/*/summary.txt results/*/summary.json 2>/dev/null | head -10); do
    RESULTS+="── $(dirname "$f" | sed 's|results/||') ──
$(head -20 "$f")

"
done
[ -z "$RESULTS" ] && RESULTS="(no results found)"

TASK="$PROMPT

## KNOWLEDGE.md
$KNOWLEDGE

## Latest Results
$RESULTS

## Current Queue
$QUEUE

## Previous Debate Conclusions
$CONCLUSIONS

Follow your persona's output format."

# Write prompt files
for AGENT in architect skeptic explorer; do
    cat "debate/personas/${AGENT}.md" > "$PROMPT_DIR/${AGENT}.txt"
    echo "" >> "$PROMPT_DIR/${AGENT}.txt"
    echo "$TASK" >> "$PROMPT_DIR/${AGENT}.txt"
done

run_agent() {
    local prompt_file="$1"
    local output_file="$2"
    local model="${3:-$DEBATE_MODEL}"
    local err_file="${output_file%.md}.err"
    export ANTHROPIC_MODEL="$model"
    export ANTHROPIC_SMALL_FAST_MODEL="$model"
    cat "$prompt_file" | claude -p > "$output_file" 2>"$err_file"
}

echo "  Launching 3 agents..."
run_agent "$PROMPT_DIR/architect.txt" "$OUT_DIR/architect.md" "$MODEL_ARCHITECT" &
PID1=$!
run_agent "$PROMPT_DIR/skeptic.txt" "$OUT_DIR/skeptic.md" "$MODEL_SKEPTIC" &
PID2=$!
run_agent "$PROMPT_DIR/explorer.txt" "$OUT_DIR/explorer.md" "$MODEL_EXPLORER" &
PID3=$!

echo "  Waiting... (tail -f $OUT_DIR/*.md to watch live)"
while kill -0 $PID1 2>/dev/null || kill -0 $PID2 2>/dev/null || kill -0 $PID3 2>/dev/null; do
    ARCH_N=$(wc -l < "$OUT_DIR/architect.md" 2>/dev/null || echo 0)
    SKEP_N=$(wc -l < "$OUT_DIR/skeptic.md" 2>/dev/null || echo 0)
    EXPL_N=$(wc -l < "$OUT_DIR/explorer.md" 2>/dev/null || echo 0)
    printf "\r  Architect: %4s lines | Skeptic: %4s lines | Explorer: %4s lines" "$ARCH_N" "$SKEP_N" "$EXPL_N"
    sleep 10
done
echo ""

wait $PID1 && echo "  ✓ Architect" || echo "  ✗ Architect (see $OUT_DIR/architect.err)"
wait $PID2 && echo "  ✓ Skeptic" || echo "  ✗ Skeptic (see $OUT_DIR/skeptic.err)"
wait $PID3 && echo "  ✓ Explorer" || echo "  ✗ Explorer (see $OUT_DIR/explorer.err)"

# Synthesize
echo "  Synthesizing ($MODEL_SYNTHESIS)..."
{
    echo "Three agents with different perspectives reviewed: '$PROMPT'"
    echo ""
    for AGENT in architect skeptic explorer; do
        F="$OUT_DIR/${AGENT}.md"
        if [ -s "$F" ]; then
            echo "━━━ THE $(echo "$AGENT" | tr '[:lower:]' '[:upper:]') ━━━"
            cat "$F"
            echo ""
        fi
    done
    echo "Synthesize: agreements, disagreements, final ranked experiment list with exact env var configs."
} > "$PROMPT_DIR/synthesis.txt"

run_agent "$PROMPT_DIR/synthesis.txt" "$OUT_DIR/synthesis.md" "$MODEL_SYNTHESIS"

echo ""
cat "$OUT_DIR/synthesis.md"
echo ""
echo "Full outputs: $OUT_DIR/"

# Append to persistent conclusions log
{
    echo ""
    echo "---"
    echo ""
    echo "## $(date '+%Y-%m-%d %H:%M') — Quick Review"
    echo ""
    echo "**Prompt:** $PROMPT"
    echo ""
    echo "**Models:** Architect=$MODEL_ARCHITECT, Skeptic=$MODEL_SKEPTIC, Explorer=$MODEL_EXPLORER, Synthesis=$MODEL_SYNTHESIS"
    echo "**Full output:** $OUT_DIR/"
    echo ""
    cat "$OUT_DIR/synthesis.md"
    echo ""
} >> debate/CONCLUSIONS.md
echo "Appended to debate/CONCLUSIONS.md"
