from telegram import Update
from telegram.ext import ContextTypes

from app.supervisor import supervisor
from app.logger import get_logger

logger = get_logger(__name__)

# ✅ NO BORRAR ESTA FUNCIÓN
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("👋 Usuario inició conversación")
    await update.message.reply_text("🤖 Hola! Pregúntame direcciones de tiendas.")

# ✅ ESTA ES LA PRINCIPAL
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    logger.info(f"📩 Usuario: {user_text}")

    await update.message.reply_text("⏳ Buscando...")

    try:
        response = supervisor(user_text)

        logger.info(f"📤 Respuesta: {response}")

        await update.message.reply_text(response)

    except Exception:
        logger.exception("💥 Error")
        await update.message.reply_text("Error")