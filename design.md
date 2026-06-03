# SnapVault — Design Decisions

---

## Decision 1: Expanding Scope from Screenshot Organizer to General Personal Discord Bot

**90% my idea, 10% AI assistance**

The original A2 concept was a screenshot memory organizer, but the real value was always *personal capture and retrieval* — not screenshots specifically. I broadened the scope to accept both images and plain text, and chose Discord as the platform because it's already open, requires no custom frontend, and supports threads natively for follow-up conversations. The main tradeoff I thought through was multi-user isolation: if a group shares one bot instance, their memories would bleed into each other's retrieval context, so I scoped the MVP to single-user and left partitioning for later.

*I used AI to check Discord API feasibility and think through the multi-user isolation problem at the database level.*

---

## Decision 2: Hybrid OCR + Vision Model with a Sparsity Threshold

**90% my idea, 10% AI assistance**

A2 review feedback said OCR alone was sufficient and a Vision model was unnecessary — I agreed for text-heavy screenshots, but disagreed for the general case. OCR silently fails on low-text images (a photo of a bike, a meme, a product shot), returning near-empty output that's useless for retrieval. My solution was a threshold: run Tesseract first, and if the extracted text is too sparse, fall back to a Vision model (`api-gemma-4-26b`) to describe the image instead. This keeps the fast, cheap OCR path for the common case while recovering value where OCR genuinely can't help.

*I used AI to check feasibility and work through the threshold implementation — specifically whether character count was more reliable than Tesseract's confidence scores.*

---

## Decision 3: RAG Pipeline with SQLite + ChromaDB

**80% my idea, 20% AI assistance**

Keyword search would break on semantic queries like "what bikes was I looking at?" — so the retrieval layer uses embeddings and RAG. Saved notes are stored in SQLite as ground truth, embedded via UCSD's `api-tgpt-embeddings`, and indexed in a local ChromaDB vector store. At query time, the question is embedded, top-k similar notes are retrieved, and passed as context to `api-gpt-oss-120b` for a grounded answer. The key structural choice was keeping SQLite and ChromaDB separate: if the vector index ever needs to be rebuilt, the source data is safe in SQLite. The main known limitation is that the in-memory conversation buffer per thread is lost on bot restart, which is acceptable for a personal tool.

*I used AI to work through the database schema split, pipeline ordering, and whether LlamaIndex was the right abstraction over calling ChromaDB directly.*

---

*Last updated: June.1 2026*