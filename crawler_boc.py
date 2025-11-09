import os
import requests
from bs4 import BeautifulSoup
from twilio.rest import Client
import json
import time
from datetime import datetime
import logging

# ---------------------------
# CONFIGURACIÓN DEL USUARIO
# ---------------------------

PALABRAS_CLAVE = ["administrativo", "auxiliar administrativo"]
URL_BOC = "https://www.gobiernodecanarias.org/boc/"  # Página base del Boletín
ARCHIVO_MEMORIA = "convocatorias_vistas.json"
REVISION_CADA_SEGUNDOS = 24 * 3600  # 1 vez al día
EJECUTAR_EN_BUCLE = True  # True = revisa cada día, False = una sola ejecución

# Credenciales Twilio (Render las obtiene de las variables de entorno)
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
FROM_WHATSAPP = "whatsapp:+14155238886"  # Número Twilio (sandbox)
TO_WHATSAPP = os.getenv("TO_WHATSAPP")   # Tu número WhatsApp (ej: whatsapp:+34XXXXXXXXX)

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# ---------------------------
# FUNCIONES PRINCIPALES
# ---------------------------

def enviar_mensaje(titulo, enlace):
    """
    Envía un mensaje por WhatsApp usando Twilio.
    """
    try:
        mensaje = f"📢 Nueva oposición administrativa en Canarias:\n\n{titulo}\n{enlace}"
        message = client.messages.create(
            body=mensaje,
            from_=FROM_WHATSAPP,
            to=TO_WHATSAPP
        )
        logging.info(f"Mensaje enviado: {message.sid}")
    except Exception as e:
        logging.exception(f"Error enviando mensaje: {e}")


def cargar_vistas():
    """
    Carga el set de enlaces ya notificados desde un JSON.
    """
    try:
        with open(ARCHIVO_MEMORIA, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()
    except json.JSONDecodeError:
        logging.warning("Archivo de memoria corrupto. Se reinicia la memoria.")
        return set()


def guardar_vistas(vistas):
    """
    Guarda el set de enlaces notificados en un JSON.
    """
    try:
        with open(ARCHIVO_MEMORIA, "w", encoding="utf-8") as f:
            json.dump(list(vistas), f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.exception(f"Error guardando archivo de memoria: {e}")


def buscar_convocatorias():
    """
    Busca enlaces en la página del BOC que contengan alguna palabra clave.
    """
    logging.info(f"🔍 Buscando convocatorias ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})...")
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; BOCBot/1.0; +https://render.com)"}
        resp = requests.get(URL_BOC, timeout=15, headers=headers)
        resp.raise_for_status()
    except Exception as e:
        logging.exception(f"Error descargando la página: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    resultados = []

    for link in soup.find_all("a", href=True):
        texto = (link.get_text(strip=True) or "").lower()
        if any(palabra in texto for palabra in PALABRAS_CLAVE):
            url_completa = link["href"]
            if url_completa.startswith("/"):
                url_completa = f"https://www.gobiernodecanarias.org{url_completa}"
            elif not url_completa.startswith("http"):
                url_completa = f"https://www.gobiernodecanarias.org/{url_completa}"
            resultados.append((texto, url_completa))

    logging.info(f"Resultados encontrados: {len(resultados)}")
    return resultados


def procesar_una_vez():
    """
    Ejecuta una pasada: buscar -> enviar notificaciones -> guardar memoria.
    """
    vistas = cargar_vistas()
    convocatorias = buscar_convocatorias()
    nuevas = [(t, l) for t, l in convocatorias if l not in vistas]

    if not nuevas:
        logging.info("No hay nuevas convocatorias encontradas.")
    else:
        logging.info(f"Nuevas convocatorias a notificar: {len(nuevas)}")

    for titulo, enlace in nuevas:
        enviar_mensaje(titulo, enlace)
        vistas.add(enlace)

    guardar_vistas(vistas)


def main():
    if EJECUTAR_EN_BUCLE:
        logging.info("Iniciando en modo bucle (cada 24h).")
        while True:
            procesar_una_vez()
            logging.info(f"⏳ Esperando {REVISION_CADA_SEGUNDOS} segundos para la siguiente revisión...\n")
            time.sleep(REVISION_CADA_SEGUNDOS)
    else:
        logging.info("Ejecución única (modo prueba).")
        procesar_una_vez()
        logging.info("Ejecución finalizada.")


if __name__ == "__main__":
    main()
