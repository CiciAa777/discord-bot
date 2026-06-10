"""
SnapVault CLI Test Harness
──────────────────────────
Test all core flows from the terminal without Discord.

Usage:
    python test_cli.py

Commands:
    /save <text>          — explicitly save a text note (checks sensitive + similarity)
    /image <path>         — save a local image file
    /ask <question>       — query your notes (shows if sensitive notes were stripped)
    /classify <text>      — test the LLM input classifier (save / query / ignore)
    /sensitive <text>     — test the sensitive-info regex detector
    /delete <id>          — delete a note by ID
    /history              — show all saved notes
    /clear                — clear conversation history
    /remind <ISO> <msg>   — add a reminder
    /quit                 — exit

Neutral input mode (no prefix):
    Type anything without a prefix → runs through LLM classifier, then acts accordingly.
    This mirrors exactly what the Discord bot does with plain messages.
"""

import asyncio
import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import db
import ingestion
import embedder
import conversation
from config import UCSD_API_KEY, DISCORD_TOKEN

USER_ID = "test_user_001"
THREAD_ID = "test_thread_001"

# ── sensitive regex (mirrors conversation.py) ─────────────────────────────────
_SENSITIVE_RE = re.compile(
    r"(sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36}|Bearer\s+[a-zA-Z0-9\-._~+/]{20,}"
    r"|[a-zA-Z0-9]{32,}|password\s*[:=]\s*\S+|api[_\-]?key\s*[:=]\s*\S+)",
    re.IGNORECASE
)

def _is_sensitive(text: str) -> bool:
    return bool(_SENSITIVE_RE.search(text))


# ── env check ─────────────────────────────────────────────────────────────────
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


# ── classifier ────────────────────────────────────────────────────────────────
def classify(text: str) -> str:
    """Call the LLM classifier — mirrors bot.py _classify()."""
    import openai
    from config import UCSD_API_KEY, UCSD_BASE_URL, LLM_CHAT_MODEL
    _llm = openai.OpenAI(api_key=UCSD_API_KEY, base_url=UCSD_BASE_URL)
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
        # debug: uncomment to see raw model output
        # print(f"  [debug] raw model output: {raw!r}")
        raw = raw.strip().lower()
        if "save" in raw:
            return "save"
        if "query" in raw:
            return "query"
        return "ignore"
    except Exception as e:
        return f"error: {e}"


def handle_classify(text: str):
    print("  → Calling LLM classifier...")
    result = classify(text)
    symbols = {"save": "💾", "query": "🔍", "ignore": "🔇"}
    symbol = symbols.get(result, "❓")
    print(f"  {symbol} Classified as: {result!r}")


# ── sensitive info detector ───────────────────────────────────────────────────
def handle_sensitive(text: str):
    match = _SENSITIVE_RE.search(text)
    if match:
        print(f"  🚨 SENSITIVE detected — matched: {match.group()!r}")
        print(f"  → This note would be shown to you but NOT fed to the LLM.")
    else:
        print(f"  ✅ Clean — no sensitive patterns detected.")


# ── shared save helper (similarity + sensitive check) ────────────────────────
def _do_save(text: str):
    """Check sensitive, check similarity, then save. Used by /save and neutral mode."""
    # Sensitive warning at save time
    if _is_sensitive(text):
        print("  ⚠ This note contains sensitive info (key/token/password).")
        choice = input("  Save anyway? (y/n) > ").strip().lower()
        if choice != "y":
            print("  ✗ Cancelled.")
            return

    # Similarity check
    existing = ingestion.find_similar_note(USER_ID, text)
    if existing:
        print(f"  ⚠ Similar note found (Note #{existing['id']}):")
        print(f"    Existing: {existing['content_text'][:120]!r}")
        print(f"    New:      {text[:120]!r}")
        choice = input("  Replace (r) / Keep both (k) / Cancel (c)? > ").strip().lower()
        if choice == "r":
            db.delete_note(existing["id"])
            embedder.delete(existing["id"])
            note = ingestion.ingest_text(USER_ID, text)
            print(f"  ✓ Replaced. New note #{note.id}")
        elif choice == "k":
            note = ingestion.ingest_text(USER_ID, text)
            print(f"  ✓ Kept both. New note #{note.id}")
        else:
            print("  ✗ Cancelled.")
    else:
        note = ingestion.ingest_text(USER_ID, text)
        print(f"  ✓ Saved as note #{note.id}")


def handle_save(text: str):
    _do_save(text)


