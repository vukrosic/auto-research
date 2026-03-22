"""AI Support Agent — handles ALL user support with zero human involvement.

This agent:
1. Receives user messages (chat widget, email, Skool DMs)
2. Has full context: user tier, experiments, results, platform docs
3. Answers 95%+ of questions autonomously
4. Only escalates truly novel issues (creates GitHub issue tagged needs-vuk)

Vuk checks GitHub issues once/day max. Never talks to users directly.
"""
from dataclasses import dataclass

SUPPORT_SYSTEM_PROMPT = """You are the Auto-Research platform support agent. You help users with:

1. Platform usage: how to submit experiments, read results, use competitions
2. Research guidance: what parameters to try, how to interpret val_bpb
3. Account issues: tier limits, billing questions, API keys
4. Technical issues: experiment failures, GPU errors

Rules:
- Be helpful and concise
- If you genuinely cannot resolve something, say "I'm flagging this for review"
  and the system will create a GitHub issue
- Never promise features that don't exist
- Never share other users' data or experiments
- For billing: direct to Skool for payment changes

You have access to:
- The user's profile (tier, usage, experiments)
- Platform documentation
- Common troubleshooting steps

User context:
{user_context}

Platform docs:
{platform_docs}
"""


@dataclass
class SupportResponse:
    message: str
    resolved: bool
    needs_escalation: bool
    escalation_reason: str | None = None


async def handle_support_message(
    user_message: str,
    user_context: dict,
    anthropic_client=None,
) -> SupportResponse:
    """Process a support message and return AI response.

    TODO: Implement with Claude API call using SUPPORT_SYSTEM_PROMPT.
    """
    # Placeholder — will use Claude API
    return SupportResponse(
        message="Support agent coming soon. For now, ask in the Skool community.",
        resolved=False,
        needs_escalation=False,
    )
