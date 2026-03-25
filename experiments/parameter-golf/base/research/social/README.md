# Social Planning

This folder is the working area for planning social media posts about Parameter Golf experiments.
It is also part of the experiment-planning loop: the questions worth explaining publicly should influence which experiments get validated next.

Use it for:
- deciding which experiment results are worth posting
- drafting short posts, threads, and visual ideas
- tracking status from idea -> drafted -> posted
- keeping claims tied to concrete experiment artifacts
- identifying which claims are strong enough to justify follow-up experiments
- turning "this would make a good post if true" into a concrete validation plan

Recommended workflow:
1. Pull numbers from `results/*/summary.json` or a findings doc.
2. Write the takeaway in one sentence.
3. Record the supporting runs in the backlog table.
4. Decide whether the story is already solid or still needs validation.
5. If validation is needed, write the experiment follow-up before drafting the post.
6. Draft the post in a separate markdown file in this folder.
7. Note whether the post still needs a chart, image, or validation run.

Suggested file layout:
- `POST_BACKLOG.md` for planned posts and status
- one file per draft, e.g. `x_post_architecture_frontier.md`
- optional image scripts or notes if a post needs a chart

How this should influence experiments:
- if a result would be compelling only if it survives longer runs, queue the longer run
- if a claim depends on fitting the 16 MB cap, prioritize budget-fit variants before more novelty experiments
- if a negative result is unusually clear, consider one confirmation rerun and then stop spending compute there
- if a post compares two ideas, make sure the comparison is fair on steps, seeds, and size budget

Rule for claims:
- prefer claims backed by multiple runs or large deltas
- label single-seed / short-run results as early signals
- distinguish clearly between legal submission results and over-budget research results
