"""
Ingestion pipeline for SnapVault.
- Images: OCR → Vision fallback → save + embed
- Text: save + embed, with difflib similarity check for consolidation
"""
import os
import uuid
import difflib
import aiohttp
from models import Note
from config import UPLOADS_DIR
import extractor_ocr
import extractor_vision
import db
import embedder
from sensitive import is_sensitive

os.makedirs(UPLOADS_DIR, exist_ok=True)

SIMILARITY_THRESHOLD = 0.80  # difflib ratio: 0=nothing in common, 1=identical


def find_similar_note(user_id: str, text: str) -> tuple[dict | None, float]:
    """
    Compare new text against the user's recent notes using difflib.
    Returns (most_similar_note_or_None, score).
    Pure Python — no API call, no embedding.
    """
    recent = db.get_recent_notes(user_id, limit=20)
    best_note, best_score = None, 0.0
    for note in recent:
        score = difflib.SequenceMatcher(
            None, text.lower(), note["content_text"].lower()
        ).ratio()
        if score > best_score:
            best_score = score
            best_note = note
    if best_score >= SIMILARITY_THRESHOLD:
        return best_note, round(best_score, 4)
    return None, 0.0


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
                discord_message_id: str = None) -> Note:
    note = Note(
        user_id=user_id,
        content_text=text,
        source_type="text",
        is_sensitive=is_sensitive(text),
        discord_message_id=discord_message_id
    )
    note.id = db.insert_note(note)
    embedder.upsert(note.id, user_id, text)
    return note


def update_note(note_id: int, new_text: str):
    """Update note text in SQLite and re-embed in ChromaDB."""
    db.update_note_text(note_id, new_text)
    db.update_note_sensitive(note_id, is_sensitive(new_text))
    embedder.delete(note_id)
    note_rows = db.get_notes_by_ids([note_id])
    if note_rows:
        embedder.upsert(note_id, note_rows[0]["user_id"], new_text)