from sqlalchemy import create_engine, text
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.postgres import PGVectorStore

from app.config import DB_CONFIG, EMBED_MODEL, LLM
from app.logger import get_logger

logger = get_logger(__name__)


# ==============================
# 🔌 CONEXIONES
# ==============================

def get_db_url():
    return (
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
        f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )


def get_vector_store():
    return PGVectorStore.from_params(
        database=DB_CONFIG["database"],
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        table_name="stock_embeddings",
        embed_dim=1536
    )


engine = create_engine(get_db_url())


# ==============================
# 🧠 NORMALIZACIÓN
# ==============================

def normalizar_query(q: str) -> str:
    prompt = f"""
Convierte esta consulta en una búsqueda de productos optimizada para catálogo.

Reglas:

- usa SIEMPRE singular (machones → machon)
- corrige errores (mcho → machon)

- normaliza medidas:
  - media → 1/2
  - tres cuartos → 3/4
  - una pulgada → 1"
  - pulgadas → "

- usa términos típicos de producto (codo, tubo, machon, latiguillo…)
- elimina palabras irrelevantes (hola, tienes, stock…)
- no expliques nada
- devuelve solo la búsqueda final

Consulta:
{q}
"""
    return LLM.complete(prompt).text.strip().lower()


# ==============================
# 🔎 VECTOR SEARCH
# ==============================

def buscar_vectores(query_clean: str):
    vector_store = get_vector_store()

    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=EMBED_MODEL
    )

    query_engine = index.as_query_engine(similarity_top_k=15)
    results = query_engine.query(query_clean)
    
    # ==========================================
    # 🔥 LOG DETALLADO DE RESULTADOS VECTORIALES
    # ==========================================
    logger.info("📊 Resultados vectoriales:")
    for i, node in enumerate(results.source_nodes):
        try:
            logger.info(
                f"{i} | "
                f"score={node.score:.4f} | "
                f"articulo={node.metadata.get('articulo')} | "
                f"texto={node.text[:80]}"
            )

        except Exception as e:
            logger.warning(f"⚠️ Error logeando nodo {i}: {e}")

    return results.source_nodes


# ==============================
# 🔍 VALIDACIÓN DE DOMINIO (🔥 NUEVO)
# ==============================

def es_producto_valido(nodes):
    if not nodes:
        return False

    top_score = nodes[0].score

    # 🔥 threshold realista
    if top_score < 0.55:
        logger.warning(f"❌ Score bajo → {top_score}")
        return False

    return True


# ==============================
# 🔍 FILTRO INTELIGENTE
# ==============================

def filtrar_por_palabras(nodes, query_clean):
    palabras = query_clean.split()

    medida = next((p for p in palabras if "/" in p or '"' in p), None)

    resultados = []
    logger.info(f"📊 Palabras: {palabras}")
    logger.info(f"📊 Medida: {medida}")

    for node in nodes:
        texto = node.text.lower()

        # medida obligatoria
        #if medida and medida not in texto:
        #    continue

        matches = sum(1 for p in palabras if p in texto)

        resultados.append({
            "node": node,
            "matches": matches,
            "score": node.score
        })

    # 🔥 FILTRO DURO
    resultados_filtrados = [r for r in resultados if r["matches"] >= 1]

    # 🔥 fallback correcto (NO romper)
    if not resultados_filtrados:
        logger.warning("⚠️ fallback activado")
        resultados_filtrados = resultados

    resultados_filtrados.sort(
        key=lambda x: (x["matches"], x["score"]),
        reverse=True
    )

    return [r["node"] for r in resultados_filtrados]


# ==============================
# 🎯 ARTÍCULOS
# ==============================

def obtener_articulos(nodes):
    candidatos = []

    for node in nodes:
        art = node.metadata.get("articulo")
        if art:
            candidatos.append((node.score, str(art)))

    candidatos.sort(key=lambda x: x[0], reverse=True)

    # 🔥 límite controlado
    candidatos = candidatos[:10]

    return [c[1] for c in candidatos]


# ==============================
# 🧠 DECISIÓN
# ==============================

def evaluar_resultados(nodes, articulos):
    if not nodes:
        return "❌ No trabajamos ese tipo de productos"

    if len(articulos) > 10:
        return (
            "Tengo varios tipos de productos relacionados.\n"
            "¿Puedes especificar más?"
        )

    if 5 < len(articulos) <= 10:
        return (
            f"He encontrado {len(articulos)} opciones.\n"
            "¿Quieres que te las muestre todas?"
        )

    return None


# ==============================
# 🗄️ SQL
# ==============================

def consultar_stock(articulos):
    sql = text("""
        SELECT descripcion,
               stock_almeiras,
               stock_santiago,
               stock_ferrol,
               stock_sandiego,
               stock_sanxenxo,
               stock_total
        FROM stock
        WHERE articulo = ANY(:articulos)
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql, {"articulos": articulos}).fetchall()

    if not rows:
        return []

    unique = {}
    for r in rows:
        unique[r.descripcion] = r

    return list(unique.values())


# ==============================
# 📤 RESPUESTA
# ==============================

def formatear_respuesta(rows):
    if not rows:
        return "❌ No hay stock disponible"

    respuesta = "📦 Productos encontrados:\n\n" 

    for r in rows:
        respuesta += (
            f"- {r.descripcion}\n"
            f"  Almeiras: {r.stock_almeiras} | "
            f"Santiago: {r.stock_santiago} | "
            f"Ferrol: {r.stock_ferrol} | "
            f"Sanxenxo: {r.stock_sanxenxo} | "
            f"Coruña: {r.stock_sandiego}\n"
            f"  📊 Total: {r.stock_total}\n\n"
        )

    return respuesta


# ==============================
# 🚀 MAIN
# ==============================

def asesor_stock(question: str):
    logger.info(f"📦 STOCK query: {question}")

    query_clean = normalizar_query(question)
    logger.info(f"📊 Query Clean: {query_clean}")
    
    nodes = buscar_vectores(query_clean)
    logger.info(f"📊 Vectores encontrados: {len(nodes)}")
    # 🔥 VALIDACIÓN REAL DE DOMINIO
   # if not es_producto_valido(nodes):
   #     return "❌ No trabajamos ese tipo de productos", None

    nodes_filtrados = filtrar_por_palabras(nodes, query_clean)
    logger.info(f"📊 Vectores filtrados: {len(nodes_filtrados)}")
    
    if not es_producto_valido(nodes) and not nodes_filtrados:
        return "❌ No hay resultados relevantes", None

    articulos = obtener_articulos(nodes_filtrados)
    logger.info(f"📊 Articulos encontrados: {len(articulos)}")

    decision = evaluar_resultados(nodes_filtrados, articulos)

    if decision:
        return decision, {
            "estado": "esperando_confirmacion",
            "articulos": articulos
        }

    rows = consultar_stock(articulos)

    return formatear_respuesta(rows), None