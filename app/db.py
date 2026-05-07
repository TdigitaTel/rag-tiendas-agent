from llama_index.vector_stores.postgres import PGVectorStore
from app.config import DB_CONFIG
from app.logger import get_logger
from llama_index.vector_stores.postgres import PGVectorStore
from app.config import DB_CONFIG
from app.logger import get_logger

logger = get_logger(__name__)

def get_vector_store():
    logger.info("🔌 Conectando a PostgreSQL")

    store = PGVectorStore.from_params(
        database=DB_CONFIG["database"],
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        table_name=DB_CONFIG["table_name"],
        embed_dim=DB_CONFIG["embed_dim"],
        perform_setup=True
    )

    logger.info("✅ PostgreSQL listo")
    return store