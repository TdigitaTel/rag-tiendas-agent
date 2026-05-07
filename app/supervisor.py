from app.logger import get_logger
from app.asesor import asesor_rag
from app.asesor_stock import asesor_stock
from app.config import LLM

logger = get_logger(__name__)

def decidir_tool(question: str) -> str:
    prompt = f"""
Eres un sistema que decide qué herramienta usar.

Opciones:
- stock → preguntas sobre inventario, productos, existencias
- rag → direcciones, teléfonos, información general

Responde SOLO con:
stock
rag

Pregunta:
{question}
"""

    response = LLM.complete(prompt)
    decision = response.text.strip().lower()

    return decision


def supervisor(question: str) -> str:
    logger.info(f"🧠 SUPERVISOR: {question}")

    tool = decidir_tool(question)

    logger.info(f"🔀 Tool elegida: {tool}")

    if "stock" in tool:
        return asesor_stock(question)

    return asesor_rag(question)