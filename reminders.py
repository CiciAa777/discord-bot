"""
Background loop that checks for due reminders and DMs users.
Start as asyncio task from bot.py.
"""
import asyncio
import discord
import db


async def reminder_loop(bot: discord.Client):
    await bot.wait_until_ready()
    while not bot.is_closed():
        due = db.get_due_reminders()
        for r in due:
            try:
                user = await bot.fetch_user(int(r["user_id"]))
                note_rows = db.get_notes_by_ids([r["note_id"]])
                note_text = note_rows[0]["content_text"][:300] if note_rows else ""
                msg = r["message"] or "Here's your reminder!"
                await user.send(f"⏰ **Reminder:** {msg}\n\n> {note_text}")
                db.mark_reminder_sent(r["id"])
            except Exception as e:
                print(f"[reminder] Failed to send reminder {r['id']}: {e}")
        await asyncio.sleep(60)
