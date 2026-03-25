# Week Plan: [YYYY-Www]

**Campaign**: [campaign name]
**Period**: [Mon date] — [Sun date]

## Resources

| GPU | Type | VRAM | Hours Available | $/hr | Total Cost |
|-----|------|------|-----------------|------|------------|
| [name] | [type] | [GB] | [hrs] | $X.XX | $XX |

**Total GPU-hours**: XXX
**Budget remaining**: $XX

## Capacity Calculations

### Per-stage costs (on [GPU type])

| Stage | Steps | Wall Time | Cost |
|-------|-------|-----------|------|
| Explore | 500 | XX min | $X.XX |
| Validate | 4000 | X.X hr | $X.XX |
| Full | 13780 | XX.X hr | $XX.XX |

### Overhead
- Inter-experiment gap (rsync + setup): ~2 min
- Calibration baseline runs needed: N (N * XX min = XX min)
- Failure budget (10%): XX hours
- **Effective GPU-hours**: XXX

### Allocation

| Phase | Hours | Runs | Days |
|-------|-------|------|------|
| Explore | XX | ~XX | [day range] |
| Validate | XX | ~XX | [day range] |
| Full | XX | ~XX | [day range] |
| Buffer | XX | — | — |
| **Total** | **XXX** | — | — |

## Wave Schedule

### Wave 1 — [Day X to Day Y]
**Type**: Explore
**Axes**: [list]
**Experiments**: [count]
**Expected duration**: XX hours

| # | Experiment Name | Axis | Change | Expected Duration |
|---|----------------|------|--------|-------------------|
| 1 | | | | |

**Decision point**: [When and what to decide]

### Wave 2 — [Day X to Day Y]
[...]

## Decision Points

| Day | Decision | Criteria |
|-----|----------|----------|
| Day 2 EOD | Review Wave 1, design Wave 2 | Any explore beat baseline? |
| Day 4 EOD | Promote to validate or pivot | >2 winners from explores |
| Day 6 EOD | Full run decision | Validated winner >0.01 BPB improvement |

## Success Criteria

A good week means:
- [ ] GPU utilization >90% (>XXX hours of actual training)
- [ ] >XX explore experiments completed
- [ ] >X validate experiments completed
- [ ] At least 1 new finding in knowledge base
- [ ] Best metric improved from X.XXXX to ≤X.XXXX

## Daily Log

### Day 1 — [date]
[Updated as the day progresses]

---
*Plan updates go below this line. Don't delete original plan above.*
