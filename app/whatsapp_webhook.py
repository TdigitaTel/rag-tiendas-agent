import os
import traceback
import requests

from fastapi import FastAPI, Request, Query

from app.supervisor import supervisor

app = FastAPI()

# ==============================
# CONFIG
# ==============================

WHATSAPP_VERIFY_TOKEN = os.getenv(
    "WHATSAPP_VERIFY_TOKEN",
    "bermudez_webhook_123"
)

WHATSAPP_ACCESS_TOKEN = os.getenv(
    "WHATSAPP_ACCESS_TOKEN"
)

WHATSAPP_PHONE_NUMBER_ID = os.getenv(
    "WHATSAPP_PHONE_NUMBER_ID"
)

# ==============================
# MEMORIA
# ==============================

user_context = {}

# ==============================
# VERIFICACIÓN META
# ==============================

@app.get("/whatsapp/webhook")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    print("🔎 Verificando webhook")

    if (
        hub_mode == "subscribe"
        and hub_verify_token == WHATSAPP_VERIFY_TOKEN
    ):
        print("✅ Verificado")
        return int(hub_challenge)

    print("❌ Error verificación")
    return {"error": "token inválido"}

# ==============================
# RECEPCIÓN MENSAJES
# ==============================

@app.post("/whatsapp/webhook")
async def receive_message(request: Request):

    try:

        data = await request.json()

        print("\n=============================")
        print("📩 MENSAJE WHATSAPP")
        print(data)

        value = data["entry"][0]["changes"][0]["value"]

        messages = value.get("messages", [])

        if not messages:
            return {"status": "ok"}

        message = messages[0]

        if message["type"] != "text":
            return {"status": "ok"}

        user_text = message["text"]["body"]

        user_id = message["from"]

        print(f"👤 USER: {user_id}")
        print(f"📩 TEXTO: {user_text}")

        ctx = user_context.get(user_id)

        respuesta, new_ctx = supervisor(
            user_text,
            ctx
        )

        if new_ctx:
            user_context[user_id] = new_ctx
        else:
            user_context.pop(user_id, None)

        enviar_whatsapp(
            user_id,
            respuesta
        )

        return {"status": "ok"}

    except Exception as e:

        print("💥 ERROR")
        print(e)
        traceback.print_exc()

        return {"status": "error"}

# ==============================
# ENVÍO MENSAJES
# ==============================

def enviar_whatsapp(
    telefono,
    texto
):

    url = (
        f"https://graph.facebook.com/v25.0/"
        f"{WHATSAPP_PHONE_NUMBER_ID}/messages"
    )

    headers = {
        "Authorization":
            f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type":
            "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {
            "body": texto
        }
    }

    r = requests.post(
        url,
        headers=headers,
        json=payload
    )

    print("📤 RESPUESTA META")
    print(r.status_code)
    print(r.text)