from sqlalchemy import create_engine, text

from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.postgres import PGVectorStore

from app.config import DB_CONFIG, EMBED_MODEL, LLM
from app.logger import get_logger

logger = get_logger(__name__)


# 🔌 conexión SQL
def get_db_url():
    return (
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
        f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )


# 🔌 conexión vectorial
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


# 🧠 NORMALIZACIÓN (LLM)
def normalizar_query(q: str) -> str:
    prompt = f"""
Convierte esta consulta en una búsqueda corta de productos.

Reglas:
- elimina palabras innecesarias
- corrige errores
- mantén términos técnicos
- no expliques nada

Ejemplos:
"tienes stock de codos de media" → codo 1/2
"tubo aluminio blanco" → tubo aluminio blanco

Consulta:
{q}
"""
    return LLM.complete(prompt).text.strip().lower()


# 🚀 FUNCIÓN PRINCIPAL
def asesor_stock(question: str) -> str:
    logger.info(f"📦 STOCK query: {question}")

    # 🔹 1. normalizar
    query_clean = normalizar_query(question)
    logger.info(f"🧠 Query normalizada: {query_clean}")

    # 🔹 2. vector search
    vector_store = get_vector_store()

    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=EMBED_MODEL
    )

    query_engine = index.as_query_engine(similarity_top_k=30)

    results = query_engine.query(query_clean)

    # 🔍 DEBUG VECTOR
    logger.info("📊 Resultados vectoriales:")
    for i, node in enumerate(results.source_nodes):
        logger.info(
            f"{i} | score={node.score:.4f} | "
            f"articulo={node.metadata.get('articulo')} | "
            f"texto={node.text[:80]}"
        )

    # 🔹 3. construir candidatos
    candidatos = []

    for node in results.source_nodes:
        score = node.score
        art = node.metadata.get("articulo")

        if art:
            candidatos.append((score, str(art)))

    logger.info(f"📦 Total candidatos: {len(candidatos)}")

    for c in candidatos[:10]:
        logger.info(f"score={c[0]:.4f} articulo={c[1]}")

    # 🔹 4. ordenar por score
    candidatos.sort(key=lambda x: x[0], reverse=True)

    # 🔹 5. detectar si hay resultados reales
    MAX_SCORE = max([c[0] for c in candidatos], default=0)

    logger.info(f"📈 Max score: {MAX_SCORE:.4f}")

    if MAX_SCORE < 0.40:
        logger.warning("❌ Consulta fuera de dominio")
        return "❌ No trabajamos ese tipo de productos"

    # 🔹 6. aplicar umbral
    UMBRAL = 0.40

    candidatos_filtrados = [c for c in candidatos if c[0] >= UMBRAL][:10]

    logger.info(f"🎯 Después de umbral ({UMBRAL}): {len(candidatos_filtrados)}")

    articulos = [c[1] for c in candidatos_filtrados]

    if not articulos:
        return "❌ No encontré productos relevantes"

    logger.info(f"🔎 Artículos finales: {articulos}")

    # 🔹 7. SQL
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

    logger.info(f"🗄️ Ejecutando SQL con artículos: {articulos}")

    with engine.connect() as conn:
        rows = conn.execute(sql, {"articulos": articulos}).fetchall()

    logger.info(f"📊 Filas devueltas por SQL: {len(rows)}")

    if not rows:
        return "❌ No hay stock disponible"

    # 🔹 8. eliminar duplicados
    unique = {}
    for r in rows:
        unique[r.descripcion] = r

    rows = list(unique.values())

    # 🔹 9. respuesta
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