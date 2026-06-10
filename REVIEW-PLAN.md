# SnapVault — Review Plan

## Feedback Received

### From Reviewers (Review Day)
- Bot should have a **neutral input mode** — every message being auto-saved or auto-queried based on phrasing heuristics felt unpredictable; users should have explicit control over what gets stored
- Add **Discord slash commands** (`/save`, `/ask`, `/remind`) — slash commands surface as autocomplete in Discord, making the bot discoverable to new users without reading docs
- Address **sensitive information** — no guardrail existed for saving API keys, passwords, or tokens into the RAG store or feeding them to the LLM

### From Staff Feedback
- Bot should have a **neutral input mode**
- Sensitive info guardrail for passwords and keys

---

## Fixes and Features Implemented in Response

**Neutral input mode** (`bot.py` `_classify()`)
- Replaced regex-based question detection with an LLM classifier
- Plain text outside threads is classified as save / query / event / ignore
- Slash commands added as the explicit path; natural language as the lazy path

**Slash commands** (`bot.py` `tree.*`)
- `/save`, `/ask`, `/list`, `/delete`, `/remind`, `/event`, `/connect_calendar`, `/help`
- All commands are ephemeral where appropriate (only visible to the user)

**Sensitive info guardrail** (`conversation.py` `_is_sensitive()`, `bot.py` `SensitiveNoteView`)
- Regex detection at save time: flags API keys, tokens, passwords, long hex strings
- User shown options: Keep Private (excluded from LLM) / Allow into LLM / Delete
- At retrieval time: sensitive notes shown directly to user but stripped from LLM context

**Structured AI prompts** (`conversation.py`)
- System prompt explicitly instructs: answer using ONLY the provided notes, be concise, say so if the answer isn't in the notes
- Prevents hallucination by design

**Note consolidation** (`embedder.py`, `ingestion.py`, `bot.py` `ConsolidationView`)
- On every save, similarity check against existing notes
- If similar note found (cosine > 0.85), user shown both with Replace / Keep Both / Discard buttons
- Keeps the store from growing unbounded with duplicate or superseded information

**Discord message sync** (`bot.py` `on_message_edit`, `on_message_delete`)
- Editing a saved message updates the note in storage
- Deleting a saved message removes the note from SQLite and ChromaDB

**Google Calendar integration** (`calendar_auth.py`, `calendar_service.py`)
- Identified as higher-value than `.ics` export
- `/event` command parses natural language event descriptions via LLM
- OAuth2 flow with Railway-hosted callback; tokens persisted per user in SQLite
