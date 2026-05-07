from app.query import query_index
from app.logger import get_logger

logger = get_logger(__name__)

def asesor_rag(question: str) -> str:
    logger.info("📚 ASESOR: ejecutando RAG")

    response = query_index(question)

    return str(response)