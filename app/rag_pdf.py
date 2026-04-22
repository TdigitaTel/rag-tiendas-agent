from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.readers.file import PyMuPDFReader
from llama_index.vector_stores.postgres import PGVectorStore

load_dotenv()

print("📄 Cargando PDF...")

# 👇 cargar PDF
loader = PyMuPDFReader()
documents = loader.load_data("data/Bermudez_Ulloa_Contacto.pdf")

print(f"📚 Documentos cargados: {len(documents)}")

# 👇 crear conexión a postgres (ajusta password si hace falta)
vector_store = PGVectorStore.from_params(
    database="rag_db",
    host="localhost",
    port=5432,
    user="rag_user",
    password="1234",
    table_name="pdf_embeddings",
    embed_dim=1536,
    perform_setup=True   # 👈 🔥 ESTO CREA LA TABLA
)

# 👇 decirle a LlamaIndex dónde guardar
storage_context = StorageContext.from_defaults(
    vector_store=vector_store
)

print("🧠 Guardando embeddings en PostgreSQL...")

# 🔥 AQUÍ se guardan en la BD
index = VectorStoreIndex.from_documents(
    documents,
    storage_context=storage_context
)

print("✅ PDF guardado en PostgreSQL")

# prueba
query_engine = index.as_query_engine()

response = query_engine.query("Dirección delegación Ferrol")

print("🧠 Respuesta:")
print(response)