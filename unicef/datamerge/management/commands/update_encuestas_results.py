from django.core.management.base import BaseCommand
from django.test import RequestFactory
import logging

logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    help = "Update Encuesta results daily"

    def handle(self, *args, **kwargs):
        logging.info("Starting update_encuestas_results command")

        # Import the function inside the handle method to avoid circular import
        from unicef.datamerge.views import update_encuestas_results

        factory = RequestFactory()
        request = factory.get("/")

        update_encuestas_results(request)
        logging.info("Finished update_encuestas_results command")
