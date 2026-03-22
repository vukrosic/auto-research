"""Discord bot — forwards messages to the auto-research chat API.

Setup:
  Add to .env in /root/auto-research/:
    DISCORD_BOT_TOKEN=your_token_here
    DISCORD_API_URL=http://localhost:8000/api/chat/

Run:
  cd /root/auto-research && python3 bot/discord_bot.py
"""
import discord
import httpx
import os
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

TOKEN = os.environ["DISCORD_BOT_TOKEN"]
API_URL = os.environ.get("DISCORD_API_URL", "http://localhost:8000/chat/")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Per-user session history (in-memory, resets on bot restart)
histories: dict[int, list[dict]] = {}


def strip_html(text: str) -> str:
    """Remove HTML tags (e.g. <details>) for Discord."""
    text = re.sub(r"<details>.*?</details>", "[raw results hidden — use web UI]", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def split_message(text: str, limit: int = 1900) -> list[str]:
    """Split long text into chunks under Discord's 2000-char limit."""
    chunks = []
    while len(text) > limit:
        # Try to split at a newline
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
    print(f"Discord bot ready as {client.user} — API: {API_URL}")


@client.event
async def on_message(message: discord.Message):
    print(f"MSG from {message.author}: {repr(message.content[:100])} | mentions: {message.mentions}")
    # Only respond when mentioned
    if message.author.bot:
        return
    if client.user not in message.mentions:
        return

    user_id = message.author.id
    text = message.content
    # Strip the bot mention
    text = re.sub(rf"<@!?{client.user.id}>", "", text).strip()
    if not text:
        await message.channel.send("Hey! Ask me about experiments or say `help` to get started 🧪")
        return

    history = histories.get(user_id, [])

    async with message.channel.typing():
        try:
            async with httpx.AsyncClient(timeout=120) as http:
                resp = await http.post(API_URL, json={"message": text, "history": history[-20:]})
            print(f"API status: {resp.status_code}")
            print(f"API response: {resp.text[:500]}")
            data = resp.json()
            reply = data.get("response") or f"API returned no response field. Keys: {list(data.keys())}"
        except httpx.ConnectError as e:
            await message.channel.send(f"❌ Can't reach API at `{API_URL}` — is the server running?\n`{e}`")
            return
        except Exception as e:
            await message.channel.send(f"❌ API error: {type(e).__name__}: {e}")
            return

    # Update history
    histories[user_id] = history + [
        {"role": "user", "content": text},
        {"role": "assistant", "content": reply},
    ]

    # Clean up HTML and send in chunks
    reply = strip_html(reply)
    for chunk in split_message(reply):
        await message.channel.send(chunk)


client.run(TOKEN)
