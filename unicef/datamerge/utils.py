import pandas as pd
import json
import logging
from django.http import HttpRequest
from .models import Encuesta  # Adjust the import path according to your project structure
from dotenv import load_dotenv

API_LIMESURVEY = "#########################################################"
INTERNAL_LS_USER = "####"
INTERNAL_LS_PASS = "########"
GITHUB_TOKEN= '#####################################'
logging.basicConfig(level=logging.DEBUG)
# Cargar las variables de entorno desde el archivo .env
load_dotenv()

class MockRequest(HttpRequest):
    def __init__(self, data):
        super().__init__()
        self.method = "POST"
        self.POST = data

def update_encuesta_by_sid(sid):
    from .views import UpdateEncuesta
    if not Encuesta.objects.filter(sid=sid).exists():
        logging.debug(f"update_encuesta_by_sid. sid: {sid}")
        try:
            request_data = {
                "sid": sid,
                "usr": INTERNAL_LS_USER,
                "pass": INTERNAL_LS_PASS,
            }
            mock_request = MockRequest(request_data)
            logging.debug(
                f"update_encuesta_by_sid. mock_request: {mock_request.__dict__}"
            )
            UpdateEncuesta(mock_request)
            encuesta = Encuesta.objects.get(sid=sid) if sid else None
            logging.debug(f"update_encuesta_by_sid. encuesta: {encuesta}")
            return encuesta
        except Exception as e:
            raise Exception(f"Error updating Encuesta with SID: {sid}, error: {str(e)}")
    return Encuesta.objects.get(sid=sid)