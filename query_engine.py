import chromadb
from llama_index.core import Settings, StorageContext, VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai_like import OpenAILikeEmbedding

from config import (
    UCSD_API_KEY,
    UCSD_BASE_URL,
    LLM_EMBED_MODEL,
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION,
    TOP_K,
)

Settings.embed_model = OpenAILikeEmbedding(
    model_name=LLM_EMBED_MODEL,
    api_key=UCSD_API_KEY,
    api_base=UCSD_BASE_URL,
    is_embedding=True,
)

_chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
_collection = _chroma_client.get_or_create_collection(CHROMA_COLLECTION)


def retrieve(query: str, user_id: str) -> list[int]:
    vector_store = ChromaVectorStore(chroma_collection=_collection)
    storage_ctx = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex([], storage_context=storage_ctx)

    retriever = index.as_retriever(
        similarity_top_k=TOP_K * 3,
        filters=None,
    )
    nodes = retriever.retrieve(query)

    note_ids = []
    for node in nodes:
        meta = node.metadata or {}
        if meta.get("user_id") == user_id:
            note_ids.append(int(meta["note_id"]))
        if len(note_ids) >= TOP_K:
            break

    return note_ids