# ── neutral input mode ────────────────────────────────────────────────────────
def handle_neutral(text: str):
    """Mirrors Discord bot plain-text-outside-thread behavior exactly."""
    print("  → Neutral input mode: classifying with LLM...")
    intent = classify(text)
    print(f"  → Intent: {intent!r}")

    if intent == "save":
        _do_save(text)
    elif intent == "query":
        handle_ask(text)
    else:
        print("  → Ignored (classified as chit-chat/command).")


# ── image ─────────────────────────────────────────────────────────────────────
async def handle_image(path: str):
    path = path.strip()
    if not os.path.exists(path):
        print(f"  ✗ File not found: {path}")
        return
    with open(path, "rb") as f:
        image_bytes = f.read()

    import extractor_ocr
    import extractor_vision
    from models import Note

    print("  → Running OCR...")
    ocr_text, is_sparse = extractor_ocr.extract(image_bytes)
    print(f"  → OCR words: {len(ocr_text.split())} | sparse: {is_sparse}")

    if is_sparse:
        print("  → OCR sparse, calling Vision model...")
        try:
            content_text = extractor_vision.extract(image_bytes)
            ocr_failed = False
            print("  → Vision succeeded.")
        except Exception as e:
            print(f"  ✗ Vision failed: {e}")
            content_text = ocr_text or "[extraction failed]"
            ocr_failed = True
    else:
        content_text = ocr_text
        ocr_failed = False

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
    print(f"  Extracted preview: {content_text[:200]!r}")


# ── ask ───────────────────────────────────────────────────────────────────────
def handle_ask(question: str):
    print("  → Retrieving + generating answer...")
    try:
        reply, safe_notes, sensitive_notes = conversation.answer(THREAD_ID, USER_ID, question)
        print(f"\n  SnapVault: {reply}\n")
        if safe_notes:
            print(f"  (grounded on {len(safe_notes)} note(s) fed to LLM):")
            for n in safe_notes:
                print(f"    • [#{n['id']}] {n['content_text'][:80]!r}")
        else:
            print("  (no relevant notes found)")
        if sensitive_notes:
            print(f"\n  🚨 {len(sensitive_notes)} sensitive note(s) retrieved but STRIPPED from LLM:")
            for n in sensitive_notes:
                print(f"    • [#{n['id']}] {n['content_text'][:80]!r}")
    except Exception as e:
        print(f"  ✗ Error: {e}")


# ── delete ────────────────────────────────────────────────────────────────────
def handle_delete(arg: str):
    try:
        note_id = int(arg.strip().lstrip("#"))
    except ValueError:
        print("  ✗ Usage: /delete <id>  e.g. /delete 10")
        return
    notes = db.get_notes_by_ids([note_id])
    if not notes or notes[0].get("user_id") != USER_ID:
        print(f"  ✗ Note #{note_id} not found.")
        return
    db.delete_note(note_id)
    embedder.delete(note_id)
    print(f"  ✓ Note #{note_id} deleted from DB and vector index.")


# ── history ───────────────────────────────────────────────────────────────────
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
        print(f"  [#{r['id']}] {r['source_type']} | {r['timestamp'][:19]}")
        print(f"       {r['preview']!r}")


# ── remind ────────────────────────────────────────────────────────────────────
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


# ── main loop ─────────────────────────────────────────────────────────────────
async def main():
    print("=" * 55)
    print("  SnapVault CLI Test Harness")
    print("=" * 55)
    for line in check_env():
        print(line)
    print()
    db.init_db()
    print("  ✓ Database initialized")
    print()
    print("  Commands:")
    print("    /save <text>       — save a note (sensitive + similarity check)")
    print("    /image <path>      — save a local image")
    print("    /ask <question>    — query your notes")
    print("    /classify <text>   — test LLM classifier")
    print("    /sensitive <text>  — test sensitive-info detector")
    print("    /delete <id>       — delete a note by ID")
    print("    /history           — show saved notes")
    print("    /clear             — clear conversation history")
    print("    /remind <ISO> <msg>")
    print("    /quit")
    print()
    print("  No prefix → neutral input mode (classify then act, mirrors Discord bot)")
    print()

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
        elif raw.startswith("/classify "):
            handle_classify(raw[10:])
        elif raw.startswith("/sensitive "):
            handle_sensitive(raw[11:])
        elif raw.startswith("/delete "):
            handle_delete(raw[8:])
        elif raw == "/history":
            show_notes()
        elif raw == "/clear":
            conversation.clear(THREAD_ID)
            print("  ✓ Conversation history cleared")
        elif raw.startswith("/remind "):
            handle_remind(raw[8:])
        elif raw.startswith("/"):
            print("  Unknown command. Try /classify, /sensitive, /save, /image, /ask, /delete, /history, /clear, /remind, /quit")
        else:
            handle_neutral(raw)


if __name__ == "__main__":
    asyncio.run(main())