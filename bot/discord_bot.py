"""Discord bot — forwards messages to the auto-research chat API.

Setup:
  Add to .env in /root/auto-research/:
    DISCORD_BOT_TOKEN=your_token_here
    DISCORD_API_URL=http://localhost:8000/chat/

Run:
  cd /root/auto-research && python3 bot/discord_bot.py

Commands (mention the bot or use slash commands):
  /new     — Clear conversation history and start fresh
  /status  — Show usage stats
"""
import discord
from discord import app_commands
import httpx
import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env")

TOKEN = os.environ["DISCORD_BOT_TOKEN"]
API_URL = os.environ.get("DISCORD_API_URL", "http://localhost:8000/chat/")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def _get_user(discord_username: str):
    """Look up user by discord_id. Returns (user, db) — caller must close db."""
    from api.database import SessionLocal
    from api.models import User
    db = SessionLocal()
    user = db.query(User).filter(User.discord_id == discord_username).first()
    return user, db


def check_and_increment_usage(discord_username: str) -> tuple[bool, str]:
    """Returns (allowed, message). Increments explore_runs_used if allowed."""
    from api.config import settings

    user, db = _get_user(discord_username)
    try:
        if not user:
            return False, "❌ You're not registered. Ask Vuk to add you!"

        limits = settings.tier_limits.get(user.tier, {})
        max_explores = limits.get("explore", 0)

        if max_explores == -1:  # unlimited
            user.explore_runs_used += 1
            db.commit()
            return True, ""

        if user.explore_runs_used >= max_explores:
            return False, (
                f"⛔ You've used all {max_explores} explores this month (tier: `{user.tier}`).\n"
                f"Upgrade at auto-research.ai or wait for monthly reset."
            )

        user.explore_runs_used += 1
        db.commit()
        remaining = max_explores - user.explore_runs_used
        return True, f"_({remaining} explores left this month)_"
    finally:
        db.close()


def get_usage_footer(discord_username: str) -> str:
    """Return a stats footer showing remaining counts."""
    from api.config import settings

    user, db = _get_user(discord_username)
    try:
        if not user:
            return ""
        limits = settings.tier_limits.get(user.tier, {})

        def left(used, mx):
            if mx == -1:
                return "∞"
            return str(max(0, mx - used))

        parts = [f"🔬 {left(user.explore_runs_used, limits.get('explore', 0))} explores"]
        if limits.get("validate", 0) != 0:
            parts.append(f"✅ {left(user.validate_runs_used, limits.get('validate', 0))} validates")
        if limits.get("full", 0) != 0:
            parts.append(f"🏁 {left(user.full_runs_used, limits.get('full', 0))} full")

        return "```\n📊 " + "  |  ".join(parts) + f"  |  tier: {user.tier}\n```"
    finally:
        db.close()


def get_api_key(discord_username: str) -> str | None:
    """Return user's api_key for authenticated API calls, or None."""
    user, db = _get_user(discord_username)
    try:
        return user.api_key if user else None
    finally:
        db.close()


async def clear_history(discord_username: str):
    """Clear conversation history in the API DB."""
    api_key = get_api_key(discord_username)
    if api_key:
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                await http.delete(API_URL + "history", cookies={"session": api_key})
        except Exception as e:
            print(f"Clear history error: {e}")


def strip_html(text: str) -> str:
    """Remove HTML tags (e.g. <details>) for Discord."""
    text = re.sub(r"<details>.*?</details>", "[📊 raw results — use web UI for full table]", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def split_message(text: str, limit: int = 1900) -> list[str]:
    """Split long text into chunks under Discord's 2000-char limit."""
    chunks = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks


@client.event
async def on_ready():
    await tree.sync()
    print(f"Discord bot ready as {client.user} — API: {API_URL} — slash commands synced")


# ── Slash commands ────────────────────────────────────────────────────────

@tree.command(name="new", description="Clear conversation history and start fresh")
async def cmd_new(interaction: discord.Interaction):
    await clear_history(str(interaction.user.name))
    await interaction.response.send_message("🧹 History cleared! Mention me to start a new conversation.", ephemeral=True)


@tree.command(name="status", description="Show your usage stats")
async def cmd_status(interaction: discord.Interaction):
    footer = get_usage_footer(str(interaction.user.name))
    if footer:
        await interaction.response.send_message(footer, ephemeral=True)
    else:
        await interaction.response.send_message("❌ You're not registered. Ask Vuk to add you!", ephemeral=True)


# ── Main message handler ──────────────────────────────────────────────────

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if client.user not in message.mentions:
        return

    discord_username = str(message.author.name)
    text = message.content
    text = re.sub(rf"<@!?{client.user.id}>", "", text).strip()

    print(f"MSG from {discord_username}: {repr(text[:100])}")

    # Text-based commands (work even before slash commands propagate)
    if text.lower() in ("/new", "new", "reset", "/reset"):
        await clear_history(discord_username)
        await message.channel.send("🧹 History cleared! Start a new conversation.", reference=message)
        return

    if text.lower() in ("/status", "status"):
        footer = get_usage_footer(discord_username)
        await message.channel.send(footer or "❌ Not registered.", reference=message)
        return

    if not text:
        await message.channel.send("Hey! Ask me about experiments or say `hi` to get started 🧪")
        return

    # Check registration & limits
    allowed, limit_msg = check_and_increment_usage(discord_username)
    if not allowed:
        await message.channel.send(limit_msg)
        return

    # Authenticated API call — uses DB-backed history automatically
    api_key = get_api_key(discord_username)
    cookies = {"session": api_key} if api_key else {}

    async with message.channel.typing():
        try:
            async with httpx.AsyncClient(timeout=120) as http:
                resp = await http.post(
                    API_URL,
                    json={"message": text, "history": []},
                    cookies=cookies,
                )
            print(f"API {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            reply = data.get("response") or f"API error. Keys: {list(data.keys())}"
        except httpx.ConnectError as e:
            await message.channel.send(f"❌ Can't reach API at `{API_URL}`\n`{e}`")
            return
        except Exception as e:
            await message.channel.send(f"❌ {type(e).__name__}: {e}")
            return

    reply = strip_html(reply)
    footer = get_usage_footer(discord_username)
    if footer:
        reply = reply + "\n\n" + footer

    for chunk in split_message(reply):
        await message.channel.send(chunk)


client.run(TOKEN)
