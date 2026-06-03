"""
If a user sends an image with a caption, we treat them as one combined memory.
"""
import os
import uuid
import aiohttp
from models import Note
from config import UPLOADS_DIR
import extractor_ocr
import extractor_vision
import db
import embedder


os.makedirs(UPLOADS_DIR, exist_ok=True)


async def ingest_image(user_id: str, image_url: str, user_caption: str = "") -> Note:
    """Download image, OCR or Vision, save, embed."""
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as resp:
            image_bytes = await resp.read()

    # Save to disk
    ext = image_url.split(".")[-1].split("?")[0] or "png"
    filename = f"{uuid.uuid4()}.{ext}"
    image_path = os.path.join(UPLOADS_DIR, filename)
    with open(image_path, "wb") as f:
        f.write(image_bytes)

    # Extract text
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
    # ADD THIS STEP: Append their extra text description to the final notes block
    if user_caption:
        content_text = f"{content_text}\n\n[User Notes]: {user_caption}"

    note = Note(
        user_id=user_id,
        content_text=content_text,
        source_type="image",
        image_path=image_path,
        ocr_failed=ocr_failed
    )
    note.id = db.insert_note(note)
    embedder.upsert(note.id, user_id, content_text)
    return note


def ingest_text(user_id: str, text: str) -> Note:
    """Store a plain text note."""
    note = Note(user_id=user_id, content_text=text, source_type="text")
    note.id = db.insert_note(note)
    embedder.upsert(note.id, user_id, text)
    return note
