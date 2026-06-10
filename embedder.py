import chromadb
from llama_index.core import Settings
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION, UCSD_API_KEY, UCSD_BASE_URL, LLM_EMBED_MODEL

Settings.embed_model = OpenAILikeEmbedding(
    model_name=LLM_EMBED_MODEL,
    api_key=UCSD_API_KEY,
    api_base=UCSD_BASE_URL,
    is_embedding=True
)

_chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
_collection = _chroma_client.get_or_create_collection(
    CHROMA_COLLECTION,
    metadata={"hnsw:space": "cosine"}
)

# Similarity band for consolidation:
#   >= SKIP_THRESHOLD  → so similar that llm_compare is skipped; treat as duplicate outright
#   >= CONSOLIDATION_THRESHOLD (and < SKIP_THRESHOLD) → ask LLM to compare
#   <  CONSOLIDATION_THRESHOLD → no overlap, save immediately without any LLM call
CONSOLIDATION_THRESHOLD = 0.80
SKIP_LLM_THRESHOLD = 0.97   # near-identical text; no point asking the LLM


def _embed(text: str) -> list[float]:
    return Settings.embed_model.get_text_embedding(text)


def upsert(note_id: int, user_id: str, text: str, embedding: list[float] | None = None):
    """
    Store a note in ChromaDB.
    Pass `embedding` to reuse a vector already computed during find_similar_for_save,
    saving a second round-trip to the embedding API.
    """
    vec = embedding if embedding is not None else _embed(text)
    _collection.upsert(
        ids=[str(note_id)],
        embeddings=[vec],
        documents=[text],
        metadatas=[{"user_id": user_id, "note_id": note_id}]
    )


def find_similar_for_save(user_id: str, text: str) -> tuple[list[dict], list[float]]:
    """
    Returns (matches, embedding) so the caller can reuse the embedding in upsert()
    without a second API call.

    matches: list of {"note_id": int, "score": float, "skip_llm": bool}
      skip_llm=True means similarity is so high llm_compare can be bypassed.
    """
    try:
        query_embedding = _embed(text)
        count = _collection.count()
        if count == 0:
            return [], query_embedding
        n = min(6, count)
        results = _collection.query(
            query_embeddings=[query_embedding],
            n_results=n,
            include=["metadatas", "distances"]
        )
    except Exception as e:
        print(f"[embedder.find_similar_for_save] error: {e}")
        return [], []

    matches = []
    if not results["ids"] or not results["ids"][0]:
        return matches, query_embedding

    for meta, distance in zip(results["metadatas"][0], results["distances"][0]):
        if meta.get("user_id") != user_id:
            continue
        similarity = 1 - distance
        print(f"[consolidation] note={meta['note_id']} similarity={similarity:.4f}")
        if similarity >= CONSOLIDATION_THRESHOLD:
            matches.append({
                "note_id": int(meta["note_id"]),
                "score": round(similarity, 4),
                "skip_llm": similarity >= SKIP_LLM_THRESHOLD,
            })
            break   # only need the closest match

    return matches, query_embedding


# Keep the old find_similar for any callers outside the save path
def find_similar(user_id: str, text: str, top_k: int = 1) -> list[dict]:
    matches, _ = find_similar_for_save(user_id, text)
    return [{"note_id": m["note_id"], "score": m["score"]} for m in matches[:top_k]]


def delete(note_id: int):
    try:
        _collection.delete(ids=[str(note_id)])
    except Exception as e:
        print(f"[embedder] delete failed for note {note_id}: {e}")