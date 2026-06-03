"""
SnapVault Discord Bot
─────────────────────
Saving:
  • Forward/send any image  → OCR + Vision extract → saved ✓
  • Send any text message   → saved as note ✓

Querying (in a thread or DM, or prefix with ?):
  • "what bikes am I looking at?"
  • "which was cheaper?"    (thread context maintained)

Commands:
  • !clear   — wipe your thread conversation history
  • !remind <ISO datetime or natural> <message>
               e.g. !remind 2025-06-10T09:00 check the bike price
"""

import asyncio
from email.mime import message
import re
import discord
from discord.ext import commands
from datetime import datetime, timezone

import db
import ingestion
import conversation
import reminders
from config import DISCORD_TOKEN

# ── intents ──────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
)


# ── helpers ───────────────────────────────────────────────────────────────────
QUESTION_RE = re.compile(
    r"^(what|which|who|where|when|how|why|show|find|list|tell|compare|is|are|do|did|can|could)\b",
    re.IGNORECASE
)

def _is_question(text: str) -> bool:
    return text.endswith("?") or bool(QUESTION_RE.match(text.strip()))

def _thread_id(message: discord.Message) -> str:
    if isinstance(message.channel, discord.Thread):
        return str(message.channel.id)
    return str(message.channel.id)

def _user_id(message: discord.Message) -> str:
    return str(message.author.id)

def _make_embed(note: dict) -> discord.Embed:
    snippet = note["content_text"][:900]
    e = discord.Embed(description=snippet, color=0x5865F2)
    e.set_footer(text=f"Saved {note['timestamp'][:10]} · {note['source_type']}")
    if note.get("image_path"):
        e.set_thumbnail(url=f"attachment://{note['image_path'].split('/')[-1]}")
    return e

# ── events ────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    db.init_db()
    bot.loop.create_task(reminders.reminder_loop(bot))
    print(f"[SnapVault] logged in as {bot.user} (id: {bot.user.id})")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Let commands run first
    await bot.process_commands(message)
    if message.content.startswith(bot.command_prefix):
        return

    uid = _user_id(message)
    text = message.content.strip()
    has_image = bool(message.attachments and
                     any(a.content_type and a.content_type.startswith("image")
                         for a in message.attachments))

    # ── SAVE: image ──
    if has_image:
        async with message.channel.typing():
            saved = []
            for att in message.attachments:
                if att.content_type and att.content_type.startswith("image"):
                    note = await ingestion.ingest_image(uid, att.url, user_caption=text)
                    saved.append(note)
            count = len(saved)
            suffix = " (Vision used)" if any(n.ocr_failed for n in saved) else ""
            await message.reply(f"✅ Saved {count} image{'s' if count>1 else ''}{suffix}")
        return

    # ── SAVE or QUERY: text ──
    if text:
        in_thread = isinstance(message.channel, discord.Thread)

        if in_thread or _is_question(text):
            # Query path
            async with message.channel.typing():
                tid = _thread_id(message)
                reply_text, notes = conversation.answer(tid, uid, text)
            await message.reply(reply_text)
            for n in notes[:3]:
                await message.channel.send(embed=_make_embed(n))
        else:
            # Save path
            ingestion.ingest_text(uid, text)
            await message.add_reaction("✅")


# ── commands ──────────────────────────────────────────────────────────────────
@bot.command(name="clear")
async def cmd_clear(ctx: commands.Context):
    """Clear your conversation history for this thread/channel."""
    conversation.clear(_thread_id(ctx.message))
    await ctx.reply("🗑️ Conversation history cleared.")


@bot.command(name="remind")
async def cmd_remind(ctx: commands.Context, when: str, *, reminder_msg: str = ""):
    """
    !remind <ISO datetime> <message>
    e.g. !remind 2025-06-10T09:00 check the bike price
    """
    try:
        remind_at = datetime.fromisoformat(when).replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        await ctx.reply("❌ Couldn't parse the date. Use ISO format: `2025-06-10T09:00`")
        return

    uid = _user_id(ctx.message)
    # Associate with most recent note for this user (optional convenience)
    db.insert_reminder(uid, note_id=0, remind_at=remind_at, message=reminder_msg)
    await ctx.reply(f"⏰ Reminder set for `{when}`")


@bot.command(name="help")
async def cmd_help(ctx: commands.Context):
    await ctx.reply(
        "**SnapVault** — your personal memory bot\n\n"
        "**Saving**\n"
        "• Send/forward any image → extracted & saved\n"
        "• Send any text → saved as a note\n\n"
        "**Asking**\n"
        "• Ask a question → bot retrieves relevant saves and answers\n"
        "• Follow up in the thread for context-aware replies\n\n"
        "**Commands**\n"
        "`!clear` — wipe conversation history\n"
        "`!remind 2025-06-10T09:00 your message` — set a reminder\n"
    )


# ── run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN not set in .env")
    bot.run(DISCORD_TOKEN)
