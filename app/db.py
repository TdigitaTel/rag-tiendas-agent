import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

print("🚀 Ejecutando db.py...")

load_dotenv()

DB_URL = os.getenv("DB_URL")
print("DB_URL:", DB_URL)

engine = create_engine(DB_URL)

def test_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ Conexión exitosa:", list(result))
    except Exception as e:
        print("❌ Error de conexión:", e)

if __name__ == "__main__":
    test_connection()