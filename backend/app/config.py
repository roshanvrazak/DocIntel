import os

# --- Ingestion ---
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# --- Retrieval ---
RETRIEVER_TOP_K = int(os.getenv("RETRIEVER_TOP_K", "5"))
RETRIEVAL_CACHE_TTL = int(os.getenv("RETRIEVAL_CACHE_TTL", "300"))  # seconds

# --- Validation ---
FAITHFULNESS_THRESHOLD = float(os.getenv("FAITHFULNESS_THRESHOLD", "0.8"))
VALIDATOR_MAX_RETRIES = int(os.getenv("VALIDATOR_MAX_RETRIES", "3"))

# --- LLM ---
LITELLM_PROXY_URL = os.getenv("LITELLM_PROXY_URL", "http://litellm:4000")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Maximum characters sent as context to any LLM call.
# ~4 chars/token → 200_000 chars ≈ 50k tokens, safely within Gemini 1.5 Pro's 1M window
# while avoiding slow/expensive calls on huge documents.
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "200000"))
