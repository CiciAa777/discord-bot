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


def upsert(note_id: int, user_id: str, text: str):
    """Embed and store a note in ChromaDB."""
    vec = Settings.embed_model.get_text_embedding(text)
    _collection.upsert(
        ids=[str(note_id)],
        embeddings=[vec],
        documents=[text],
        metadatas=[{"user_id": user_id, "note_id": note_id}]
    )


def delete(note_id: int):
    try:
        _collection.delete(ids=[str(note_id)])
    except Exception as e:
        print(f"[embedder] delete failed for note {note_id}: {e}")