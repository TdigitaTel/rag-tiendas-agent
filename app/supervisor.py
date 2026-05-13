print("✅ Entro Supervisor")

from app.logger import get_logger
print("✅ entro logger")

from app.asesor import asesor_rag
print("✅ asesor_rag OK")

from app.asesor_stock import asesor_stock, consultar_stock, formatear_respuesta
print("✅ asesor_stock OK")

from app.config import LLM

logger = get_logger(__name__)


# ============================
# 🔀 DECISIÓN DE TOOL
# ============================
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
    return response.text.strip().lower()


# ============================
# 🧠 DETECTAR INTENCIÓN
# ============================
def detectar_intencion(texto: str) -> str:
    prompt = f"""
El usuario dijo: "{texto}"

Clasifica en UNA palabra:
- confirmacion
- rechazo
- nueva_consulta

Ejemplos:
"si" → confirmacion
"ok" → confirmacion
"vale" → confirmacion
"perfecto" → confirmacion

"no" → rechazo
"mejor no" → rechazo

"codo pvc" → nueva_consulta
"tienes tubos" → nueva_consulta
"fresas" → nueva_consulta

Respuesta:
"""
    return LLM.complete(prompt).text.strip().lower()


# ============================
# 🧠 SUPERVISOR CON CONTEXTO
# ============================
def supervisor(question: str, ctx: dict | None = None):
    logger.info(f"🧠 SUPERVISOR: {question}")
    logger.info(f"🧠 CONTEXTO: {ctx}")

    try:
        # ==========================================
        # 🔥 1. SI HAY CONTEXTO → DECIDIR INTENCIÓN
        # ==========================================
        if ctx and ctx.get("estado") == "esperando_confirmacion":

            intencion = detectar_intencion(question)
            logger.info(f"🧠 Intención detectada: {intencion}")

            # ============================
            # ✔ CONFIRMACIÓN
            # ============================
            if intencion == "confirmacion":
                articulos = ctx.get("articulos")

                if not articulos:
                    return "❌ Error recuperando resultados", None

                rows = consultar_stock(articulos)
                respuesta = formatear_respuesta(rows)

                return respuesta, None  # limpiar contexto

            # ============================
            # ❌ RECHAZO
            # ============================
            elif intencion == "rechazo":
                return "Perfecto 👍 dime más detalles del producto", None

            # ============================
            # 🆕 NUEVA CONSULTA
            # ============================
            elif intencion == "nueva_consulta":
                logger.info("🆕 Nueva consulta detectada → ignorando contexto")
                ctx = None  # rompe flujo y continúa abajo

        # ==========================================
        # 🔀 2. FLUJO NORMAL
        # ==========================================
        tool = decidir_tool(question)
        logger.info(f"🔀 Tool elegida: {tool}")

        if "stock" in tool:
            resultado = asesor_stock(question)
        else:
            resultado = asesor_rag(question)

        # ==========================================
        # 🧠 NORMALIZAR OUTPUT
        # ==========================================
        if isinstance(resultado, tuple):
            respuesta, data = resultado
        else:
            respuesta = resultado
            data = None

        return respuesta, data

    except Exception as e:
        logger.error(f"💥 ERROR EN SUPERVISOR: {e}")
        return "❌ Error procesando la solicitud", None