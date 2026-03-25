WHY = "Test optimal balance between weight sharing (num_unique_blocks) and repetition cycles (num_cycles) to reduce parameters while maintaining performance"

CONFIGS = [
    ("baseline", "Control — no changes.", {}),
    ("share_3x3", "3 unique blocks, 3 cycles (9L total) - moderate weight sharing", {"num_unique_blocks": 3, "num_cycles": 3}),
    ("share_2x4", "2 unique blocks, 4 cycles (8L total) - aggressive weight sharing", {"num_unique_blocks": 2, "num_cycles": 4}),
    ("share_1x9", "1 unique block, 9 cycles (9L total) - extreme weight sharing", {"num_unique_blocks": 1, "num_cycles": 9}),
    ("share_4x2", "4 unique blocks, 2 cycles (8L total) - light weight sharing", {"num_unique_blocks": 4, "num_cycles": 2}),
]
