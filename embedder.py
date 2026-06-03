import chromadb
from llama_index.core import Document, VectorStoreIndex, StorageContext, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
# MAKE SURE THIS LINE IS INCLUDED:
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION, UCSD_API_KEY, UCSD_BASE_URL, LLM_EMBED_MODEL

# Use OpenAILikeEmbedding to bypass native OpenAI string validation
Settings.embed_model = OpenAILikeEmbedding(
    model_name=LLM_EMBED_MODEL,
    api_key=UCSD_API_KEY,
    api_base=UCSD_BASE_URL,
    is_embedding=True
)

_chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
_collection = _chroma_client.get_or_create_collection(CHROMA_COLLECTION)


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