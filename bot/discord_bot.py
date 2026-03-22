"""Discord bot — forwards messages to the auto-research chat API.

Setup:
  Add to .env in /root/auto-research/:
    DISCORD_BOT_TOKEN=your_token_here
    DISCORD_API_URL=http://localhost:8000/chat/

Run:
  cd /root/auto-research && python3 bot/discord_bot.py

Commands (via mention or slash):
  /new              — Clear conversation history
  /status           — Show usage stats
  /research <topic> — Launch full pipeline: 12 screens → 5 scales → 2 full runs
  /progress         — Show pipeline progress with steps
"""
import asyncio
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

# Per-user research pipeline state
research_jobs: dict[int, dict] = {}


# ── DB helpers ────────────────────────────────────────────────────────────

def _get_user(discord_username: str):
    from api.database import SessionLocal
    from api.models import User
    db = SessionLocal()
    user = db.query(User).filter(User.discord_id == discord_username).first()
    return user, db


def check_and_increment_usage(discord_username: str) -> tuple[bool, str]:
    from api.config import settings
    user, db = _get_user(discord_username)
    try:
        if not user:
            return False, "❌ You're not registered. Ask Vuk to add you!"
        limits = settings.tier_limits.get(user.tier, {})
        max_exp = limits.get("experiments", 0)
        if max_exp == -1:
            user.explore_runs_used += 1
            db.commit()
            return True, ""
        if user.explore_runs_used >= max_exp:
            return False, (
                f"⛔ You've used all {max_exp} experiments this month.\n"
                "Upgrade at auto-research.ai or wait for monthly reset."
            )
        user.explore_runs_used += 1
        db.commit()
        return True, ""
    finally:
        db.close()


def get_usage_footer(discord_username: str) -> str:
    from api.config import settings
    user, db = _get_user(discord_username)
    try:
        if not user:
            return ""
        limits = settings.tier_limits.get(user.tier, {})
        max_exp = limits.get("experiments", 0)
        if max_exp == -1:
            return ""
        remaining = max(0, max_exp - user.explore_runs_used)
        return str(remaining)
    finally:
        db.close()


def get_api_key(discord_username: str) -> str | None:
    user, db = _get_user(discord_username)
    try:
        return user.api_key if user else None
    finally:
        db.close()


# ── Utilities ─────────────────────────────────────────────────────────────

async def clear_history(discord_username: str):
    api_key = get_api_key(discord_username)
    if api_key:
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                await http.delete(API_URL + "history", cookies={"session": api_key})
        except Exception as e:
            print(f"Clear history error: {e}")


