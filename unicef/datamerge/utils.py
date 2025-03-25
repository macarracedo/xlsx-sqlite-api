import pandas as pd
import requests
import logging
from django.utils import timezone
from django.http import HttpRequest
from .models import (
    Encuesta,
    EncuestaResult,
)  # Adjust the import path according to your project structure
from dotenv import load_dotenv
import os

API_LIMESURVEY = os.getenv("API_LIMESURVEY")
INTERNAL_LS_USER = os.getenv("INTERNAL_LS_USER")
INTERNAL_LS_PASS = os.getenv("INTERNAL_LS_PASS")
logging.basicConfig(level=logging.DEBUG)
# Cargar las variables de entorno desde el archivo .env
load_dotenv()


def update_encuesta_by_sid(sid, check_results=True):
    logging.debug(f"update_encuesta_by_sid. sid: {sid}")
    if not sid:
        raise ValueError("SID is required")

    payload = {"sid": sid, "usr": INTERNAL_LS_USER, "pass": INTERNAL_LS_PASS}

    try:
        # Se realiza la petición POST al servicio externo
        response = requests.post(API_LIMESURVEY, data=payload, verify=False)
        response.raise_for_status()  # Lanza excepción en caso de error HTTP
        data_externa = response.json()  # Se decodifica la respuesta JSON

        # Create or update the Encuesta object
        encuesta, created = Encuesta.objects.update_or_create(
            sid=sid,
            defaults={
                "titulo": data_externa["Encuesta"]["Titulo encuesta"],
                "fecha_inicio": data_externa["Encuesta"]["Fecha de inicio"],
                "fecha_fin": data_externa["Encuesta"]["Fecha de fin"],
                "activa": data_externa["Encuesta"]["Activa"],
                "url": data_externa["Encuesta"]["Url"],
            },
        )
        if check_results:
            # Update or create the daily result
            now = timezone.now()
            EncuestaResult.objects.update_or_create(
                encuesta=encuesta,
                date=now,
                defaults={
                    "encuestas_cubiertas": data_externa["Encuesta"][
                        "Encuestas cubiertas"
                    ],
                    "encuestas_incompletas": data_externa["Encuesta"][
                        "Encuestas incompletas"
                    ],
                    "encuestas_totales": data_externa["Encuesta"]["Encuestas totales"],
                },
            )
        logging.debug(
            f"update_encuesta_by_sid. encuesta with sid {encuesta.sid} updated"
        )
        return encuesta

    except requests.RequestException as ex:
        raise Exception(f"Error en la petición al servicio externo, {str(ex)}")
    except ValueError as ex:
        raise Exception(f"Respuesta JSON inválida, {str(ex)}")
    except Encuesta.DoesNotExist:
        raise Exception(f"Encuesta not found with SID: {sid}")


def update_or_create_encuesta_result(encuesta, data_externa):
    # Set timezone to Madrid
    timezone.activate("Europe/Madrid")
    madrid_tz = timezone.get_current_timezone()
    now = timezone.localtime(timezone.now(), madrid_tz)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Check if there is already an EncuestaResult for today
    encuesta_result, created = EncuestaResult.objects.update_or_create(
        encuesta=encuesta,
        date__range=(today_start, today_end),
        defaults={
            "date": now,
            "encuestas_cubiertas": data_externa.get("Encuesta", {}).get(
                "Encuestas cubiertas"
            ),
            "encuestas_incompletas": data_externa.get("Encuesta", {}).get(
                "Encuestas incompletas"
            ),
            "encuestas_totales": data_externa.get("Encuesta", {}).get(
                "Encuestas totales"
            ),
        },
    )

    if created:
        logging.info(f"Created new EncuestaResult for {encuesta.sid} on {now.date()}")
    else:
        logging.info(
            f"Updated existing EncuestaResult for {encuesta.sid} on {now.date()}"
        )

    return encuesta_result
