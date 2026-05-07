from llama_index.core import VectorStoreIndex
from app.db import get_vector_store
from app.logger import get_logger
from app.config import LLM
import time

logger = get_logger(__name__)

# 🔥 cargar índice desde PostgreSQL (NO reindexar)
vector_store = get_vector_store()
index = VectorStoreIndex.from_vector_store(vector_store)

def query_index(question):
    logger.info(f"❓ Pregunta: {question}")

    engine = index.as_query_engine(
        similarity_top_k=5,
        llm=LLM   # 🔥 AQUÍ USAMOS EL LLM
    )

    start = time.time()
    response = engine.query(question)
    end = time.time()

    logger.info(f"⏱ Respuesta en {end - start:.2f}s")

    try:
        for i, node in enumerate(response.source_nodes):
            logger.debug(f"🔎 Fuente {i}: {node.text[:200]}")
    except:
        logger.warning("⚠️ No hay contexto")

    return response