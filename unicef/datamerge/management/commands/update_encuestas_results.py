# filepath: /home/manuel/GitHub/xlsx-sqlite-api/unicef/datamerge/management/commands/update_encuesta_results.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from unicef.datamerge.models import Encuesta, EncuestaResult
from unicef.datamerge.utils import update_encuesta_by_sid
import requests
import logging

API_LIMESURVEY = "https://unicef.ccii.es//cciiAdmin/consultaDatosEncuesta.php"
INTERNAL_LS_USER = "ccii"
INTERNAL_LS_PASS = "ccii2024"

logging.basicConfig(level=logging.DEBUG)

class Command(BaseCommand):
    help = 'Update Encuesta results daily'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        encuestas = Encuesta.objects.all()
        for encuesta in encuestas:
            encuesta_sid = encuesta.sid
            self.stdout.write(self.style.SUCCESS(f'Updating Encuesta results for {encuesta_sid}'))
            payload = {"sid": encuesta_sid, "usr": INTERNAL_LS_USER, "pass": INTERNAL_LS_PASS}

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
                now = timezone.now()
                EncuestaResult.objects.update_or_create(
                    encuesta=encuesta,
                    date=now,
                    defaults={
                        "encuestas_cubiertas": data_externa.get("Encuesta", {}).get("Encuestas cubiertas"),
                        "encuestas_incompletas": data_externa.get("Encuesta", {}).get("Encuestas incompletas"),
                        "encuestas_totales": data_externa.get("Encuesta", {}).get("Encuestas totales"),
                    }
                )

            except requests.RequestException as ex:
                self.stderr.write(self.style.ERROR(f"Error en la petición al servicio externo, {str(ex)}"))
            except ValueError as ex:
                self.stderr.write(self.style.ERROR(f"Respuesta JSON inválida, {str(ex)}"))
            except Encuesta.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Encuesta not found, {str(ex)}"))

        self.stdout.write(self.style.SUCCESS('Successfully updated Encuesta results'))