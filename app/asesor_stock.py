
from sqlalchemy import create_engine, text
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.postgres import PGVectorStore
from app.sqlserverconnect import get_sqlserver_connection
from app.config import DB_CONFIG, EMBED_MODEL, LLM, TOP_SCORE
import re
import json
import unicodedata

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
# 🧠 NORMALIZACIÓN LLM
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
- elimina palabras irrelevantes
- no expliques nada
- devuelve solo la búsqueda final
- SIEMPRE incluye el tipo de producto (machon, codo, latiguillo, etc)
- NUNCA devuelvas solo material o medida
Consulta:
{q}
"""
    return LLM.complete(prompt).text.strip().lower()


# ==============================
# 🔎 VECTOR SEARCH + LOG
# ==============================

def buscar_vectores(query_clean: str):
    vector_store = get_vector_store()

    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=EMBED_MODEL
    )

    query_engine = index.as_query_engine(similarity_top_k=30)
    results = query_engine.query(query_clean)

    nodes = results.source_nodes

    logger.info(f"📊 Vectores encontrados: {len(nodes)}")

    for i, node in enumerate(nodes):
        logger.info(
            f"{i} | score={node.score:.4f} | "
            f"articulo={node.metadata.get('articulo')} | "
            f"texto={node.text[:80]}"
        )

    return nodes



def obtener_codigo_almacen(texto):
    with open("data/almacenes.json","r",encoding="utf-8") as f:
        ALMACENES = json.load(f)

    texto = texto.lower()
    for almacen, datos in ALMACENES.items():
        for alias in datos["alias"]:
            if alias.lower() in texto:
                return datos["codigo"]
    return None
# ==============================
# 🧠 NLP SIMPLE
# ==============================
def quitar_tildes(texto: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'

    )
def normalizar_texto(texto: str) -> str:
    texto = texto.lower()
    texto = quitar_tildes(texto)
    texto = re.sub(r"[^\w/]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def tokenizar(texto: str):
    return normalizar_texto(texto).split()


# ==============================
# 🔥 SCORING HÍBRIDO
# ==============================

def analizar_candidatos(nodes, consulta: str ):

    tokens_consulta = tokenizar(consulta)

    candidatos = []

    for node in nodes:
        texto_node = normalizar_texto(node.text)
        tokens_node = tokenizar(node.text)

        matches = [
            p for p in tokens_consulta
            if p in tokens_node or p in texto_node
        ]
        logger.info(f"📊 Palabras {texto_node}: {len(matches)}")

        if not matches:
            continue

        matches_unicos = list(set(matches))

        ratio_consulta = len(matches_unicos) / len(tokens_consulta)
        ratio_articulo = len(matches_unicos) / max(len(tokens_node), 1)

        logger.info(
            f"{node.text} | score_vector={node.score:.4f} | ratio_consulta={ratio_consulta} | ratio_articulo={ratio_articulo}"
        )

        score_final = (
            node.score * 0.35 +
            ratio_consulta * 0.50 +
            ratio_articulo * 0.15
        )

        # 🔥 FILTRO POR SCORE

        candidatos.append({
            "node": node,
            "score_final": score_final,
            "texto": node.text
            })
        
    candidatos.sort(key=lambda x: x["score_final"], reverse=True)
    logger.info(f"📊 Candidatos válidos : {len(candidatos)}")

    for i, c in enumerate(candidatos[:10]):
        logger.info(
            f"{i} | score_final={c['score_final']:.4f} | texto={c['texto']}"
        )

    return candidatos


# ==============================
# 🧠 DECISIÓN
# ==============================

def decidir_respuesta(candidatos, limite_bajo=5, limite_alto=10):

    total = len(candidatos)

    if total == 0:
        return {"accion": "sin_resultados"}

    # 🔥 NUEVO: detectar precisión real
    top_score = candidatos[0]["score_final"]
    logger.info(f"🎯 Top score_final: {top_score:.4f}")

    # ============================
    # 🎯 MATCH REAL (preciso aunque haya muchos)
    # ============================

    if top_score >= TOP_SCORE:
        return {"accion": "mostrar_directo"}

    # ============================
    # ⚠️ MUCHOS RESULTADOS (genérico)
    # ============================

    if total > 15:
        return {
            "accion": "pedir_especificacion",
            "mensaje": f"Encontré {total} productos. ¿Puedes especificar más?"
        }
    # ============================
    # 👍 INTERMEDIO
    # ============================
    if limite_bajo <= total <= 15:
        return {
            "accion": "confirmar_mostrar",
            "mensaje": f"He encontrado {total} opciones.\n¿Quieres que te las muestre todas?"
        }

    # ============================
    # 🔍 POCOS → DIRECTO
    # ============================

    return {"accion": "mostrar"}


# ==============================
# 🎯 ARTÍCULOS
# ==============================

def obtener_articulos(nodes):
    return [
        str(n["node"].metadata.get("articulo"))
        for n in nodes
        if n["node"].metadata.get("articulo")
    ]


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

    unique = {}
    for r in rows:
        unique[r.descripcion] = r

    return list(unique.values())

def formatear_respuesta_p(rows):

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

def consultar_stock_sql(articulos, almacen=None):
    if not articulos:
        return []
    conn = get_sqlserver_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        placeholders = ",".join(["?"] * len(articulos))
        # 🔥 CASO CON ALMACÉN
        if almacen:
            query = f"""
                SELECT 
                    s.codigoarticulo as codigoarticulo,
                    a.descripcionarticulo as descripcionarticulo,
                    s.codigoalmacen as codigoalmacen,
                    al.almacen as almacen,
                    SUM(s.unidadsaldo) AS stock
                FROM acumuladostock s
                JOIN articulos a 
                    ON s.codigoarticulo = a.codigoarticulo
                JOIN almacenes al
                    ON s.codigoalmacen = al.codigoalmacen
                WHERE s.codigoarticulo IN ({placeholders})
                  AND s.codigoalmacen = ?
                GROUP BY  
                    s.codigoarticulo,
                    a.descripcionarticulo,
                    s.codigoalmacen,
                    al.almacen 
            """
            params = list(articulos) + [almacen]

        # 🔥 CASO TOTAL
        else:
            query = f"""
                SELECT 
                    s.codigoarticulo as codigoarticulo,
                    a.descripcionarticulo as descripcionarticulo,
                    SUM(s.unidadsaldo) AS stock_total
                FROM acumuladostock s
                JOIN articulos a 
                    ON s.codigoarticulo = a.codigoarticulo
                WHERE s.codigoarticulo IN ({placeholders})
                GROUP BY 
                    s.codigoarticulo,
                    a.descripcionarticulo
            """
            params = articulos
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return rows
    
    except Exception as e:
        logger.error(f"❌ Error consultando stock: {e}")
        return []
    finally:
        conn.close()
# ==============================
# 📤 RESPUESTA
# ==============================


def formatear_respuesta_sql(rows):
    
    logger.info(f"📦 Dando formato a respuesta...")
    if not rows:
        return "❌ No hay stock disponible"
    respuesta = "📦 Productos encontrados:\n\n"
    for r in rows:
        respuesta += f"🔹 {r.descripcionarticulo}\n"
        if hasattr(r, "almacen"):
            respuesta += (
                f"   🏪 {r.almacen} ({r.codigoalmacen})\n"
                f"   📦 Stock: {r.stock: ,.2f}\n\n"
            )
        else:
            respuesta += (
                f"   📊 Stock Total: {r.stock_total :,.2f}\n\n"
            )
    
    logger.info(f"📦 Formato completado...")
    return respuesta

# ==============================
# 🚀 MAIN
# ==============================

def asesor_stock(question: str):

    logger.info(f"📦 STOCK query: {question}")

    query_clean = normalizar_query(question)
    logger.info(f"🧠 Query normalizada: {query_clean}")
    if "no se encontró" in query_clean:
        logger.warning("❌ Consulta fuera de dominio detectada por LLM")
        return "❌ No trabajamos ese tipo de productos", None

    nodes = buscar_vectores(query_clean)
    logger.info(f"🧠 Nodos encontrados: {len(nodes)}")
    
    if not nodes:
        return "❌ No trabajamos ese tipo de productos", None

    candidatos = analizar_candidatos(nodes, query_clean)

    if not candidatos:
        return "❌ No trabajamos ese tipo de productos", None
    
    logger.info(f"🧠 decidiendo respuestas...")
    decision = decidir_respuesta(candidatos)

    accion = decision["accion"]
    candidatos = sorted(
        candidatos,
        key=lambda x: x["score_final"],
        reverse=True)
    #Fltrando solo los que pasan el umbral
    top_score = candidatos[0]["score_final"]
    top_nodes = [c for c in candidatos
        if c["score_final"] >=  TOP_SCORE
        ]
    logger.info(f"🎯 Top score_final: {top_score:.4f}")
    logger.info(f"✅ Artículos que pasan umbral: {len(top_nodes)}")
    
    logger.info(f"🧠 obtenienido articulos...")
    articulos = obtener_articulos(top_nodes)

    if accion == "sin_resultados":
        return "❌ No encontré productos", None

    if accion == "pedir_especificacion":
        return decision["mensaje"], None

    if accion == "confirmar_mostrar":
        almacen = obtener_codigo_almacen(question)
        return decision["mensaje"], {
            "estado": "esperando_confirmacion",
            "articulos": articulos,
            "almacen": almacen,
                "tema_actual": {
                "tipo": "stock",
                "articulos": articulos,
                "query": query_clean}
    }
    almacen = obtener_codigo_almacen(question)
    logger.info(f"🏪 Almacén detectado: {almacen if almacen else 'TOTAL'}")
    
    logger.info(f"🧠 Consultando stock...")
    rows = consultar_stock_sql(articulos, almacen=almacen)
    
    logger.info(f"🧠 Formateando respuesta..")
    return formatear_respuesta_sql(rows),  {"tema_actual": {
        "tipo": "stock",
        "articulos": articulos,
        "query": query_clean}

}