"""
SnapVault Discord Bot
─────────────────────
Saving:
  • /save <text>        — explicitly save a text note
  • Send any image      — auto-saved
  • Plain text message  — classified by LLM as save / query / ignore

Querying:
  • /ask <question>     — query your saves
  • Reply in a thread   — context-aware follow-ups

Managing:
  • /list               — show your 5 most recent notes
  • /delete <id>        — delete a note by ID

Other:
  • /remind <when> <message>
  • /help
  • !clear              — wipe thread conversation history
"""

import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
import openai

import db
import ingestion
import embedder
import conversation
import reminders
from config import DISCORD_TOKEN, UCSD_API_KEY, UCSD_BASE_URL, LLM_CHAT_MODEL

# ── intents ───────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
tree = bot.tree

_llm = openai.OpenAI(api_key=UCSD_API_KEY, base_url=UCSD_BASE_URL)


# ── helpers ───────────────────────────────────────────────────────────────────
def _thread_id(message: discord.Message) -> str:
    return str(message.channel.id)

def _user_id(message: discord.Message) -> str:
    return str(message.author.id)

def _make_embed(note: dict, label: str = "") -> discord.Embed:
    snippet = note["content_text"][:900]
    title = label if label else f"Note {note['id']}"
    e = discord.Embed(title=title, description=snippet, color=0x5865F2)
    e.set_footer(text=f"Note {note['id']} · {note['timestamp'][:10]} · {note['source_type']}")
    return e

def _classify(text: str) -> str:
    try:
        resp = _llm.chat.completions.create(
            model=LLM_CHAT_MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": (
                "Classify this message as 'save' (storing information), "
                "'query' (asking a question), or 'ignore' (greeting/chit-chat/command).\n"
                f"Message: {text}\n"
                "Reply with only one word: save, query, or ignore."
            )}]
        )
        raw = (
            resp.choices[0].message.content
            or resp.choices[0].message.reasoning_content
            or ""
        )
        raw = raw.strip().lower()
        if "save" in raw:   return "save"
        if "query" in raw:  return "query"
        return "ignore"
    except Exception:
        return "ignore"

async def _send_query_response(channel, reply_func, thread_id: str, user_id: str, text: str):
    # FIX: conversation.answer() calls OpenAI + ChromaDB synchronously — run in thread
    reply_text, safe_notes, sensitive_notes = await asyncio.to_thread(
        conversation.answer, thread_id, user_id, text
    )
    await reply_func(reply_text)
    for n in safe_notes[:3]:
        await channel.send(embed=_make_embed(n))
    if sensitive_notes:
        await channel.send(
            "⚠️ Some retrieved notes contain sensitive info and were **not** shown to the AI:"
        )
        for n in sensitive_notes:
            await channel.send(embed=_make_embed(n))


