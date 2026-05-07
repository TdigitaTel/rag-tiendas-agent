import os
from dotenv import load_dotenv

from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

load_dotenv()

# 🔥 LLM explícito
LLM = OpenAI(
    model="gpt-4o-mini",
    temperature=0
)

# 🔥 Embeddings explícitos
EMBED_MODEL = OpenAIEmbedding(
    model="text-embedding-3-small"
)

DB_CONFIG = {
    "database": os.getenv("DB_NAME"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "table_name": "pdf_embeddings",
    "embed_dim": 1536
}

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")