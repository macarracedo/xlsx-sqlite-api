# filepath: /home/manuel/GitHub/xlsx-sqlite-api/unicef/datamerge/management/commands/update_encuesta_results.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from unicef.datamerge.models import Encuesta, EncuestaResult

from django.test import RequestFactory
import requests
import logging
import os

API_LIMESURVEY = os.getenv("API_LIMESURVEY")
INTERNAL_LS_USER = os.getenv("INTERNAL_LS_USER")
INTERNAL_LS_PASS = os.getenv("INTERNAL_LS_PASS")

logging.basicConfig(level=logging.INFO)


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


class Command(BaseCommand):
    help = "Update Encuesta results daily"

    def handle(self, *args, **kwargs):
        encuestas = Encuesta.objects.all()
        logging.info(f"API_LIMESURVEY: {API_LIMESURVEY}")
        logging.info(f"INTERNAL_LS_USER: {INTERNAL_LS_USER}")
        logging.info(f"INTERNAL_LS_PASS: {INTERNAL_LS_PASS}")
        for encuesta in encuestas:
            encuesta_sid = encuesta.sid
            self.stdout.write(
                self.style.SUCCESS(f"Updating Encuesta results for {encuesta_sid}")
            )
            payload = {
                "sid": encuesta_sid,
                "usr": INTERNAL_LS_USER,
                "pass": INTERNAL_LS_PASS,
            }

            try:
                # Se realiza la petición POST al servicio externo
                response = requests.post(API_LIMESURVEY, data=payload, verify=False)
                logging.debug(f"UpdateEncuesta. response: {response}")
                response.raise_for_status()  # Lanza excepción en caso de error HTTP
                data_externa = response.json()  # Se decodifica la respuesta JSON
                logging.debug(f"UpdateEncuesta. data_externa:{data_externa}")

                # Fetch the Encuesta object
                encuesta = Encuesta.objects.get(sid=encuesta_sid)

                # Update or create the daily result
                update_or_create_encuesta_result(encuesta, data_externa)

            except requests.RequestException as ex:
                logging.info(f"API_LIMESURVEY: {API_LIMESURVEY}")
                logging.info(f"INTERNAL_LS_USER: {INTERNAL_LS_USER}")
                logging.info(f"INTERNAL_LS_PASS: {INTERNAL_LS_PASS}")
                self.stderr.write(
                    self.style.ERROR(
                        f"Error en la petición al servicio externo, {str(ex)}"
                    )
                )
            except ValueError as ex:
                self.stderr.write(
                    self.style.ERROR(f"Respuesta JSON inválida, {str(ex)}")
                )
            except Encuesta.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Encuesta not found, {str(ex)}"))

        self.stdout.write(self.style.SUCCESS("Successfully updated Encuesta results"))

        # Generate and update CSV files
        self.stdout.write(
            self.style.SUCCESS("Generating and updating CSV files to GitHub...")
        )
        factory = RequestFactory()
        request = factory.get("/")

        from unicef.datamerge.views import (
            update_csv_completitud_by_comunidad,
            update_csv_previstas_by_comunidad,
            update_csv_historico_by_encuesta,
            update_csv_datetime_last_update,
            update_csv_tipologia_by_ccaa,
            update_csv_previstas_alumnado_by_comunidad,
        )

        update_csv_completitud_by_comunidad(request)
        update_csv_previstas_by_comunidad(request)
        update_csv_previstas_alumnado_by_comunidad(request)
        update_csv_historico_by_encuesta(request, back_days=3)
        update_csv_historico_by_encuesta(request, back_days=10)
        update_csv_historico_by_encuesta(request, back_days=30)
        update_csv_tipologia_by_ccaa(request)
        update_csv_datetime_last_update(request)

        self.stdout.write(
            self.style.SUCCESS("Successfully generated and updated CSV files in GitHub")
        )
