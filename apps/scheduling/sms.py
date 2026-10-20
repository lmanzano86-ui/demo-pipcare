"""Envío de SMS. Si hay credenciales Twilio en el entorno las usa;
si no, registra el mensaje (modo demostración / sin proveedor).

Para activar Twilio en producción:
  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER (+1...)
"""

import base64
import json
import os
import urllib.parse
import urllib.request


def _twilio_cfg():
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    sender = os.environ.get("TWILIO_FROM_NUMBER", "").strip()
    if sid and token and sender:
        return sid, token, sender
    return None


def send_sms(to_phone, body):
    """Devuelve (ok: bool, detail: str). Nunca lanza excepciones."""
    cfg = _twilio_cfg()
    if not cfg:
        return True, "registrado (Twilio no configurado)"
    sid, token, sender = cfg
    try:
        data = urllib.parse.urlencode(
            {"To": to_phone, "From": sender, "Body": body}).encode()
        req = urllib.request.Request(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            data=data, method="POST")
        creds = base64.b64encode(f"{sid}:{token}".encode()).decode()
        req.add_header("Authorization", f"Basic {creds}")
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode())
        return True, f"Twilio SID {payload.get('sid', '')}"
    except Exception as e:  # noqa: BLE001 - el fallo se registra, no se propaga
        return False, f"Twilio error: {e}"
