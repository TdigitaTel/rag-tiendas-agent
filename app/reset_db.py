from sqlalchemy import create_engine, text
from app.logger import get_logger
from app.config import DB_CONFIG

logger = get_logger(__name__)


def get_connection():
    return create_engine(
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )


def reset_vector_table(table_base_name: str):
    """
    🔥 Borra tabla vectorial de LlamaIndex
    (automáticamente añade prefijo data_)
    """

    table_name = f"data_{table_base_name}"

    logger.info(f"🧨 Eliminando tabla: {table_name}")

    engine = get_connection()

    try:
        with engine.connect() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
            conn.commit()

        logger.info(f"✅ Tabla {table_name} eliminada correctamente")

    except Exception:
        logger.exception(f"💥 Error eliminando {table_name}")


# 🔥 helpers específicos (más claro para usar)
def reset_pdf_embeddings():
    reset_vector_table("pdf_embeddings")


def reset_stock_embeddings():
    reset_vector_table("stock_embeddings")


if __name__ == "__main__":
    reset_stock_embeddings()