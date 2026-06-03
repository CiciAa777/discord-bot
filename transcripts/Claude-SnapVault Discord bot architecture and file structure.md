# SnapVault Discord bot architecture and file structure

**Created:** 6/1/2026 9:44:09  
**Updated:** 6/1/2026 10:23:51  
**Exported:** 6/1/2026 14:00:16  
**Link:** [https://claude.ai/chat/1cba56b4-51c8-488e-a2e4-608ba3af7a9d](https://claude.ai/chat/1cba56b4-51c8-488e-a2e4-608ba3af7a9d)  

## User:

> 6/1/2026 9:44:09

> File: 

SnapVault — Personal Capture & Retrieval Discord Bot One Sentence Description A Discord bot where you forward any screenshot or note to build a personal searchable memory and ask questions(Personal RAG). Past Project Reference Builds on A2 — Screenshot Organizer, which implemented extraction from facebook-listing screenshots. That project's core insight carries forward: screenshots contain valuable unstructured information worth extracting and retrieving. The ingestion and OCR/Vision pipeline is reused and generalized from Facebook listings to any personal screenshot. GitHub: repo link Planned Technologies Category Technology Bot framework discord.py RAG framework LlamaIndex (handles chunking, embedding, retrieval loop) LLM gpt API OCR Tesseract (primary); VLM (fallback for low-text images) Vector store ChromaDB Metadata + reminders SQLite Hosting Railway (deploy from GitHub) Language Python 3.11+ LlamaIndex handles the embedding/retrieval pipeline boilerplate. The Discord integration, image ingestion pipeline, database schema, and conversation layer are designed and owned by myself. MVP — First Deliverable 1. User forwards a screenshot → bot runs OCR; if sparse, falls back to Claude Vision → stores extracted text + image → replies "Saved ✓" 2. User sends a text note → stored directly → "Saved ✓" 3. User asks "what bikes am I looking at?" → bot retrieves top relevant saves, returns: Original items as Discord embeds (thumbnail + extracted text) A short direct answer grounded in those saves 4. User follows up "which was cheaper?" → bot maintains thread context, responds proposal.md 2026-05-20 1 / 3 Rough Architecture 1. Discord Handler Input: Discord message event (text, image, or thread follow-up) Output: routes to Ingestion Pipeline or Conversation Manager Logic: active thread → Conversation Manager; question phrasing → Conversation Manager with retrieval; otherwise → Ingestion 2. Ingestion Pipeline Input: message content (text and/or image bytes) + user_id + timestamp Output: structured Note object Effect: writes to SQLite, triggers Embedding & Storage Dispatches to OCR Extractor or Vision Extractor based on content type 3. OCR Extractor Input: image bytes Output: extracted text string If result < 50 words → flags for Vision fallback Default path, no API cost 4. Vision Extractor (fallback) Input: image bytes Output: natural language description + any detected structured fields One Claude Vision API call Only called when OCR is insufficient 5. Embedding & Storage (via LlamaIndex) Input: Note with content_text populated Output: vector in ChromaDB + metadata row in SQLite Persists both stores; namespaced by user_id 6. Query Engine (via LlamaIndex) Input: natural language query + user_id Output: top-k relevant Notes Embeds query, cosine similarity against user's ChromaDB namespace, returns ranked Notes with image paths 7. Conversation Manager Input: user message + top-k retrieved Notes + last ~8 turns from thread (short-term buffer) Output: Discord reply with (a) original saves as embeds and (b) LLM-generated answer Posts reply, opens or continues a Discord thread for follow-up After First Deliverable Goals proposal.md 2026-05-20 2 / 3 Reminders — "remind me about this Friday" → bot DMs at that time (SQLite scheduled job) Calendar export — detect date/event in a save, offer to export as .ics file

This is the final project I'm working towards, I previously had done a project as attached. shall we based on our previous one to edit or just help me regenerate new files? before generating, give me a clear plan/structure, what file do what

````markdown
# ReSnap — Screenshot Memory Engine

Upload screenshots. ReSnap extracts text, tags content, and organizes everything into browsable categories with AI-generated summaries.
- **Timeline** — upload screenshots and browse them in order
- **Categories** — auto-organized by topic (Travel, Food, Shopping, etc.)
- **Insights** — AI summaries of screenshot clusters

---

## Setup & Running

1. Install Python dependencies:
```bash
cd "a2-screenshot-memory-engine"
pip install fastapi uvicorn python-multipart anthropic pillow pytesseract sentence-transformers
```

2. Install frontend dependencies:
```bash
cd "a2-screenshot-memory-engine/frontend"
npm install
```
3. Terminal 1 — Backend
```bash
cd "a2-screenshot-memory-engine"
python main.py
```
For quick test: 
```bash
python extractor.py path/to/your/image.png
```
4. Terminal 2 — Frontend
```bash
cd "a2-screenshot-memory-engine/frontend"
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## Demo

[Watch the Project Walkthrough](https://www.youtube.com/watch?v=djhqzQZKvP8)

---

## Project Structure

````
a2-screenshot-memory-engine/
├── main.py              # FastAPI backend
├── extractor.py         # OCR + tagging + embedding
├── clusterer.py         # Groups similar screenshots
├── summarizer.py        # LLM cluster summaries
├── db.py                # SQLite database
├── uploads/             # Stored images (auto-created)
└── frontend/
    └── src/
        ├── App.tsx      # Main UI
        └── main.tsx     # Entry point
```

---

## Architecture

```
Upload
  │
  ▼
FastAPI (main.py)
  │  saves to /uploads/, triggers background task
  ▼
extractor.py — OCR → tags → category → embedding
  │
  ▼
clusterer.py — groups by similarity
  │
  ▼
summarizer.py — LLM summary on demand
  │
  ▼
SQLite (db.py)
  │
  ▼
React Frontend — Timeline / Categories / Insights
```

---
```

## Assistant:

> 6/1/2026 9:44:32

Let me read through both documents carefully and give you a clear plan before writing a single line of code.

Looking at what you have (ReSnap) vs. what you're building (SnapVault), here's my assessment:

**What carries over well:**
- The OCR + Vision fallback logic from `extractor.py`
- The structured extraction concept (Three-Tier JSON)
- The embedding + similarity approach from `clusterer.py`
- The SQLite schema pattern from `db.py`

**What's fundamentally different:**
- ReSnap is a web app (FastAPI + React). SnapVault is a **Discord bot** — no frontend at all
- ReSnap uses sentence-transformers locally. SnapVault uses LlamaIndex to handle the embedding/retrieval pipeline
- ReSnap has no conversation layer. SnapVault needs thread-aware multi-turn chat
- Storage is ChromaDB (vectors) + SQLite (metadata), not just SQLite

---

## Recommended Approach: Rebuild with selective reuse

Don't retrofit ReSnap — the Discord bot architecture is different enough that shoehorning it would create messy code. Instead, **copy the extraction logic** and rebuild everything else clean.

---

## File Structure & Responsibilities

```
snapvault/
├── bot.py                  # Entry point — Discord client, event routing
├── ingestion.py            # Decides OCR vs Vision, builds Note object, writes to DB
├── extractor_ocr.py        # Tesseract OCR (ported from ReSnap's extractor.py)
├── extractor_vision.py     # Claude Vision fallback (replaces api-lightonocr-1b)
├── embedder.py             # LlamaIndex wrapper — embed + upsert to ChromaDB
├── query_engine.py         # LlamaIndex retrieval — query → top-k Notes
├── conversation.py         # Thread buffer (last 8 turns) + LLM answer generation
├── db.py                   # SQLite schema + CRUD (metadata, reminders)
├── models.py               # Note dataclass / schema
├── config.py               # API keys, thresholds, constants
├── requirements.txt
└── README.md
```

---

## What each file does

| File | Responsibility | Reused from ReSnap? |
|---|---|---|
| `bot.py` | Discord events, routing messages to ingestion or conversation | No — new |
| `ingestion.py` | Orchestrates the save flow: image or text → Note → DB + embed | Partial — logic from extractor.py |
| `extractor_ocr.py` | Tesseract extraction, sparse-text detection (<50 words triggers fallback) | Yes — port directly |
| `extractor_vision.py` | Claude Vision API call, returns description + structured fields | Partial — generalizes ReSnap's VLM fallback |
| `embedder.py` | LlamaIndex Document → ChromaDB upsert, namespaced by user_id | No — new (replaces clusterer.py) |
| `query_engine.py` | Embed query → cosine search in user's ChromaDB namespace → ranked Notes | No — new (replaces clusterer.py retrieval) |
| `conversation.py` | Holds last ~8 turns per thread, calls LLM with retrieved context, formats Discord embeds | No — new |
| `db.py` | SQLite: notes table (id, user_id, content_text, image_path, timestamp, source_type), reminders table | Partial — extend ReSnap's schema |
| `models.py` | `Note` dataclass with all fields | No — new, clean |
| `config.py` | `DISCORD_TOKEN`, `ANTHROPIC_API_KEY`, similarity threshold, OCR word threshold | No — new |

---

## Flow summary

```
Discord message
    │
    ├── has image or text? ──→ ingestion.py
    │       │
    │       ├── image → extractor_ocr.py → sparse? → extractor_vision.py
    │       ├── text → use directly
    │       │
    │       └── Note → db.py (SQLite) + embedder.py (ChromaDB)
    │                       └── reply "Saved ✓"
    │
    └── question / thread follow-up ──→ conversation.py
            │
            ├── query_engine.py → top-k Notes
            ├── thread buffer (last 8 turns)
            └── LLM call → Discord reply with embeds
```

---

**My recommendation:** Shall I generate all files in one shot, or go module by module (starting with `models.py` → `db.py` → extractors → bot)? Also — do you have a Discord bot token and app already created, or do you need setup guidance for that too?

## User:

> 6/1/2026 9:47:00

please generate in one shot, try to save token at same time. Don't have discord bot created yet

## Assistant:

> 6/1/2026 9:49:45

Let me read the skills and then generate everything.

> Viewed file
>
> - Check skills directory
> - **Done**

No relevant skill for Python bots. Generating all files now.

> Ran 4 commands, created 14 files, presented file
>
> - Create project directory
> - models.py - Note dataclass
> - config.py - all constants and env vars
> - db.py - SQLite schema and CRUD
> - extractor_ocr.py - Tesseract OCR with sparse detection
> - extractor_vision.py - Claude Vision fallback
> - embedder.py - LlamaIndex ChromaDB upsert
> - query_engine.py - LlamaIndex retrieval returning Note IDs
> - ingestion.py - orchestrates save flow
> - conversation.py - thread buffer and LLM answer generation
> - reminders.py - background scheduler for due reminders
> - bot.py - Discord client, event routing, all command handling
> - requirements.txt
> - .env.example - template for secrets
> - README.md with setup including Discord bot creation steps
> - Verify all files created
> - Confirm .env.example exists
> - find env example
> - Presenting file(s)...
> - **Done**

All 13 files generated. Here's a quick orientation:

**Boot order when you run `python bot.py`:**
`bot.py` → `db.init_db()` → starts `reminders.reminder_loop()` as background task → listens for Discord events

**The two main flows:**

| Flow | Files touched |
|---|---|
| Save image | `bot.py` → `ingestion.py` → `extractor_ocr` → `extractor_vision` (fallback) → `db.py` + `embedder.py` |
| Ask question | `bot.py` → `conversation.py` → `query_engine.py` → `db.py` → Anthropic API |

**First thing to do — create your Discord bot (takes ~5 min):**
1. Go to https://discord.com/developers/applications → **New Application**
2. **Bot** tab → **Add Bot** → copy the token
3. Enable **Message Content Intent** (required or the bot can't read messages)
4. **OAuth2 → URL Generator**: scopes `bot`, permissions: Send Messages, Read History, Create Threads, Add Reactions
5. Paste that URL in your browser to invite it to your server
6. Copy token into `.env` alongside your `ANTHROPIC_API_KEY`

Then `pip install -r requirements.txt` and `python bot.py`.

> File: [/home/claude/snapvault/bot.py](https://claude.ai/api/organizations/291c1b10-c4f9-4c59-8d37-2e45e63fd468/conversations/1cba56b4-51c8-488e-a2e4-608ba3af7a9d/wiggle/download-file?path=%2Fhome%2Fclaude%2Fsnapvault%2Fbot.py)

> File: [/home/claude/snapvault/ingestion.py](https://claude.ai/api/organizations/291c1b10-c4f9-4c59-8d37-2e45e63fd468/conversations/1cba56b4-51c8-488e-a2e4-608ba3af7a9d/wiggle/download-file?path=%2Fhome%2Fclaude%2Fsnapvault%2Fingestion.py)

> File: [/home/claude/snapvault/conversation.py](https://claude.ai/api/organizations/291c1b10-c4f9-4c59-8d37-2e45e63fd468/conversations/1cba56b4-51c8-488e-a2e4-608ba3af7a9d/wiggle/download-file?path=%2Fhome%2Fclaude%2Fsnapvault%2Fconversation.py)

> File: [/home/claude/snapvault/db.py](https://claude.ai/api/organizations/291c1b10-c4f9-4c59-8d37-2e45e63fd468/conversations/1cba56b4-51c8-488e-a2e4-608ba3af7a9d/wiggle/download-file?path=%2Fhome%2Fclaude%2Fsnapvault%2Fdb.py)

> File: [/home/claude/snapvault/extractor_ocr.py](https://claude.ai/api/organizations/291c1b10-c4f9-4c59-8d37-2e45e63fd468/conversations/1cba56b4-51c8-488e-a2e4-608ba3af7a9d/wiggle/download-file?path=%2Fhome%2Fclaude%2Fsnapvault%2Fextractor_ocr.py)

> File: [/home/claude/snapvault/extractor_vision.py](https://claude.ai/api/organizations/291c1b10-c4f9-4c59-8d37-2e45e63fd468/conversations/1cba56b4-51c8-488e-a2e4-608ba3af7a9d/wiggle/download-file?path=%2Fhome%2Fclaude%2Fsnapvault%2Fextractor_vision.py)

> File: [/home/claude/snapvault/embedder.py](https://claude.ai/api/organizations/291c1b10-c4f9-4c59-8d37-2e45e63fd468/conversations/1cba56b4-51c8-488e-a2e4-608ba3af7a9d/wiggle/download-file?path=%2Fhome%2Fclaude%2Fsnapvault%2Fembedder.py)

> File: [/home/claude/snapvault/query_engine.py](https://claude.ai/api/organizations/291c1b10-c4f9-4c59-8d37-2e45e63fd468/conversations/1cba56b4-51c8-488e-a2e4-608ba3af7a9d/wiggle/download-file?path=%2Fhome%2Fclaude%2Fsnapvault%2Fquery_engine.py)

> File: [/home/claude/snapvault/reminders.py](https://claude.ai/api/organizations/291c1b10-c4f9-4c59-8d37-2e45e63fd468/conversations/1cba56b4-51c8-488e-a2e4-608ba3af7a9d/wiggle/download-file?path=%2Fhome%2Fclaude%2Fsnapvault%2Freminders.py)

> File: [/home/claude/snapvault/models.py](https://claude.ai/api/organizations/291c1b10-c4f9-4c59-8d37-2e45e63fd468/conversations/1cba56b4-51c8-488e-a2e4-608ba3af7a9d/wiggle/download-file?path=%2Fhome%2Fclaude%2Fsnapvault%2Fmodels.py)

> File: [/home/claude/snapvault/config.py](https://claude.ai/api/organizations/291c1b10-c4f9-4c59-8d37-2e45e63fd468/conversations/1cba56b4-51c8-488e-a2e4-608ba3af7a9d/wiggle/download-file?path=%2Fhome%2Fclaude%2Fsnapvault%2Fconfig.py)

> File: [/home/claude/snapvault/requirements.txt](https://claude.ai/api/organizations/291c1b10-c4f9-4c59-8d37-2e45e63fd468/conversations/1cba56b4-51c8-488e-a2e4-608ba3af7a9d/wiggle/download-file?path=%2Fhome%2Fclaude%2Fsnapvault%2Frequirements.txt)

> File: [/home/claude/snapvault/README.md](https://claude.ai/api/organizations/291c1b10-c4f9-4c59-8d37-2e45e63fd468/conversations/1cba56b4-51c8-488e-a2e4-608ba3af7a9d/wiggle/download-file?path=%2Fhome%2Fclaude%2Fsnapvault%2FREADME.md)

## User:

> 6/1/2026 10:23:11

will this alow me to test my code on cmd or soemthing before trying out in discord?

## Assistant:

> 6/1/2026 10:23:51

Yes — you can write a simple CLI test harness that simulates the same flows without needing Discord at all.

Let me create one:

> Created file, presented file
>
> - CLI test harness for SnapVault without Discord
> - Presenting file(s)...
> - **Done**

Run it with:
```bash
python test_cli.py
```

What you can test from the prompt:

| Command | What it tests |
|---|---|
| `hello I found a great bike on craigslist for $400` | bare text → `ingestion` → `db` → `embedder` |
| `/save another note about a Trek mountain bike` | explicit save |
| `/image /path/to/screenshot.png` | full OCR → Vision fallback → embed pipeline |
| `/ask what bikes am I looking at?` | `query_engine` → `conversation` → Anthropic API |
| `which was cheaper?` (follow-up) | thread history maintained across turns |
| `/history` | shows all saved notes in SQLite |
| `/clear` | wipes conversation buffer |
| `/remind 2025-06-10T09:00 check bike price` | reminder insert → DB |

The key difference from Discord: `/image` reads a local file path directly instead of downloading from a Discord attachment URL, so you can test with any screenshot you have on disk. Everything else — OCR, Vision, embeddings, ChromaDB, the LLM conversation — runs identically to how it will in the real bot.

> File: [/home/claude/snapvault/test_cli.py](https://claude.ai/api/organizations/291c1b10-c4f9-4c59-8d37-2e45e63fd468/conversations/1cba56b4-51c8-488e-a2e4-608ba3af7a9d/wiggle/download-file?path=%2Fhome%2Fclaude%2Fsnapvault%2Ftest_cli.py)

Powered by Claude Exporter (https://www.ai-chat-exporter.net)
