from django.core.management.base import BaseCommand
from unicef.datamerge.views import (
    update_csv_completitud_by_comunidad,
    update_csv_previstas_by_comunidad,
    update_csv_historico_by_encuesta,
    update_csv_datetime_last_update
)
from django.test import RequestFactory
import logging

logging.basicConfig(level=logging.INFO)

class Command(BaseCommand):
    help = 'Generate and update CSV files and upload them to GitHub without querying LimeSurvey or updating survey results'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Generating and updating CSV files to GitHub...'))
        factory = RequestFactory()
        request = factory.get('/')

        update_csv_completitud_by_comunidad(request)
        update_csv_previstas_by_comunidad(request)
        update_csv_historico_by_encuesta(request)
        update_csv_datetime_last_update(request)

        self.stdout.write(self.style.SUCCESS('Successfully generated and updated CSV files in GitHub'))