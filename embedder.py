import chromadb
from llama_index.core import Document, VectorStoreIndex, StorageContext, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
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

# Lower this if consolidation isn't triggering — 0.80 catches near-duplicates and typos
CONSOLIDATION_THRESHOLD = 0.80


def _get_index() -> VectorStoreIndex:
    vector_store = ChromaVectorStore(chroma_collection=_collection)
    storage_ctx = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex([], storage_context=storage_ctx)


def upsert(note_id: int, user_id: str, text: str):
    """Embed and store a Note in ChromaDB."""
    doc = Document(
        text=text,
        doc_id=str(note_id),
        metadata={"user_id": user_id, "note_id": note_id}
    )
    index = _get_index()
    index.insert(doc)


def _embed(text: str) -> list[float]:
    return Settings.embed_model.get_text_embedding(text)


def find_similar(user_id: str, text: str, top_k: int = 1) -> list[dict]:
    """
    Return up to top_k notes for this user with cosine similarity above threshold.
    Each result: {"note_id": int, "score": float}
    ChromaDB cosine distance is in [0, 2]; similarity = 1 - distance.
    """
    try:
        query_embedding = _embed(text)
        # Need at least 1 result; guard against empty collection
        count = _collection.count()
        if count == 0:
            return []
        n = min(top_k + 5, count)
        results = _collection.query(
            query_embeddings=[query_embedding],
            n_results=n,
            include=["metadatas", "distances"]
        )
    except Exception as e:
        print(f"[embedder.find_similar] error: {e}")
        return []

    matches = []
    if not results["ids"] or not results["ids"][0]:
        return matches

    for meta, distance in zip(results["metadatas"][0], results["distances"][0]):
        if meta.get("user_id") != user_id:
            continue
        similarity = 1 - distance   # cosine: 0=identical, 1=orthogonal
        print(f"[consolidation] note={meta['note_id']} similarity={similarity:.4f}")
        if similarity >= CONSOLIDATION_THRESHOLD:
            matches.append({"note_id": int(meta["note_id"]), "score": round(similarity, 4)})
        if len(matches) >= top_k:
            break

    return matches


def delete(note_id: int):
    try:
        _collection.delete(ids=[str(note_id)])
    except Exception as e:
        print(f"[embedder] delete failed for note {note_id}: {e}")