import requests
from bs4 import BeautifulSoup
from twilio.rest import Client
import json
from datetime import datetime
import os

# ---------------------------
# CONFIGURACIÓN DEL USUARIO
# ---------------------------
PALABRAS_CLAVE = ["administrativo", "auxiliar administrativo"]
URL_BOC = "https://www.gobiernodecanarias.org/boc/"
ARCHIVO_MEMORIA = "convocatorias_vistas.json"

# Credenciales Twilio desde variables de entorno
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
FROM_WHATSAPP = "whatsapp:+14155238886"  # Número Twilio
TO_WHATSAPP = os.getenv("TO_WHATSAPP")   # Tu número personal

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# ---------------------------
# FUNCIONES
# ---------------------------

def enviar_mensaje(texto):
    """Envía un mensaje de WhatsApp usando Twilio."""
    try:
        message = client.messages.create(
            body=texto,
            from_=FROM_WHATSAPP,
            to=TO_WHATSAPP
        )
        print(f"✅ Mensaje enviado: {message.sid}")
    except Exception as e:
        print(f"⚠️ Error enviando mensaje: {e}")

def cargar_vistas():
    """Carga enlaces ya enviados desde archivo JSON."""
    try:
        with open(ARCHIVO_MEMORIA, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def guardar_vistas(vistas):
    """Guarda los enlaces ya vistos."""
    with open(ARCHIVO_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(list(vistas), f, indent=2)

def buscar_convocatorias():
    """Busca convocatorias en el BOC con las palabras clave."""
    print(f"🔍 Buscando convocatorias ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})...")
    try:
        resp = requests.get(URL_BOC, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] No se pudo acceder al BOC: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    resultados = []

    for link in soup.find_all("a", href=True):
        texto = link.get_text(strip=True).lower()
        if any(palabra in texto for palabra in PALABRAS_CLAVE):
            url_completa = link["href"]
            if not url_completa.startswith("http"):
                url_completa = f"https://www.gobiernodecanarias.org{url_completa}"
            resultados.append((texto, url_completa))
    return resultados

def main():
    """Ejecuta el bot una vez."""
    vistas = cargar_vistas()
    convocatorias = buscar_convocatorias()
    nuevas = [(t, l) for t, l in convocatorias if l not in vistas]

    if nuevas:
        for titulo, enlace in nuevas:
            mensaje = f"📢 Nueva oposición administrativa en Canarias:\n\n{titulo}\n{enlace}"
            enviar_mensaje(mensaje)
            vistas.add(enlace)
        guardar_vistas(vistas)
    else:
        enviar_mensaje("🤖 No hay nuevas convocatorias hoy en el BOC de Canarias 👌")

    print("✅ Proceso completado.")

if __name__ == "__main__":
    main()
