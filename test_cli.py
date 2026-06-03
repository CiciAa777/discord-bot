"""
SnapVault CLI Test Harness
──────────────────────────
Test all core flows from the terminal without Discord.

Usage:
    python test_cli.py

Commands inside the CLI:
    /save <text>          — save a text note
    /image <path>         — save a local image file
    /ask <question>       — query your notes
    /history              — show all saved notes
    /clear                — clear conversation history
    /remind <ISO> <msg>   — add a reminder
    /quit                 — exit
"""

import asyncio
import sys
import os

# Make sure we can import project modules
sys.path.insert(0, os.path.dirname(__file__))

import db
import ingestion
import conversation
from config import UCSD_API_KEY, DISCORD_TOKEN

USER_ID = "test_user_001"
THREAD_ID = "test_thread_001"


def check_env():
    issues = []
    if not UCSD_API_KEY:
        issues.append("  ✗ UCSD_API_KEY missing in .env")
    else:
        issues.append("  ✓ UCSD_API_KEY found")
    if not DISCORD_TOKEN:
        issues.append("  ⚠ DISCORD_TOKEN missing (fine for CLI testing)")
    else:
        issues.append("  ✓ DISCORD_TOKEN found")
    return issues


def show_notes():
    import sqlite3
    from config import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, source_type, timestamp, substr(content_text,1,120) as preview "
        "FROM notes WHERE user_id=? ORDER BY id DESC LIMIT 20",
        (USER_ID,)
    ).fetchall()
    conn.close()
    if not rows:
        print("  (no notes saved yet)")
        return
    for r in rows:
        print(f"  [{r['id']}] {r['source_type']} | {r['timestamp'][:19]}")
        print(f"       {r['preview']!r}")


async def handle_image(path: str):
    path = path.strip()
    if not os.path.exists(path):
        print(f"  ✗ File not found: {path}")
        return
    with open(path, "rb") as f:
        image_bytes = f.read()

    # Bypass URL download — call extractors directly
    import extractor_ocr
    import extractor_vision
    import embedder

    print("  → Running OCR...")
    ocr_text, is_sparse = extractor_ocr.extract(image_bytes)
    print(f"  → OCR words: {len(ocr_text.split())} | sparse: {is_sparse}")

    if is_sparse:
        print("  → OCR sparse, calling UCSD Gemma Vision...")
        try:
            content_text = extractor_vision.extract(image_bytes)
            ocr_failed = False
        except Exception as e:
            print(f"  ✗ Vision failed: {e}")
            content_text = ocr_text or "[extraction failed]"
            ocr_failed = True
    else:
        content_text = ocr_text
        ocr_failed = False

    from models import Note
    note = Note(
        user_id=USER_ID,
        content_text=content_text,
        source_type="image",
        image_path=path,
        ocr_failed=ocr_failed
    )
    note.id = db.insert_note(note)
    embedder.upsert(note.id, USER_ID, content_text)

    print(f"  ✓ Saved as note #{note.id}")
    print(f"  Extracted text preview: {content_text[:200]!r}")


def handle_save(text: str):
    note = ingestion.ingest_text(USER_ID, text)
    print(f"  ✓ Saved as note #{note.id}")


def handle_ask(question: str):
    print("  → Retrieving + generating answer...")
    try:
        reply, notes = conversation.answer(THREAD_ID, USER_ID, question)
        print(f"\n  SnapVault: {reply}\n")
        if notes:
            print(f"  (based on {len(notes)} saved note(s)):")
            for n in notes:
                print(f"    • [{n['id']}] {n['content_text'][:80]!r}")
        else:
            print("  (no relevant notes found)")
    except Exception as e:
        print(f"  ✗ Error: {e}")


def handle_remind(args: str):
    parts = args.strip().split(" ", 1)
    if len(parts) < 2:
        print("  Usage: /remind 2025-06-10T09:00 your message here")
        return
    when, msg = parts
    try:
        from datetime import datetime, timezone
        remind_at = datetime.fromisoformat(when).replace(tzinfo=timezone.utc).isoformat()
        db.insert_reminder(USER_ID, note_id=0, remind_at=remind_at, message=msg)
        print(f"  ✓ Reminder set for {when}: {msg!r}")
    except ValueError:
        print("  ✗ Bad date format. Use ISO: 2025-06-10T09:00")


async def main():
    print("=" * 50)
    print("  SnapVault CLI Test Harness")
    print("=" * 50)

    # Env check
    for line in check_env():
        print(line)
    print()

    # Init DB
    db.init_db()
    print("  ✓ Database initialized\n")
    print("  Commands: /save <text> | /image <path> | /ask <q> | /history | /clear | /remind <ISO> <msg> | /quit")
    print("  (or just type text without a prefix to save it as a note)\n")

    while True:
        try:
            raw = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  bye!")
            break

        if not raw:
            continue

        if raw.lower() in ("/quit", "/exit", "quit", "exit"):
            print("  bye!")
            break
        elif raw.startswith("/save "):
            handle_save(raw[6:])
        elif raw.startswith("/image "):
            await handle_image(raw[7:])
        elif raw.startswith("/ask "):
            handle_ask(raw[5:])
        elif raw == "/history":
            show_notes()
        elif raw.startswith("/delete "):
            import sqlite3
            from config import DB_PATH
            note_id = raw[8:].strip()
            conn = sqlite3.connect(DB_PATH)
            conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
            conn.commit()
            conn.close()
            print(f"  ✓ Deleted note #{note_id} from SQLite. (Note: Vector remains in Chroma)")
        elif raw == "/clear":
            conversation.clear(THREAD_ID)
            print("  ✓ Conversation history cleared")
        elif raw.startswith("/remind "):
            handle_remind(raw[8:])
        elif raw.startswith("/"):
            print("  Unknown command. Try /save, /image, /ask, /history, /clear, /remind, /quit")
        else:
            # Bare text → save it
            handle_save(raw)


if __name__ == "__main__":
    asyncio.run(main())