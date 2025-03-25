from django.core.management.base import BaseCommand
from unicef.datamerge.views import update_encuestas_results
import logging

logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    help = "Update Encuesta results daily"

    def handle(self, *args, **kwargs):
        logging.info("Starting update_encuestas_results command")
        update_encuestas_results()
        logging.info("Finished update_encuestas_results command")
