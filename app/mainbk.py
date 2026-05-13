from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from app.bot import start, handle_message
from app.config import TELEGRAM_TOKEN
from app.logger import get_logger

logger = get_logger(__name__)

def main():
    logger.info("🚀 Iniciando bot...")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Bot activo")
    app.run_polling()

if __name__ == "__main__":
    main()