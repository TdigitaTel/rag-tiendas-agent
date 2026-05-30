import pyodbc
from app.logger import get_logger
logger = get_logger(__name__)

def get_sqlserver_connection():
    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=192.168.0.101\\SQLEXIT;"
            "DATABASE=EXITERP;"
            "UID=SBU;"
            "PWD=Su663001***321;"
            "TrustServerCertificate=yes;"
        )
        logger.info("✅ Conectado a SQL Server")
        return conn

    except Exception as e:
        logger.error(f"❌ Error conectando a SQL Server: {e}")
        return None