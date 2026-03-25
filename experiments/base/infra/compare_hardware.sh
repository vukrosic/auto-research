#!/bin/bash
# Compare val_bpb between a legacy reference run and H100 runs at matched step counts
# Usage: bash infra/compare_hardware.sh logs/reference_run.txt logs/h100_run.txt
#
# Extracts val_bpb at each logged step and computes:
#   - Side-by-side comparison
#   - Max absolute difference
#   - Whether ranking is preserved (for multi-config comparison)

set -e

REF_LOG=${1:?Usage: $0 <reference_log> <h100_log>}
H100_LOG=${2:?Usage: $0 <reference_log> <h100_log>}

echo "=== Cross-Hardware Comparison ==="
echo "Reference: $REF_LOG"
echo "H100: $H100_LOG"
echo ""

# Extract step:val_bpb pairs
extract_bpb() {
    grep -oP 'step:\K\d+(?=/\d+ val_loss:\S+ val_bpb:)|\bval_bpb:\K[\d.]+' "$1" | \
        paste - - | sort -n
}

echo "Step | REF_BPB | H100_BPB | Delta"
echo "-----|----------|----------|------"

paste <(extract_bpb "$REF_LOG") <(extract_bpb "$H100_LOG") | \
while read step1 bpb1 step2 bpb2; do
    if [ "$step1" = "$step2" ]; then
        delta=$(python3 -c "print(f'{abs($bpb1 - $bpb2):.4f}')")
        printf "%-5s| %-9s| %-9s| %s\n" "$step1" "$bpb1" "$bpb2" "$delta"
    else
        echo "WARNING: step mismatch $step1 vs $step2"
    fi
done

echo ""
echo "=== Summary ==="

# Compute max delta
paste <(extract_bpb "$REF_LOG") <(extract_bpb "$H100_LOG") | \
python3 -c "
import sys
max_delta = 0
count = 0
for line in sys.stdin:
    parts = line.strip().split()
    if len(parts) == 4 and parts[0] == parts[2]:
        delta = abs(float(parts[1]) - float(parts[3]))
        max_delta = max(max_delta, delta)
        count += 1
print(f'Matched checkpoints: {count}')
print(f'Max absolute delta: {max_delta:.4f} BPB')
if max_delta < 0.003:
    print('VERDICT: EXCELLENT transfer (< 0.003)')
elif max_delta < 0.005:
    print('VERDICT: GOOD transfer (< 0.005)')
elif max_delta < 0.010:
    print('VERDICT: ACCEPTABLE transfer (< 0.010) — monitor carefully')
else:
    print('VERDICT: POOR transfer (>= 0.010) — investigate before submitting')
"
