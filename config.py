import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
UCSD_API_KEY = os.getenv("UCSD_API_KEY", "")
UCSD_BASE_URL = "https://tritonai-api.ucsd.edu"

# OCR Configuration
OCR_SPARSE_THRESHOLD = 50       # words; below this triggers Vision fallback

# Retrieval Configuration
TOP_K = 5                        # number of Notes returned per query
CHROMA_PERSIST_DIR = "./chroma_db"
CHROMA_COLLECTION = "snapvault"

# Conversation History
MAX_THREAD_HISTORY = 8           # turns kept in memory per thread

# UCSD Split-Model Architecture
LLM_CHAT_MODEL = "api-gpt-oss-120b"    # Heavyweight model for reasoning & chat
LLM_VISION_MODEL = "api-gemma-4-26b"   # Multimodal model for image processing
LLM_EMBED_MODEL = "api-tgpt-embeddings"
LLM_MAX_TOKENS = 1024


# Databases & Files
DB_PATH = "./snapvault.db"
UPLOADS_DIR = "./uploads"