"""
Ingestion pipeline for SnapVault.
- Images: OCR → Vision fallback → save + embed
- Text: save + embed, with LLM-powered similarity check for consolidation
"""
import os
import uuid
import aiohttp
import openai
from models import Note
from config import UPLOADS_DIR, UCSD_API_KEY, UCSD_BASE_URL, LLM_CHAT_MODEL
import extractor_ocr
import extractor_vision
import db
import embedder
from sensitive import is_sensitive

os.makedirs(UPLOADS_DIR, exist_ok=True)

_llm = openai.OpenAI(api_key=UCSD_API_KEY, base_url=UCSD_BASE_URL)


def llm_compare(existing_text: str, new_text: str) -> dict:
    """
    Ask LLM to compare two notes and decide what to do.
    Returns {"verdict": "duplicate"|"update"|"keep_both", "reason": str}
    """
    try:
        resp = _llm.chat.completions.create(
            model=LLM_CHAT_MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": (
                "Compare these two notes and classify their relationship.\n\n"
                f"Existing note: {existing_text}\n"
                f"New note: {new_text}\n\n"
                "Reply with exactly one of these verdicts and a short reason:\n"
                "- 'duplicate' if they contain the same information (including typos/rephrasing)\n"
                "- 'update' if the new note corrects or adds to the existing one\n"
                "- 'keep_both' if they are meaningfully different\n\n"
                "Format: <verdict>|<one sentence reason>"
            )}]
        )
        raw = (resp.choices[0].message.content or "").strip()
        parts = raw.split("|", 1)
        verdict = parts[0].strip().lower()
        reason = parts[1].strip() if len(parts) > 1 else ""
        if verdict not in ("duplicate", "update", "keep_both"):
            verdict = "keep_both"
        return {"verdict": verdict, "reason": reason}
    except Exception as e:
        print(f"[ingestion.llm_compare] error: {e}")
        return {"verdict": "keep_both", "reason": "Could not compare notes."}


def find_similar_note(user_id: str, text: str) -> tuple[dict | None, list[float], bool]:
    """
    Returns (existing_note_or_None, embedding, skip_llm).
    The embedding can be reused in ingest_text to avoid a second API call.
    skip_llm=True means the match is near-identical; llm_compare can be bypassed.
    """
    matches, embedding = embedder.find_similar_for_save(user_id, text)
    if not matches:
        return None, embedding, False
    notes = db.get_notes_by_ids([matches[0]["note_id"]])
    existing = notes[0] if notes else None
    return existing, embedding, matches[0].get("skip_llm", False)


async def ingest_image(user_id: str, image_url: str,
                       user_caption: str = "",
                       discord_message_id: str = None) -> Note:
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as resp:
            image_bytes = await resp.read()

    ext = image_url.split(".")[-1].split("?")[0] or "png"
    filename = f"{uuid.uuid4()}.{ext}"
    image_path = os.path.join(UPLOADS_DIR, filename)
    with open(image_path, "wb") as f:
        f.write(image_bytes)

    ocr_text, is_sparse = extractor_ocr.extract(image_bytes)
    ocr_failed = False

    if is_sparse:
        try:
            content_text = extractor_vision.extract(image_bytes)
        except Exception:
            content_text = ocr_text or "[Could not extract text from image]"
            ocr_failed = True
    else:
        content_text = ocr_text

    if user_caption:
        content_text = f"{content_text}\n\n[User Notes]: {user_caption}"

    note = Note(
        user_id=user_id,
        content_text=content_text,
        source_type="image",
        image_path=image_path,
        ocr_failed=ocr_failed,
        is_sensitive=is_sensitive(content_text),
        discord_message_id=discord_message_id
    )
    note.id = db.insert_note(note)
    embedder.upsert(note.id, user_id, content_text)
    return note


def ingest_text(user_id: str, text: str,
                discord_message_id: str = None,
                embedding: list[float] | None = None) -> Note:
    """
    Save a text note. Pass `embedding` to reuse a vector already computed
    during find_similar_note, avoiding a redundant embedding API call.
    """
    note = Note(
        user_id=user_id,
        content_text=text,
        source_type="text",
        is_sensitive=is_sensitive(text),
        discord_message_id=discord_message_id
    )
    note.id = db.insert_note(note)
    # Reuse the embedding if provided — skips a second round-trip
    embedder.upsert(note.id, user_id, text, embedding=embedding)
    return note


def update_note(note_id: int, new_text: str):
    """Update note text in SQLite and re-embed in ChromaDB."""
    db.update_note_text(note_id, new_text)
    db.update_note_sensitive(note_id, is_sensitive(new_text))
    embedder.delete(note_id)
    note_rows = db.get_notes_by_ids([note_id])
    if note_rows:
        embedder.upsert(note_id, note_rows[0]["user_id"], new_text)