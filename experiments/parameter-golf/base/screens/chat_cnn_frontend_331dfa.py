WHY = "Test if local pattern detection via convolutions before transformer helps"

CONFIGS = [
    ("baseline", "Control — no changes.", {}),
    ("conv_3", "Single conv layer, kernel=3", {"conv_kernel": 3}),
    ("conv_5", "Single conv layer, kernel=5", {"conv_kernel": 5}),
    ("conv_7", "Single conv layer, kernel=7", {"conv_kernel": 7}),
    ("conv_3_bottle", "conv=3 + embed_bottleneck=128", {"conv_kernel": 3, "embed_bottleneck": 128}),
    ("conv_5_bottle", "conv=5 + embed_bottleneck=128", {"conv_kernel": 5, "embed_bottleneck": 128}),
]
