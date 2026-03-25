---
title: "<claim in one sentence>"
status: "PROPOSED"
origin: ""
finding: ""
created: "YYYY-MM-DD"
---

# H<NNN>: <Claim in one sentence>

## Hypothesis
<Precise, falsifiable claim. E.g., "Squaring any monotonic activation improves val_bpb by >0.005 at 2000+ steps compared to the unsquared version.">

## Prior Evidence
- What explorations or prior work suggest this?
- Effect size observed so far?
- Why might this be true (mechanism)?

## Test Plan (pre-registered)
> **Lock this section before running experiments.** Any edits after results arrive must be noted.

- **Baseline:** <exact config>
- **Treatment:** <exact config, only the hypothesized change>
- **Steps:** <minimum steps for this claim>
- **Seeds:** <how many, which>
- **Success criterion:** <exact BPB threshold, e.g., ">0.005 BPB improvement on 2+ seeds">
- **Kill criterion:** <when to stop early>
- **Confounds to control:** <what else could explain the result>

## Experiments

| Name | Steps | Seeds | val_bpb | Delta | Pass? |
|---|---|---|---|---|---|

## Result
<One paragraph: confirmed/falsified/inconclusive + evidence summary>

## Caveats
- What this does NOT prove
- Conditions under which this might not hold
- What would strengthen/weaken confidence
