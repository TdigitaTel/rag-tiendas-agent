print("🔥 PASO 0: entrando a main.py")

# ==============================
# 🔹 IMPORTS
# ==============================

print("🔥 PASO 1: antes de telegram import")

from telegram.ext import ApplicationBuilder, MessageHandler, filters
print("✅ PASO 2: telegram import OK")

from app.supervisor import supervisor
print("✅ PASO 3: supervisor import OK")

from app.config import TELEGRAM_TOKEN
print("✅ PASO 4: config import OK")

import traceback
import os
import uvicorn 

from dotenv import load_dotenv

load_dotenv()

# ==============================
# 🧠 MEMORIA SIMPLE (POR USUARIO)
# ==============================

user_context = {}


# ==============================
# 🔹 HANDLER PRINCIPAL
# ==============================

async def handle_message(update, context):
    print("\n=============================")
    print("📩 PASO 11: mensaje recibido")

    try:
        user_text = update.message.text
        user_id = update.message.from_user.id

        print(f"📩 TEXTO: {user_text}")
        print(f"👤 USER: {user_id}")

        # 🔹 recuperar contexto REAL (None si no existe)
        ctx = user_context.get(user_id)
        print(f"🧠 CONTEXTO ACTUAL: {ctx}")

        # ============================
        # 🧠 TODO PASA POR SUPERVISOR
        # ============================
        print("🧠 PASO 12: llamando supervisor")

        respuesta, new_ctx = supervisor(user_text, ctx)

        # ============================
        # 💾 ACTUALIZAR CONTEXTO
        # ============================

        if new_ctx:
            # guardar nuevo estado
            user_context[user_id] = new_ctx
            print(f"💾 CONTEXTO GUARDADO: {new_ctx}")

        else:
            # limpiar contexto si ya no se necesita
            if user_id in user_context:
                user_context[user_id] = None
                print("🧹 CONTEXTO LIMPIADO")

        print(f"📤 PASO 13: respuesta: {respuesta}")

        print("📡 PASO 14: enviando respuesta a Telegram")
        await update.message.reply_text(respuesta)

        print("✅ PASO 15: respuesta enviada")

    except Exception as e:
        print("💥 ERROR EN HANDLER:", e)
        traceback.print_exc()

    print("=============================\n")


# ==============================
# 🔹 MAIN
# ==============================

def main():
    print("🚀 PASO 5: entrando a main()")

    # 🔑 TOKEN CHECK
    if TELEGRAM_TOKEN:
        print(f"🔑 TOKEN OK: {TELEGRAM_TOKEN[:10]}...")
    else:
        print("❌ TOKEN VACÍO")
        return

    try:
        print("⚙️ PASO 6: creando app Telegram")
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        print("✅ PASO 7: app creada correctamente")
    except Exception as e:
        print("💥 ERROR creando ApplicationBuilder:", e)
        traceback.print_exc()
        return

    try:
        print("⚙️ PASO 8: añadiendo handler")
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )
        print("✅ PASO 9: handler añadido")
    except Exception as e:
        print("💥 ERROR añadiendo handler:", e)
        traceback.print_exc()
        return

    print("📡 PASO 10: iniciando polling (esperando mensajes...)")

    try:
        app.run_polling()
    except Exception as e:
        print("💥 ERROR en polling:", e)
        traceback.print_exc()


# ==============================
# 🔹 ENTRYPOINT
# ==============================


if __name__ == "__main__":

    canal = os.getenv(
        "CANAL",
        "telegram"
    )

    if canal == "telegram":

        print("🚀 MODO TELEGRAM")
        main()

    elif canal == "whatsapp":

        print("🚀 MODO WHATSAPP")

        uvicorn.run(
            "app.whatsapp_webhook:app",
            host="0.0.0.0",
            port=8000,
            reload=True
        )