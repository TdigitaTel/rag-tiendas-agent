import pandas as pd
from sqlalchemy import create_engine, text

from llama_index.core import VectorStoreIndex, StorageContext, Document
from llama_index.vector_stores.postgres import PGVectorStore

from app.config import DB_CONFIG, EMBED_MODEL
from app.logger import get_logger

logger = get_logger(__name__)


# 🔌 conexión SQL
def get_db_url():
    return (
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
        f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )


# 🔌 vector store (pgvector)
def get_vector_store():
    return PGVectorStore.from_params(
        database=DB_CONFIG["database"],
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        table_name="stock_embeddings",
        embed_dim=1536,
        perform_setup=True
    )


def load_stock_to_db():
    logger.info("📦 INICIO carga stock")

    # 🔹 1. leer Excel
    df = pd.read_excel("data/stock.xlsx")

    logger.info(f"📊 Filas: {len(df)}")

    # 🔹 2. renombrar columnas
    df = df.rename(columns={
        "Artículo": "articulo",
        "Descrip.Propia": "descripcion",
        "Ref.Fabricante": "ref_fabricante",
        "UE Stock": "ue_stock",
        "Stock Almeiras": "stock_almeiras",
        "Stock Santiago": "stock_santiago",
        "Stock Ferrol": "stock_ferrol",
        "Stock Sandiego": "stock_sandiego",
        "Stock SanXenxo": "stock_sanxenxo",
        "Stock Total": "stock_total",
        "Grupo": "grupo",
        "Subgrupo": "subgrupo",
        "observacion": "observacion"
    })

    # 🔹 3. limpiar numéricos
    numeric_cols = [
        "stock_almeiras", "stock_santiago", "stock_ferrol",
        "stock_sandiego", "stock_sanxenxo", "stock_total"
    ]

    for col in numeric_cols:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", ".", regex=False)
        )
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # 🔹 4. guardar en PostgreSQL
    engine = create_engine(get_db_url())

    logger.info("📥 Insertando datos en tabla stock...")
    df.to_sql("stock", engine, if_exists="append", index=False)

    logger.info("✅ Datos insertados en tabla stock")

    # 🔥 5. VECTOR INDEX (NUEVO)
    logger.info("🧠 Generando embeddings de productos...")

    docs = []

    for _, row in df.iterrows():
        texto = f"""
        {row['descripcion']}
        {row['ref_fabricante']}
        {row['grupo']} {row['subgrupo']}
        """

        docs.append(
            Document(
                text=texto,
                metadata={
                    "articulo": row["articulo"]
                }
            )
        )

    vector_store = get_vector_store()

    storage_context = StorageContext.from_defaults(
        vector_store=vector_store
    )

    VectorStoreIndex.from_documents(
        docs,
        storage_context=storage_context,
        embed_model=EMBED_MODEL
    )

    logger.info("✅ Embeddings de productos creados")


if __name__ == "__main__":
    load_stock_to_db()