# ── consolidation UI ──────────────────────────────────────────────────────────
class ConsolidationView(discord.ui.View):
    """
    Shown when LLM detects a new note is similar to an existing one.
    Verdict and reason from LLM are shown to help user decide.
    """
    def __init__(self, user_id: str, new_text: str, existing_note: dict,
                 verdict: str, reason: str, discord_message_id: str = None):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.new_text = new_text
        self.existing_note = existing_note
        self.verdict = verdict
        self.reason = reason
        self.discord_message_id = discord_message_id

    @discord.ui.button(label="Replace old note", style=discord.ButtonStyle.danger)
    async def replace(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("Not your note.", ephemeral=True)
            return
        db.delete_note(self.existing_note["id"])
        embedder.delete(self.existing_note["id"])
        # FIX: ingest_text is sync (DB write + embedding) — run in thread
        note = await asyncio.to_thread(
            ingestion.ingest_text, self.user_id, self.new_text,
            self.discord_message_id
        )
        self.stop()
        await interaction.response.edit_message(
            content=f"✅ Replaced Note {self.existing_note['id']} with Note {note.id}.",
            embeds=[], view=None
        )

    @discord.ui.button(label="Keep both", style=discord.ButtonStyle.success)
    async def keep_both(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("Not your note.", ephemeral=True)
            return
        # FIX: same as above
        note = await asyncio.to_thread(
            ingestion.ingest_text, self.user_id, self.new_text,
            self.discord_message_id
        )
        self.stop()
        await interaction.response.edit_message(
            content=f"✅ Saved as Note {note.id}. Both notes kept.",
            embeds=[], view=None
        )

    @discord.ui.button(label="Discard new", style=discord.ButtonStyle.secondary)
    async def discard(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("Not your note.", ephemeral=True)
            return
        self.stop()
        await interaction.response.edit_message(
            content="❌ New note discarded. Existing note kept.", embeds=[], view=None
        )

    async def on_timeout(self):
        self.stop()


# ── sensitive info UI ─────────────────────────────────────────────────────────
class SensitiveNoteView(discord.ui.View):
    def __init__(self, user_id: str, note_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.note_id = note_id

    @discord.ui.button(label="Keep private (default)", style=discord.ButtonStyle.secondary)
    async def keep_private(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("Not your note.", ephemeral=True)
            return
        self.stop()
        await interaction.response.edit_message(
            content=f"🔒 Note {self.note_id} saved. Stored but **excluded from AI context**.",
            view=None
        )

    @discord.ui.button(label="Allow into LLM", style=discord.ButtonStyle.primary)
    async def allow_llm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("Not your note.", ephemeral=True)
            return
        db.update_note_sensitive(self.note_id, False)
        self.stop()
        await interaction.response.edit_message(
            content=f"✅ Note {self.note_id} now **allowed into AI context**.", view=None
        )

    @discord.ui.button(label="Delete it", style=discord.ButtonStyle.danger)
    async def delete_it(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("Not your note.", ephemeral=True)
            return
        db.delete_note(self.note_id)
        embedder.delete(self.note_id)
        self.stop()
        await interaction.response.edit_message(
            content="🗑️ Sensitive note deleted — nothing stored.", view=None
        )

    async def on_timeout(self):
        self.stop()


# ── save helper ───────────────────────────────────────────────────────────────
async def _save_with_consolidation_check(
    send_func,
    user_id: str,
    text: str,
    discord_message_id: str = None,
    original_message: discord.Message = None,
):
    # Single embedding round-trip: returns (existing_note | None, embedding, skip_llm)
    # The embedding is reused by ingest_text so we never call the embedding API twice.
    existing, embedding, skip_llm = await asyncio.to_thread(
        ingestion.find_similar_note, user_id, text
    )

    if existing:
        if skip_llm:
            # Near-identical (>= SKIP_LLM_THRESHOLD) — treat as duplicate without an LLM call
            verdict, reason = "duplicate", "Notes are nearly identical."
        else:
            # In the 0.80–0.97 band — worth asking the LLM
            comparison = await asyncio.to_thread(
                ingestion.llm_compare, existing["content_text"], text
            )
            verdict = comparison["verdict"]
            reason = comparison["reason"]

        verdict_label = {
            "duplicate": "🔁 Duplicate",
            "update":    "🔄 Update to existing",
            "keep_both": "📝 Possibly different",
        }.get(verdict, "⚠️ Similar note found")

        view = ConsolidationView(
            user_id, text, existing, verdict, reason,
            discord_message_id=discord_message_id
        )
        await send_func(
            content=(
                f"{verdict_label} — *{reason}*\n\n"
                "**Existing note** (above) vs **New note** (below):"
            ),
            embeds=[
                _make_embed(existing, label="📌 Existing note"),
                discord.Embed(title="🆕 New note", description=text[:900], color=0x57F287)
            ],
            view=view
        )
        return

    # Reuse the embedding computed above — ingest_text won't call the API again
    note = await asyncio.to_thread(
        ingestion.ingest_text, user_id, text, discord_message_id, embedding
    )

    if note.is_sensitive:
        await send_func(
            content=(
                f"⚠️ This looks like **sensitive info** (Note {note.id}).\n"
                "Saved but **excluded from AI context** by default. What would you like to do?"
            ),
            embeds=[],
            view=SensitiveNoteView(user_id, note.id)
        )
    else:
        if original_message:
            await original_message.add_reaction("✅")
        else:
            await send_func(content="✅ Saved.", embeds=[], view=None)


# ── events ────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    db.init_db()
    bot.loop.create_task(reminders.reminder_loop(bot))
    await tree.sync()
    print(f"[SnapVault] logged in as {bot.user} (id: {bot.user.id})")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    await bot.process_commands(message)
    if message.content.startswith(bot.command_prefix):
        return

    uid = _user_id(message)
    text = message.content.strip()

    has_image = bool(
        message.attachments and
        any(a.content_type and a.content_type.startswith("image") for a in message.attachments)
    )
    if has_image:
        async with message.channel.typing():
            saved = []
            for att in message.attachments:
                if att.content_type and att.content_type.startswith("image"):
                    note = await ingestion.ingest_image(
                        uid, att.url,
                        user_caption=text,
                        discord_message_id=str(message.id)
                    )
                    saved.append(note)
            sensitive_saved = [n for n in saved if n.is_sensitive]
            if sensitive_saved:
                for n in sensitive_saved:
                    await message.reply(
                        f"⚠️ Image Note {n.id} contains sensitive info. "
                        "Saved but excluded from AI. What would you like to do?",
                        view=SensitiveNoteView(uid, n.id)
                    )
            else:
                await message.add_reaction("✅")
        return

    if not text:
        return

    if isinstance(message.channel, discord.Thread):
        async with message.channel.typing():
            await _send_query_response(
                message.channel, message.reply,
                _thread_id(message), uid, text
            )
        return

    # FIX: _classify calls OpenAI (sync) — run in thread
    async with message.channel.typing():
        intent = await asyncio.to_thread(_classify, text)

    if intent == "save":
        async def _send(content, embeds, view):
            await message.reply(content=content, embeds=embeds, view=view)
        await _save_with_consolidation_check(
            _send, uid, text,
            discord_message_id=str(message.id),
            original_message=message
        )
    elif intent == "query":
        async with message.channel.typing():
            await _send_query_response(
                message.channel, message.reply,
                _thread_id(message), uid, text
            )


@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if after.author.bot:
        return
    if before.content == after.content:
        return
    new_text = after.content.strip()
    if not new_text:
        return
    existing = db.get_note_by_discord_message_id(str(after.id))
    if not existing:
        return
    # FIX: update_note does DB write + re-embed (sync) — run in thread
    await asyncio.to_thread(ingestion.update_note, existing["id"], new_text)
    await after.add_reaction("✏️")


@bot.event
async def on_message_delete(message: discord.Message):
    """If a saved message is deleted in Discord, delete the note from storage too."""
    if message.author.bot:
        return
    existing = db.get_note_by_discord_message_id(str(message.id))
    if not existing:
        return
    db.delete_note(existing["id"])
    embedder.delete(existing["id"])
    try:
        user = await bot.fetch_user(message.author.id)
        await user.send(
            f"🗑️ Note {existing['id']} was deleted from your SnapVault "
            "because you deleted the original Discord message."
        )
    except Exception:
        pass


# ── slash commands ────────────────────────────────────────────────────────────
@tree.command(name="save", description="Save a text note to your SnapVault")
@app_commands.describe(note="The text you want to save")
async def slash_save(interaction: discord.Interaction, note: str):
    await interaction.response.defer(ephemeral=True)
    uid = str(interaction.user.id)

    async def _send(content, embeds, view):
        await interaction.followup.send(content=content, embeds=embeds, view=view, ephemeral=True)

    await _save_with_consolidation_check(_send, uid, note)


@tree.command(name="ask", description="Ask a question about your saved notes")
@app_commands.describe(question="What do you want to know?")
async def slash_ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    uid = str(interaction.user.id)
    tid = str(interaction.channel_id)
    # FIX: conversation.answer() is fully synchronous — run in thread
    reply_text, safe_notes, sensitive_notes = await asyncio.to_thread(
        conversation.answer, tid, uid, question
    )
    await interaction.followup.send(reply_text)
    for n in safe_notes[:3]:
        await interaction.followup.send(embed=_make_embed(n))
    if sensitive_notes:
        await interaction.followup.send(
            "⚠️ Some notes with sensitive content were not shown to the AI:",
            ephemeral=True
        )
        for n in sensitive_notes:
            await interaction.followup.send(embed=_make_embed(n), ephemeral=True)


@tree.command(name="list", description="Show your most recent saved notes")
async def slash_list(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    notes = db.get_recent_notes(uid, limit=5)
    if not notes:
        await interaction.response.send_message("No saved notes yet.", ephemeral=True)
        return
    await interaction.response.send_message("Your 5 most recent notes:", ephemeral=True)
    for n in notes:
        await interaction.followup.send(embed=_make_embed(n), ephemeral=True)


@tree.command(name="delete", description="Delete a saved note by ID")
@app_commands.describe(note_id="The note ID (visible in note footers)")
async def slash_delete(interaction: discord.Interaction, note_id: int):
    uid = str(interaction.user.id)
    notes = db.get_notes_by_ids([note_id])
    if not notes or notes[0].get("user_id") != uid:
        await interaction.response.send_message("❌ Note not found or not yours.", ephemeral=True)
        return
    db.delete_note(note_id)
    embedder.delete(note_id)
    await interaction.response.send_message(f"🗑️ Note {note_id} deleted.", ephemeral=True)


@tree.command(name="remind", description="Set a reminder")
@app_commands.describe(when="ISO datetime e.g. 2025-06-10T09:00", message="What to remind you about")
async def slash_remind(interaction: discord.Interaction, when: str, message: str):
    try:
        remind_at = datetime.fromisoformat(when).replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        await interaction.response.send_message("❌ Use ISO format: `2025-06-10T09:00`", ephemeral=True)
        return
    db.insert_reminder(str(interaction.user.id), note_id=0, remind_at=remind_at, message=message)
    await interaction.response.send_message(f"⏰ Reminder set for `{when}`", ephemeral=True)


@tree.command(name="help", description="How to use SnapVault")
async def slash_help(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**SnapVault** — your personal memory bot\n\n"
        "**Saving**\n"
        "• `/save <text>` — save a text note\n"
        "• Send an image → auto-saved\n"
        "• Plain text → auto-classified as save or query\n\n"
        "**Asking**\n"
        "• `/ask <question>` — query your saves\n"
        "• Reply in a thread for context-aware follow-ups\n\n"
        "**Managing**\n"
        "• `/list` — see your 5 most recent notes\n"
        "• `/delete <id>` — remove a note by ID\n"
        "• Edit a message → note auto-updated ✏️\n"
        "• Delete a message → note auto-removed 🗑️\n\n"
        "**Reminders**\n"
        "• `/remind 2025-06-10T09:00 your message`\n\n"
        "• `!clear` — wipe conversation history for this thread",
        ephemeral=True
    )


# ── prefix commands ───────────────────────────────────────────────────────────
@bot.command(name="clear")
async def cmd_clear(ctx: commands.Context):
    conversation.clear(_thread_id(ctx.message))
    await ctx.reply("🗑️ Conversation history cleared.")


# ── run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN not set in .env")
    bot.run(DISCORD_TOKEN)