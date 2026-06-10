# SnapVault — Personal Capture & Retrieval Discord Bot
# Updated Proposal (Final State)

## One Sentence Description
A Discord bot where you forward any screenshot or note to build a personal searchable memory and ask questions (Personal RAG).

## Past Project Reference
Builds on **A2 — Screenshot Organizer**, which implemented extraction from Facebook listing screenshots. That project's core insight carries forward: screenshots contain valuable unstructured information worth extracting and retrieving. The ingestion and OCR/Vision pipeline is reused and generalized from Facebook listings to any personal screenshot.

GitHub: *[repo link](https://github.com/ucsd-cse-genai-programming-sp26/a2-document-scanner.git)*

---

## Planned Technologies

| Category | Technology | Status |
|----------|------------|--------|
| Bot framework | `discord.py` | ✅ Implemented as planned |
| RAG framework | LlamaIndex | ✅ Implemented as planned — `embedder.py`, `query_engine.py` |
| LLM | GPT API | ⚠️ Changed — swapped to UCSD TritonAI-hosted models (`api-gpt-oss-120b`, `api-gemma-4-26b`) via OpenAI-compatible API layer. Same interface, different endpoint. `config.py` |
| OCR | Tesseract + VLM fallback | ✅ Implemented as planned — `extractor_ocr.py`, `extractor_vision.py` |
| Vector store | ChromaDB | ✅ Implemented as planned — `embedder.py`, `query_engine.py` |
| Metadata + reminders | SQLite | ✅ Implemented as planned — `db.py` |
| Hosting | Railway | ✅ Implemented — deployed at `discord-bot-production-fe87.up.railway.app`. Note: Railway uses an ephemeral filesystem; SQLite and ChromaDB don't persist across redeploys without a mounted volume. |
| Language | Python 3.11+ | ✅ Implemented as planned |

---

## MVP — First Deliverable

**1. Screenshot ingestion pipeline**
- *Proposed*: OCR → Vision fallback → DB storage → "Saved ✓"
- ✅ Implemented as proposed. `ingestion.py` → `extractor_ocr.py` → `extractor_vision.py` (sparsity threshold: < 50 words triggers Vision) → `db.py` + `embedder.py`
- ⚠️ Extended: now also checks for sensitive content (API keys, tokens) at save time and prompts user with Keep Private / Allow LLM / Delete buttons (`bot.py` `SensitiveNoteView`)

**2. Text note ingestion**
- *Proposed*: Save direct text notes to storage
- ✅ Implemented as proposed. `ingestion.ingest_text()` → SQLite + ChromaDB
- ⚠️ Extended: added similarity check on save — if a similar note exists (cosine similarity > 0.85), user is shown both notes and asked to Replace / Keep Both / Discard (`bot.py` `ConsolidationView`, `embedder.find_similar()`)

**3. Contextual question answering**
- *Proposed*: Retrieve top relevant saves, return grounded answer + Discord embeds
- ✅ Implemented as proposed. `query_engine.py` → `conversation.py` → Discord embeds via `_make_embed()`
- ⚠️ Extended: sensitive notes retrieved but stripped from LLM context, shown directly to user with a warning (`conversation.py` `_is_sensitive()`)

**4. Conversation follow-ups**
- *Proposed*: Isolate interactions within dedicated Discord threads
- ⚠️ Implemented differently. Thread detection used as a signal (if already in a thread → always query) but threads are not auto-created. Short-term history buffer maintained per channel/thread ID in memory (`conversation.py` `_history` dict). Threads can be created manually for follow-up context.

---

## Rough Architecture

**1. Discord Handler** (`bot.py`)
- ✅ Implemented as proposed
- ⚠️ Extended: added LLM-based input classifier (`_classify()`) that routes plain text to save / query / event / ignore — replaces the original regex-based question detection. Also added slash commands (`/save`, `/ask`, `/list`, `/delete`, `/remind`, `/event`, `/connect_calendar`, `/help`) for explicit intent.

**2. Ingestion Pipeline** (`ingestion.py`)
- ✅ Implemented as proposed
- ⚠️ Extended: `find_similar_note()` for consolidation check; `discord_message_id` tracked per note so edits/deletes in Discord sync to storage

**3. OCR Extractor** (`extractor_ocr.py`)
- ✅ Implemented as proposed. Sparsity threshold: < 50 words flags for Vision fallback

**4. Vision Extractor** (`extractor_vision.py`)
- ✅ Implemented as proposed. Uses `api-gemma-4-26b`

**5. Embedding & Storage** (`embedder.py`)
- ✅ Implemented as proposed
- ⚠️ Extended: added `find_similar()` for consolidation and `delete()` for note removal from vector index

**6. Query Engine** (`query_engine.py`)
- ✅ Implemented as proposed. Top-k retrieval filtered by `user_id`

**7. Conversation Manager** (`conversation.py`)
- ✅ Implemented as proposed
- ⚠️ Extended: sensitive note filtering before LLM context injection; returns three values: `(reply, safe_notes, sensitive_notes)`

---

## After First Deliverable Goals

**Reminders**
- ✅ Implemented. `reminders.py` background loop checks SQLite every 60s, DMs user on due reminders. `/remind 2026-07-01T09:00 message` command in `bot.py`

**Calendar export (.ics)**
- ⚠️ Changed and implemented differently. Instead of exporting `.ics` files, implemented live Google Calendar integration via OAuth2. `/event` command parses natural language event descriptions via LLM and creates real Google Calendar events. `calendar_auth.py`, `calendar_service.py`. OAuth callback served by aiohttp web server on port 8080, hosted on Railway.
- Having deployment issues, so reverted back now.

---

## Additional Features Added (Beyond Original Proposal)

- **Neutral input mode** — LLM classifier routes plain text without requiring explicit slash commands
- **Slash commands** — `/save`, `/ask`, `/list`, `/delete`, `/event`, `/remind`, `/help`
- **Sensitive info guardrail** — regex detection at save time and retrieval time; sensitive notes excluded from LLM context by default with user override
- **Note consolidation** — similarity check on every save with user-controlled Replace / Keep Both / Discard UI
- **Discord message sync** — editing or deleting a Discord message updates or removes the corresponding note
- **Live deployment** — Railway deployment with OAuth callback server