def strip_html(text: str) -> str:
    text = re.sub(r"<details>.*?</details>", "[📊 raw results — use web UI for full table]", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def split_message(text: str, limit: int = 1900) -> list[str]:
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


# ── Research pipeline ─────────────────────────────────────────────────────

def make_job(topic: str) -> dict:
    return {
        "topic": topic,
        "phase": "starting",
        "screen_done": 0, "screen_total": 12,
        "scale_done": 0, "scale_total": 5, "scale_ids": [],
        "full_done": 0, "full_total": 2, "full_ids": [],
        "prog_msg_id": None,
    }


async def start_research(user_id: int, channel, discord_username: str, topic: str):
    from bot.research_pipeline import run_pipeline, format_progress

    if user_id in research_jobs and research_jobs[user_id].get("phase") not in ("done", "error"):
        await channel.send("⚠️ Pipeline already running. Use `@bot /progress` to check status.")
        return

    job = make_job(topic)
    research_jobs[user_id] = job

    api_key = get_api_key(discord_username)
    prog_msg = await channel.send(format_progress(job))
    job["prog_msg_id"] = prog_msg.id

    asyncio.create_task(run_pipeline(job, channel, api_key, prog_msg))


async def show_progress(user_id: int, discord_username: str, channel):
    from bot.research_pipeline import poll_experiments, format_progress

    job = research_jobs.get(user_id)
    if not job:
        await channel.send("No active research pipeline. Start one with `@bot research <topic>`.")
        return

    api_key = get_api_key(discord_username)
    scale_exps = None
    full_exps = None

    if api_key:
        if job.get("scale_ids"):
            scale_exps = await poll_experiments(api_key, job["scale_ids"])
            job["scale_done"] = sum(1 for e in scale_exps if e["status"] in ("completed", "failed"))
        if job.get("full_ids"):
            full_exps = await poll_experiments(api_key, job["full_ids"])
            job["full_done"] = sum(1 for e in full_exps if e["status"] in ("completed", "failed"))

    await channel.send(format_progress(job, scale_exps=scale_exps, full_exps=full_exps))


# ── Bot lifecycle ─────────────────────────────────────────────────────────

@client.event
async def on_ready():
    await tree.sync()
    print(f"Discord bot ready as {client.user} — API: {API_URL}")


# ── Slash commands ────────────────────────────────────────────────────────

@tree.command(name="new", description="Clear conversation history and start fresh")
async def cmd_new(interaction: discord.Interaction):
    await clear_history(str(interaction.user.name))
    await interaction.response.send_message("🧹 History cleared!", ephemeral=True)


@tree.command(name="status", description="Show your usage stats")
async def cmd_status(interaction: discord.Interaction):
    footer = get_usage_footer(str(interaction.user.name))
    msg = f"Experiments remaining: **{footer}**" if footer else "❌ Not registered."
    await interaction.response.send_message(msg, ephemeral=True)


@tree.command(name="research", description="Launch full pipeline: 12 screens → 5 scales → 2 full runs")
@app_commands.describe(topic="What to research (e.g. 'activation functions', 'MoE routing')")
async def cmd_research(interaction: discord.Interaction, topic: str):
    await interaction.response.send_message(f"🚀 Starting research on **{topic}**...", ephemeral=True)
    await start_research(interaction.user.id, interaction.channel, str(interaction.user.name), topic)


@tree.command(name="progress", description="Check research pipeline progress")
async def cmd_progress(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    job = research_jobs.get(interaction.user.id)
    if not job:
        await interaction.followup.send("No active pipeline. Start one with `/research <topic>`.")
        return
    from bot.research_pipeline import poll_experiments, format_progress
    api_key = get_api_key(str(interaction.user.name))
    scale_exps = None
    full_exps = None
    if api_key:
        if job.get("scale_ids"):
            scale_exps = await poll_experiments(api_key, job["scale_ids"])
        if job.get("full_ids"):
            full_exps = await poll_experiments(api_key, job["full_ids"])
    await interaction.followup.send(format_progress(job, scale_exps=scale_exps, full_exps=full_exps))


# ── Message handler ───────────────────────────────────────────────────────

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if client.user not in message.mentions:
        return

    discord_username = str(message.author.name)
    user_id = message.author.id
    text = message.content
    text = re.sub(rf"<@!?{client.user.id}>", "", text).strip()

    print(f"MSG from {discord_username}: {repr(text[:100])}")

    # ── Text-based commands ──
    if text.lower() in ("/new", "new", "reset", "/reset"):
        await clear_history(discord_username)
        await message.channel.send("🧹 History cleared!", reference=message)
        return

    if text.lower() in ("/status", "status"):
        footer = get_usage_footer(discord_username)
        msg = f"Experiments remaining: **{footer}**" if footer else "❌ Not registered."
        await message.channel.send(msg, reference=message)
        return

    if text.lower() in ("/progress", "progress"):
        await show_progress(user_id, discord_username, message.channel)
        return

    m = re.match(r"/?research\s+(.+)", text, re.IGNORECASE)
    if m:
        topic = m.group(1).strip()
        await message.channel.send(f"🚀 Starting research on **{topic}**...", reference=message)
        await start_research(user_id, message.channel, discord_username, topic)
        return

    if not text:
        await message.channel.send("Hey! Ask me about experiments or say `hi` to get started 🧪")
        return

    # ── Normal chat ──
    allowed, limit_msg = check_and_increment_usage(discord_username)
    if not allowed:
        await message.channel.send(limit_msg)
        return

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
