from telegram import Update
from telegram.ext import ContextTypes
from app.asesor_stockbk import asesor_stock
from app.supervisor import supervisor
from app.logger import get_logger

logger = get_logger(__name__)

memory = {}

def get_ctx(user_id):
    if user_id not in memory:
        memory[user_id] = {}
    return memory[user_id]

# ✅ NO BORRAR ESTA FUNCIÓN
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("👋 Usuario inició conversación")
    await update.message.reply_text("🤖 Hola! Pregúntame direcciones de tiendas.")

# ✅ ESTA ES LA PRINCIPAL
async def handle_message(update, context):
    user_id = update.effective_user.id
    texto = update.message.text.lower()

    ctx = get_ctx(user_id)

    print(f"🧠 Estado actual: {ctx}")

    # 🔥 1. SI HAY ESTADO → CONTINUACIÓN
    if ctx.get("estado") == "esperando_confirmacion":
        respuesta = manejar_confirmacion(ctx, texto)

    else:
        # 🔥 2. FLUJO NORMAL
        respuesta, data = asesor_stock(texto)

        # guardar estado si hace falta
        if data:
            ctx.update(data)

    await update.message.reply_text(respuesta)

def manejar_confirmacion(ctx, texto):

    if texto in ["si", "sí", "vale", "ok"]:

        articulos = ctx.get("articulos", [])
        from app.asesor_stockbk import consultar_stock, formatear_respuesta
        rows = consultar_stock(articulos)
        respuesta = formatear_respuesta(rows)
        ctx.clear()
        return respuesta

    else:
        ctx.clear()
        return "Vale, dime qué necesitas 👍"