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
import io
import json
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
        used = max_exp - remaining
        bar_len = 10
        filled = round(bar_len * remaining / max_exp)
        bar = "🟩" * filled + "⬜" * (bar_len - filled)
        return f"-# 🧪 **{remaining}/{max_exp}** experiments remaining  {bar}"
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


def extract_details(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Return (cleaned_text, [(title, content), ...]) extracting <details> blocks as attachments."""
    attachments = []

    def replacer(m):
        inner = m.group(0)
        title_match = re.search(r"<summary>(.*?)</summary>", inner)
        title = title_match.group(1) if title_match else "results"
        content = re.sub(r"<[^>]+>", "", inner).strip()
        attachments.append((title, content))
        return ""

    cleaned = re.sub(r"<details>.*?</details>", replacer, text, flags=re.DOTALL)
    cleaned = re.sub(r"<[^>]+>", "", cleaned).strip()
    return cleaned, attachments


def _parse_screen_report(report_text: str) -> dict | None:
    """Parse a tiered screen markdown report into structured data."""
    lines = report_text.split("\n")
    stages: list[dict] = []
    current_stage = None
    verdict_lines = []
    in_verdict = False

    for line in lines:
        m = re.match(r"###\s+Stage\s+(\d+)\s*—\s*(\d+)\s+step", line)
        if m:
            current_stage = {"num": int(m.group(1)), "steps": int(m.group(2)), "rows": []}
            stages.append(current_stage)
            in_verdict = False
            continue
        if current_stage and line.startswith("|") and "---" not in line and "Run" not in line:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 6:
                name = cells[0].strip("`")
                desc = cells[1][:45]
                loss = cells[2].strip()
                delta = cells[4].strip()
                decision = cells[5].strip()
                current_stage["rows"].append((name, desc, loss, delta, decision))
            continue
        if "## What happened" in line:
            in_verdict = True
            continue
        if in_verdict and line.strip() and not line.startswith("_"):
            verdict_lines.append(line.strip().replace("**", ""))

    if not stages:
        return None
    return {"stages": stages, "verdict": verdict_lines}


def _render_results_image(parsed: dict) -> io.BytesIO:
    """Render parsed screen results as a clean table image."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgba

    stages = parsed["stages"]
    verdict = parsed["verdict"]

    # Colors
    BG = "#1e1e2e"
    TEXT = "#cdd6f4"
    HEADER_BG = "#313244"
    GREEN = "#a6e3a1"
    RED = "#f38ba8"
    YELLOW = "#f9e2af"
    BLUE = "#89b4fa"
    DIM = "#6c7086"
    BASELINE_BG = "#282838"
    WIN_BG = "#1e3a2e"
    LOSE_BG = "#3a1e2e"

    # Calculate total rows for figure sizing
    total_rows = sum(len(s["rows"]) for s in stages)
    n_headers = len(stages)
    n_verdict = min(len(verdict), 3)
    fig_height = max(2.0, 0.38 * total_rows + 0.55 * n_headers + 0.35 * n_verdict + 0.8)
    fig_width = 9.5

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    y = 0.96
    row_h = 0.38 / max(total_rows + n_headers + n_verdict, 1)
    row_h = min(row_h, 0.055)

    for si, stage in enumerate(stages):
        # Stage header
        ax.add_patch(plt.Rectangle((0.02, y - row_h * 0.8), 0.96, row_h * 0.9,
                                    facecolor=HEADER_BG, edgecolor="none", transform=ax.transData,
                                    clip_on=False, zorder=1))
        ax.text(0.04, y - row_h * 0.3, f"Stage {stage['num']}",
                fontsize=11, fontweight="bold", color=BLUE, fontfamily="monospace",
                va="center", transform=ax.transData)
        ax.text(0.18, y - row_h * 0.3, f"{stage['steps']} steps  ·  {len(stage['rows'])} configs",
                fontsize=9, color=DIM, fontfamily="monospace",
                va="center", transform=ax.transData)
        y -= row_h * 1.1

        # Column headers
        cols = [("Name", 0.04), ("Loss", 0.38), ("Delta", 0.52), ("Decision", 0.66), ("Description", 0.80)]
        for label, x in cols:
            ax.text(x, y - row_h * 0.3, label, fontsize=7.5, color=DIM, fontfamily="monospace",
                    fontweight="bold", va="center", transform=ax.transData)
        y -= row_h * 0.8

        # Data rows
        for name, desc, loss, delta, decision in stage["rows"]:
            is_baseline = "baseline" in decision.lower()
            is_win = "✓" in decision
            is_drop = "drop" in decision.lower()

            # Row background
            if is_baseline:
                rbg = BASELINE_BG
            elif is_win:
                rbg = WIN_BG
            elif is_drop:
                rbg = LOSE_BG
            else:
                rbg = BG
            ax.add_patch(plt.Rectangle((0.02, y - row_h * 0.75), 0.96, row_h * 0.85,
                                        facecolor=rbg, edgecolor="none",
                                        transform=ax.transData, clip_on=False, zorder=0))

            # Icon
            if is_baseline:
                icon, icon_color = "○", DIM
            elif is_win:
                icon, icon_color = "▲", GREEN
            elif is_drop:
                icon, icon_color = "▼", RED
            else:
                icon, icon_color = "·", DIM

            # Delta color
            try:
                dval = float(delta)
                delta_color = GREEN if dval < -0.001 else RED if dval > 0.001 else DIM
            except ValueError:
                delta_color = DIM

            # Decision text
            if is_baseline:
                dec_text, dec_color = "baseline", DIM
            elif "promote" in decision.lower():
                dec_text, dec_color = "advance →", GREEN
            elif "finalist" in decision.lower():
                dec_text, dec_color = "winner ★", YELLOW
            elif is_drop:
                dec_text, dec_color = "eliminated", RED
            else:
                dec_text, dec_color = decision[:12], TEXT

            vy = y - row_h * 0.3
            ax.text(0.025, vy, icon, fontsize=9, color=icon_color, fontfamily="monospace",
                    va="center", transform=ax.transData)
            ax.text(0.04, vy, name[:18], fontsize=9, color=TEXT, fontfamily="monospace",
                    fontweight="bold", va="center", transform=ax.transData)
            ax.text(0.38, vy, loss[:8], fontsize=9, color=TEXT, fontfamily="monospace",
                    va="center", transform=ax.transData)
            ax.text(0.52, vy, delta[:8], fontsize=9, color=delta_color, fontfamily="monospace",
                    va="center", transform=ax.transData)
            ax.text(0.66, vy, dec_text, fontsize=8.5, color=dec_color, fontfamily="monospace",
                    va="center", transform=ax.transData)
            ax.text(0.80, vy, desc[:25], fontsize=7.5, color=DIM, fontfamily="monospace",
                    va="center", transform=ax.transData)
            y -= row_h

        y -= row_h * 0.3  # gap between stages

    # Verdict
    if verdict:
        y -= row_h * 0.2
        for v in verdict[:3]:
            ax.text(0.04, y - row_h * 0.3, v[:90], fontsize=8.5, color=YELLOW,
                    fontfamily="monospace", va="center", transform=ax.transData, style="italic")
            y -= row_h * 0.8

    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor(), pad_inches=0.15)
    plt.close(fig)
    buf.seek(0)
    return buf


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

    # Send a live progress message that updates while the API works
    _spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    _progress_file = Path("/root/parameter-golf/results/.screen_progress.json")
    prog_msg = await message.channel.send(f"{_spinners[0]} Thinking...")

    def _bar(done, total, width=12):
        filled = int(width * done / max(total, 1))
        return "█" * filled + "░" * (width - filled)

    def _fmt_time(seconds):
        m, s = divmod(int(seconds), 60)
        return f"{m}m {s:02d}s" if m else f"{s}s"

    async def _update_progress():
        i = 0
        elapsed = 0
        while True:
            await asyncio.sleep(3)
            elapsed += 3
            i = (i + 1) % len(_spinners)
            timer = _fmt_time(elapsed)

            # Try to read real screen progress
            content = f"{_spinners[i]} **Thinking...** `[{timer}]`"
            try:
                if _progress_file.exists():
                    prog = json.loads(_progress_file.read_text())
                    stage = prog.get("stage", 1)
                    ci = prog.get("config_i", 0)
                    ct = prog.get("config_total", 1)
                    cname = prog.get("config_name", "")
                    steps = prog.get("stage_steps", 0)
                    done_all = prog.get("done_all", 0)
                    total_all = prog.get("total_all", 1)
                    eta_s = prog.get("eta_s", 0)

                    overall_bar = _bar(done_all, total_all)
                    stage_bar = _bar(ci, ct)

                    eta_str = f"  ⏱ ~{_fmt_time(eta_s)} remaining" if eta_s > 0 else ""

                    content = (
                        f"{_spinners[i]} **Training** `[{timer}]`{eta_str}\n"
                        f"Overall [{overall_bar}] {done_all}/{total_all} configs\n"
                        f"Stage {stage}/3 [{stage_bar}] {ci}/{ct} · `{cname}` · {steps} steps"
                    )
            except Exception:
                pass

            try:
                await prog_msg.edit(content=content)
            except Exception:
                break

    ticker = asyncio.create_task(_update_progress())
    try:
        async with httpx.AsyncClient(timeout=1800) as http:
            resp = await http.post(
                API_URL,
                json={"message": text, "history": []},
                cookies=cookies,
            )
        print(f"API {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        reply = data.get("response") or f"API error. Keys: {list(data.keys())}"
    except httpx.ConnectError as e:
        ticker.cancel()
        await prog_msg.edit(content=f"❌ Can't reach API at `{API_URL}`\n`{e}`")
        return
    except Exception as e:
        ticker.cancel()
        await prog_msg.edit(content=f"❌ {type(e).__name__}: {e}")
        return
    finally:
        ticker.cancel()

    # Extract details blocks (raw screen reports) and render as image
    reply, attachments = extract_details(reply)
    results_image = None
    for title, content in attachments:
        parsed = _parse_screen_report(content)
        if parsed:
            try:
                results_image = _render_results_image(parsed)
            except Exception as e:
                print(f"Image render error: {e}")
            break

    # Build final message: AI analysis text only (table is the image)
    final_text = reply.strip() if reply.strip() else "Results:"

    # Collect files: results image + raw .md report
    files = []
    if results_image:
        files.append(discord.File(fp=results_image, filename="results.png"))
    if attachments:
        for title, content in attachments:
            files.append(discord.File(
                fp=io.BytesIO(content.encode()),
                filename=f"{title.replace(' ', '_').replace('/', '_')[:40]}.md",
            ))

    # Replace the progress message with the first chunk; send remaining as new messages
    chunks = split_message(final_text)
    for i, chunk in enumerate(chunks):
        chunk_files = files if i == len(chunks) - 1 and files else []
        if i == 0:
            await prog_msg.edit(content=chunk)
            if chunk_files:
                await message.channel.send(files=chunk_files[:10])
        else:
            await message.channel.send(chunk, files=chunk_files[:10] if chunk_files else [])


client.run(TOKEN)
