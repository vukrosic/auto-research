"""AI Onboarding Agent — guides new users through their first experiment.

Triggers automatically when a new account is provisioned.
Interactive chat that walks through:
1. What the platform does
2. How to pick a template/competition
3. Submitting their first experiment
4. Reading results
5. Next steps

Tracks completion. Nudges if user drops off (via email after 24h).
"""

ONBOARDING_SYSTEM_PROMPT = """You are the Auto-Research onboarding assistant. A new user just joined.
Guide them through their first experiment step by step.

Their profile:
{user_context}

Steps:
1. Welcome them, explain the platform in 2 sentences
2. Show them active competitions (if any) or suggest a starter experiment
3. Help them submit their first explore run (500 steps, default params)
4. Explain what happens next (queued → running → results)
5. When results arrive, explain val_bpb and what makes a good score

Be friendly, concise, and encouraging. They're here to do research, not read docs.
"""


async def start_onboarding(user_id: int, user_email: str):
    """Initialize onboarding chat for a new user.

    TODO: Create onboarding session, send first message via platform chat.
    """
    pass


async def send_nudge(user_id: int):
    """Send a nudge email if user hasn't completed onboarding in 24h.

    TODO: Check onboarding completion status, send email via notification service.
    """
    pass
