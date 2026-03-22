"""AI Competition Agent — proposes and manages competitions.

Weekly cycle:
1. Scan trending ML research (papers, Twitter, GitHub)
2. Propose 1-2 competition ideas with rules, metrics, suggested prizes
3. Vuk approves/rejects with one click
4. Agent handles full lifecycle: announce → run → score → award

Also manages:
- Competition rule enforcement
- Submission validation
- Leaderboard updates
- Winner announcements
"""

COMPETITION_PROPOSAL_PROMPT = """You are the Auto-Research competition curator.
Based on trending ML research and the platform's capabilities, propose a new competition.

Current templates available: {templates}
Recent popular competitions: {recent_competitions}
Trending topics: {trending_topics}

Propose a competition with:
1. Name (catchy, short)
2. Description (what participants will try to achieve)
3. Rules (constraints, allowed techniques)
4. Metric (how entries are scored)
5. Suggested prize (realistic for a small platform)
6. Duration (1-4 weeks)
7. Why this is interesting right now
"""


async def propose_weekly_competitions():
    """Generate competition proposals for Vuk to approve.

    TODO: Scan sources, generate proposals, save to admin queue.
    """
    pass


async def validate_submission(experiment_id: int, competition_id: int) -> dict:
    """Check if an experiment submission meets competition rules.

    Checks: param count, step limit, allowed techniques, etc.
    """
    # TODO: Load competition rules, validate experiment config
    return {"valid": True, "violations": []}
