# SnapVault — Personal Capture & Retrieval Discord Bot

## One Sentence Description
A Discord bot where you forward any screenshot or note to build a personal searchable memory and ask questions(Personal RAG).

## Past Project Reference
Builds on **A2 — Screenshot Organizer**, which implemented  extraction from facebook-listing screenshots. That project's core insight carries forward: screenshots contain valuable unstructured information worth extracting and retrieving. The ingestion and OCR/Vision pipeline is reused and generalized from Facebook listings to any personal screenshot.

GitHub: *[repo link](https://github.com/ucsd-cse-genai-programming-sp26/a2-document-scanner.gitt)*

---

## Planned Technologies

| Category | Technology |
|----------|------------|
| Bot framework | `discord.py` |
| RAG framework | LlamaIndex (handles chunking, embedding, retrieval loop) |
| LLM |gpt API |
| OCR | Tesseract (primary); VLM (fallback for low-text images) |
| Vector store | ChromaDB |
| Metadata + reminders | SQLite |
| Hosting | Railway (deploy from GitHub) |
| Language | Python 3.11+ |

LlamaIndex handles the embedding/retrieval pipeline boilerplate. The Discord integration, image ingestion pipeline, database schema, and conversation layer are designed and owned by myself.

---

## MVP — First Deliverable
1. User forwards a screenshot → bot runs OCR; if sparse, falls back to Claude Vision → stores extracted text + image → replies "Saved ✓"
2. User sends a text note → stored directly → "Saved ✓"  
3. User asks "what bikes am I looking at?" → bot retrieves top relevant saves, returns:
   - Original items as Discord embeds (thumbnail + extracted text)
   - A short direct answer grounded in those saves
4. User follows up "which was cheaper?" → bot maintains thread context, responds

---

## Rough Architecture

**1. Discord Handler**
- Input: Discord message event (text, image, or thread follow-up)
- Output: routes to Ingestion Pipeline or Conversation Manager
- Logic: active thread → Conversation Manager; question phrasing → Conversation Manager with retrieval; otherwise → Ingestion

**2. Ingestion Pipeline**
- Input: message content (text and/or image bytes) + user_id + timestamp
- Output: structured `Note` object
- Effect: writes to SQLite, triggers Embedding & Storage
- Dispatches to OCR Extractor or Vision Extractor based on content type

**3. OCR Extractor**
- Input: image bytes
- Output: extracted text string
- If result < 50 words → flags for Vision fallback
- Default path, no API cost

**4. Vision Extractor (fallback)**
- Input: image bytes
- Output: natural language description + any detected structured fields
- One Claude Vision API call
- Only called when OCR is insufficient

**5. Embedding & Storage (via LlamaIndex)**
- Input: Note with content_text populated
- Output: vector in ChromaDB + metadata row in SQLite
- Persists both stores; namespaced by user_id

**6. Query Engine (via LlamaIndex)**
- Input: natural language query + user_id
- Output: top-k relevant Notes
- Embeds query, cosine similarity against user's ChromaDB namespace, returns ranked Notes with image paths

**7. Conversation Manager**
- Input: user message + top-k retrieved Notes + last ~8 turns from thread (short-term buffer)
- Output: Discord reply with (a) original saves as embeds and (b) LLM-generated answer
- Posts reply, opens or continues a Discord thread for follow-up

---

## After First Deliverable Goals

- **Reminders** — "remind me about this Friday" → bot DMs at that time (SQLite scheduled job)
- **Calendar export** — detect date/event in a save, offer to export as `.ics` file

reference: https://medium.com/@animu/turning-discord-into-a-knowledge-engine-a-practical-rag-powered-bot-c4ae45b2ac48
https://github.com/ramsbaby/jarvis