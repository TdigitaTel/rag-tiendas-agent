print("✅ Entro Supervisor")

from app.logger import get_logger
print("✅ entro logger")

from app.asesor import asesor_rag
print("✅ asesor_rag OK")

from app.asesor_stock import asesor_stock, consultar_stock_sql, formatear_respuesta_sql,consultar_stock, formatear_respuesta_p
print("✅ asesor_stock OK")

from app.config import LLM
from app.asesor_stock import obtener_codigo_almacen

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
        # 🔥 CONSULTA CONTEXTUAL
        # ==========================================
        if ctx and ctx.get("tema_actual"):
            tema = ctx["tema_actual"]
            articulos = tema.get("articulos", [])
            almacen = obtener_codigo_almacen(question)

            if articulos and almacen:
                logger.info("🧠 Consulta contextual de almacén detectada")
                logger.info(f"📦 Artículos contexto: {articulos}")
                logger.info(f"🏪 Almacén contexto: {almacen}")
                rows = consultar_stock_sql(articulos,almacen=almacen)
                respuesta = formatear_respuesta_sql(rows)
                return respuesta, ctx

            if articulos and es_consulta_contextual(question):
                logger.info("🧠 Consulta contextual detectada")
                logger.info(f"📦 Artículos contexto: {articulos}")
                rows = consultar_stock_sql(articulos,almacen=None)

                respuesta = formatear_respuesta_sql(rows)
                return respuesta, ctx
        # ==========================================
        # 🔥 CONFIRMACIÓN
        # ==========================================
        if ctx and ctx.get("estado") == "esperando_confirmacion":
            intencion = detectar_intencion(question)
            logger.info(f"🧠 Intención detectada: {intencion}")
            if intencion == "confirmacion":
                articulos = ctx.get("articulos")
                if not articulos:
                    return "❌ Error recuperando resultados", None
                almacen = ctx.get("almacen")
                rows = consultar_stock_sql(
                    articulos,
                    almacen=almacen
                )
                respuesta = formatear_respuesta_sql(rows)
                return respuesta, None
            elif intencion == "rechazo":
                return "Perfecto 👍 dime más detalles del producto", None
            elif intencion == "nueva_consulta":
                ctx = None

        # ==========================================
        # 🔀 FLUJO NORMAL
        # ==========================================

        tool = decidir_tool(question)
        logger.info(f"🔀 Tool elegida: {tool}")

        if "stock" in tool:
            resultado = asesor_stock(question)
        else:
            resultado = asesor_rag(question)

        if isinstance(resultado, tuple):
            respuesta, data = resultado
        else:
            respuesta = resultado
            data = None
        return respuesta, data

    except Exception as e:

        logger.error(f"💥 ERROR EN SUPERVISOR: {e}")

        return "❌ Error procesando la solicitud", None
    
def es_consulta_contextual(texto: str) -> bool:
    texto = texto.lower().strip()
    patrones = [
        "y en ",
        "en ferrol",
        "en santiago",
        "en sanxenxo",
        "en coruña",
        "en la coruña",
        "en total"
    ]
    return any(p in texto for p in patrones)