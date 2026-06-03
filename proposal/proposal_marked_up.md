# SnapVault — Personal Capture & Retrieval Discord Bot

### One-sentence description:
A Discord-based personal RAG assistant that allows users to save screenshots and notes, then retrieve and ask questions about them later using local vector search and vision-assisted models.

### Past project reference:
Assignment 2 — Screenshot Organizer. The original project extracted structured marketplace information. SnapVault generalizes this into a personal memory system capable of processing arbitrary screenshots, notes, schedules, and event flyers.
* **Original Repo**: [https://github.com/ucsd-cse-genai-programming-sp26/a2-document-scanner.git]
---

### Planned Technologies

* **Bot Framework: discord.py**
  ✅ Implemented. Serves as the primary user interface for note capture, multi-format image uploads, interactive retrieval, and reminder notifications.

* **RAG Framework: LlamaIndex**
  ✅ Implemented. Orchestrates embedding generation, vector space data routing, index construction, and top-k context retrieval pipelines.

* **LLM: GPT API**
  ⚠️ Changed and Implemented. Swapped generic OpenAI GPT endpoints for UCSD TritonAI-hosted models accessed via an OpenAI-compatible API layer for inference and vision extraction.

* **OCR: Tesseract**
  ✅ Implemented. Configured as the front-line raw text extraction engine for processing captured documents and high-contrast images.

* **Vision Fallback: Multimodal LLM**
  ✅ Implemented. Automatically executes when raw OCR returns low-confidence scores or when a screenshot requires semantic/spatial understanding over plain text.

* **Vector Store: ChromaDB**
  ✅ Implemented. Manages dense vector representations of parsed notes and images to enable semantic similarity searches.

* **Metadata Storage: SQLite**
  ✅ Implemented. Stores relational metadata tables, indexing timestamps, relational text logs, and user scheduling metrics.

* **Hosting: Railway**
  ❌ Not implemented. Dropped for the current MVP release cycle; execution remains hosted on local environments for demo and evaluation purposes.Will do it in later versions. 

---

### First Deliverable

* **Screenshot Ingestion Pipeline**
  * *Proposal*: OCR → Vision Fallback → Database Storage → "Saved ✓" confirmation response.
  * ✅ Implemented. Extracts text contents, compiles system descriptions, and securely embeds image vectors into the active data layer.

* **Text Note Ingestion**
  * *Proposal*: Save direct text string notes straight to storage.
  * ✅ Implemented. Directly registers alphanumeric inputs alongside automated tracking timestamps.

* **Contextual Question Answering**
  * *Proposal*: Pull top relevant files and answer queries strictly grounded on those references.
  * ✅ Implemented. Intercepts incoming queries, surfaces top matching reference blocks, and injects them as LLM grounding context.

* **Conversation Follow-ups**
  * *Proposal*: Isolate individual chat interactions within dedicated Discord channel threads.
  * ⚠️ Implemented differently. Maintains lightweight sliding conversational history windows directly across native channel spaces without forcing thread creation

  ---

### Rough Architecture

* **Discord UI Gateway Handler**
  ✅ Implemented. Classes inbound traffic as note ingestion, image uploads, algorithmic configuration prompts, or real-time query inputs.

* **Ingestion Controller Pipeline**
  ✅ Implemented. Groups native Discord messages into custom `Note` object arrays while dynamically tracking user captions bound to uploaded media.

* **OCR Parser Block**
  ✅ Implemented. Parses direct textual elements from uploaded files, supplying downstream vector nodes with structural text data.

* **Vision Synthesis Fallback**
  ✅ Implemented. Evaluates imagery lacking structural text to build comprehensive, semantically aware content descriptions.

* **Embedding & Storage Core**
  ✅ Implemented. Relies on TritonAI embedding nodes to populate database layers across both ChromaDB and SQLite relational schemas.

* **Semantic Query Engine**
  ✅ Implemented. Exposes matching memory blocks to users using styled Discord embeds, passing the payload to the generation prompt.

* **Conversational Context Manager**
  ✅ Implemented. Blends short-term interaction logs with active RAG context layers to avoid hallucinated LLM responses.

---

### After First Deliverable Goals

* **Discord Reminder System**
  ✅ Added and Implemented. Supports background tracking using command formats like `!remind 2026-07-01T09:00 Sign up for swimming class`.

* **Calendar Export Integration (.ics)**
  ❌ Not implemented. Shelved to focus on refining retrieval precision, vector indexing stability, and native chat integrations.

* **Multi-User Multi-Tenant Isolation**
  ❌ Not implemented. Deferred for the core MVP release; data scope is currently tailored to a single-user prototype profile.

---

### Additional Functionality Added

* **Unified Multimodal Memory Store**
  ✅ Added beyond original proposal. Merges text snippets, raw OCR extracts, semantic vision summaries, structural calendars, and event logs into a single retrieval index.

---

### Current Limitations
* Execution bound exclusively to local deployments (lacks a persistent cloud endpoint).
* No multi-tenant memory boundary partitions (accessible as a shared sandbox).
* Lacks automated engine detection hooks to suggest calendar events or reminder entries.
* No standalone `.ics` calendar format rendering engine.

---

### Next Steps
1. Hosting (prioritized) & updating neutral input(let user delete notes/update notes)
2. Introduce multi-user data segmentation and memory isolation policies. (not sure)
3. Develop automated event tracking and intelligent reminder prompt suggestions.
4. Boost retrieval performance by implementing hierarchical re-ranking mechanisms.
5. Scale up into production-ready cloud environments.
6. Build automated export engines for external `.ics` digital calendar syncs.