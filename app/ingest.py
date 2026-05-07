from llama_index.readers.file import PyMuPDFReader
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SentenceSplitter

from app.db import get_vector_store
from app.logger import get_logger
from app.reset_db import reset_vector_table
from app.config import EMBED_MODEL

import time

logger = get_logger(__name__)

def ingest_pdf(path):
    
    logger.info("🧨 Reseteando base vectorial...")
    reset_vector_table()   # 👈 🔥 SE EJECUTA SIEMPRE

    logger.info(f"📄 Cargando PDF: {path}")

    # 🔹 cargar PDF
    loader = PyMuPDFReader()
    documents = loader.load_data(path)

    logger.info(f"📚 Documentos: {len(documents)}")

    # 🔥 DEBUG: ver texto real (muy importante)
    for i, doc in enumerate(documents):
        logger.debug(f"\n--- DOC {i} ---")
        logger.debug(doc.text[:500])

    # 🔹 conexión a PostgreSQL
    vector_store = get_vector_store()

    storage_context = StorageContext.from_defaults(
        vector_store=vector_store
    )

    # 🔥 CHUNKING PROFESIONAL (CLAVE)
    parser = SentenceSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    start = time.time()

    # 🔥 INDEXACIÓN CORRECTA
    VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=EMBED_MODEL,
        transformations=[parser]   # 👈 AQUÍ ESTÁ LA MAGIA
    )

    end = time.time()

    logger.info(f"⏱ Indexado en {end - start:.2f}s")
    logger.info("✅ Embeddings guardados en PostgreSQL")

    for doc in documents:
        print("----- TEXTO PDF -----")
        print(doc.text)

if __name__ == "__main__":
    ingest_pdf("data/Bermudez_Ulloa_Contacto.pdf")