import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

DB_URL = os.getenv("DB_URL")
engine = create_engine(DB_URL)

file_path = "data/stocks_store-1.xlsx"

df = pd.read_excel(file_path)

# limpiar columnas
df.columns = [col.lower().strip() for col in df.columns]

print("📊 Datos:", df.head())

# guardar en postgres
df.to_sql("stock", engine, if_exists="replace", index=False)

print("✅ Excel cargado en PostgreSQL")