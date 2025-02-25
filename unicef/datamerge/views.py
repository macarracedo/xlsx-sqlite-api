import requests
from django.contrib.auth.models import Group, User
from rest_framework import permissions, viewsets, status, views
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from rest_framework.decorators import action
from django.http import JsonResponse, HttpResponse
from unicef.datamerge.serializers import (
    GroupSerializer,
    UserSerializer,
    EncuestaSerializer,
    EncuestaResult,
    ColegioSerializer,
    FileUploadSerializer,
)
from unicef.datamerge.utils import update_encuesta_by_sid
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from unicef.datamerge.models import Encuesta, Colegio, EncuestaResult
from django.db.models import Sum, Count, F, FloatField, ExpressionWrapper
import logging
import csv
from io import StringIO
from github import Github
from dotenv import load_dotenv
from django.utils import timezone

API_LIMESURVEY = "https://unicef.ccii.es//cciiAdmin/consultaDatosEncuesta.php"
INTERNAL_LS_USER = "ccii"
INTERNAL_LS_PASS = "ccii2024"
GITHUB_TOKEN= '#####################################'
logging.basicConfig(level=logging.DEBUG)
# Cargar las variables de entorno desde el archivo .env
load_dotenv()

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """

    queryset = Group.objects.all().order_by("name")
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class EncuestaViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Encuestas to be viewed or edited.
    """

    queryset = Encuesta.objects.all().order_by("sid")
    serializer_class = EncuestaSerializer
    permission_classes = [permissions.IsAuthenticated]


class ColegioViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Colegios to be created, viewed or edited.
    """

    queryset = Colegio.objects.all().order_by("cid")
    serializer_class = ColegioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """This method is used to create a new Colegio object.
        Args:
            request (_type_): _description_

        Returns:
            _type_: _description_

        """
        cid = request.POST.get("cid")
        nombre = request.POST.get("nombre")
        comunidad_autonoma = request.POST.get("comunidad_autonoma")
        telefono = request.POST.get("telefono")
        email = request.POST.get("email")
        pri_sid = request.POST.get("pri_sid")
        sec_sid = request.POST.get("sec_sid")
        pro_sid = request.POST.get("pro_sid")
        if not all([cid, nombre, comunidad_autonoma]):
            return Response(
                {"detail": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST
            )
        payload = {
            "nombre": nombre,
            "comunidad_autonoma": comunidad_autonoma,
            "telefono": telefono,
            "email": email,
            "pri_sid": pri_sid,
            "sec_sid": sec_sid,
            "pro_sid": pro_sid,
        }

        pri_encuesta = update_encuesta_by_sid(pri_sid) if pri_sid else None
        sec_encuesta = update_encuesta_by_sid(sec_sid) if sec_sid else None
        pro_encuesta = update_encuesta_by_sid(pro_sid) if pro_sid else None
        try:
            # Se realiza la petición POST al servicio externo
            Colegio.objects.update_or_create(
                cid=cid,
                defaults={
                    "nombre": nombre,
                    "comunidad_autonoma": comunidad_autonoma,
                    "telefono": telefono,
                    "email": email,
                    "pri_sid": pri_encuesta,
                    "sec_sid": sec_encuesta,
                    "pro_sid": pro_encuesta,
                },
            )
        except requests.RequestException as ex:
            return JsonResponse(
                {
                    "error": "Error al actualizar o crear el objeto Colegio",
                    "detalle": str(ex),
                },
                status=500,
            )
        return JsonResponse(payload)

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser], serializer_class=FileUploadSerializer)
    def cocina_csv(self, request, *args, **kwargs):
        """This method is used to create multiple Colegio objects from a CSV file.
        Args:
            request (_type_): _description_

        Returns:
            _type_: _description_

        """
        # serializer_class = FileUploadSerializer
        file = request.FILES.get("cocina_csv")
        if not file:
            return Response(
                {"detail": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
            )
        logging.debug(f"bulk_create_csv. file: {file}")
        created_colegios = []
        csv_file = StringIO(file.read().decode("utf-8"))
        reader = csv.DictReader(csv_file)

        for row in reader:
            nombre = row["AN"]
            comunidad_autonoma = row["CCAA"]
            ssid = row["SSID"]
            id_de_centro = row["ID DE CENTRO"]
            url = row["URL"]
            tipologia = row["TIPOLOGIA"]

            cid, nivel = id_de_centro.split(" - ")

            if not all([cid, nombre, comunidad_autonoma, ssid, url, tipologia]):
                return Response(
                    {"detail": "Missing parameters for one or more colegios"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if Colegio already exists
            if Colegio.objects.filter(cid=cid).exists():
                continue

            # Create or update Encuesta. Alse gets its results from LimeSurvey
            # Check SIDs exist in database, if not, run UpdateEncuesta
            encuesta = update_encuesta_by_sid(ssid) if ssid else None

            # Create Colegio
            colegio, created = Colegio.objects.update_or_create(
                cid=cid,
                defaults={
                    "nombre": nombre,
                    "comunidad_autonoma": comunidad_autonoma,
                    "telefono": "",
                    "email": "",
                    "pri_sid": encuesta if "Primaria" in nivel else None,
                    "sec_sid": encuesta if "Secundaria" in nivel else None,
                    "pro_sid": encuesta if "Profesorado" in nivel else None,
                },
            )
            logging.debug(f"bulk_create_csv. colegio: {colegio}")
            created_colegios.append(colegio)

        serializer = ColegioSerializer(created_colegios, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@csrf_exempt
@require_POST
def UpdateEncuesta(request):
    """This method is used to update the number of responses of an Encuesta object.
        Sends a GET request with the url of the Encuesta object to LimeSurvey API and retrieves the number of responses.
    Args:
        request (HttpRequest): The HTTP request containing the sid, usr, and pass parameters.

    Returns:
        JsonResponse: A JSON response containing the updated data or an error message.
    """
    logging.debug(f"UpdateEncuesta. request: {request.__dict__}")
    sid = request.POST.get("sid")
    usr = request.POST.get("usr")
    password = request.POST.get("pass")
    logging.debug(f"UpdateEncuesta. sid: {sid}")
    if not all([sid, usr, password]):
        return JsonResponse(
            {"detail": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST
        )

    payload = {"sid": sid, "usr": usr, "pass": password}

    try:
        # Se realiza la petición POST al servicio externo
        response = requests.post(API_LIMESURVEY, data=payload, verify=False)
        logging.debug(f"UpdateEncuesta. response: {response}")
        response.raise_for_status()  # Lanza excepción en caso de error HTTP
        data_externa = response.json()  # Se decodifica la respuesta JSON
        logging.debug(f"UpdateEncuesta. data_externa:{data_externa}")

        # Fetch the Encuesta object
        encuesta = Encuesta.objects.get(sid=sid)

        # Update or create the daily result
        today = timezone.now().date()
        EncuestaResult.objects.update_or_create(
            encuesta=encuesta,
            date=today,
            defaults={
                "encuestas_cubiertas": data_externa.get("Encuesta", {}).get("Encuestas cubiertas"),
                "encuestas_incompletas": data_externa.get("Encuesta", {}).get("Encuestas incompletas"),
                "encuestas_totales": data_externa.get("Encuesta", {}).get("Encuestas totales"),
            }
        )

    except requests.RequestException as ex:
        return JsonResponse(
            {"error": "Error en la petición al servicio externo", "detalle": str(ex)},
            status=500,
        )
    except ValueError as ex:
        return JsonResponse(
            {"error": "Respuesta JSON inválida", "detalle": str(ex)}, status=500
        )
    except Encuesta.DoesNotExist:
        return JsonResponse(
            {"error": "Encuesta not found"}, status=status.HTTP_404_NOT_FOUND
        )

    return JsonResponse(data_externa)


def push_to_gh_repo(csv_data):
    """This method pushes csv data to a GitHub repository.

    Args:
        csv_data (str): The CSV data to be pushed.
    """
    # GitHub repository and file details
    repo_name = "macarracedo/xlsx-sqlite-api"
    file_path = "data/colegios_data.csv"
    commit_message = "[BOT] Update colegios data CSV"


    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(repo_name)

    try:
        # Get the file if it exists
        contents = repo.get_contents(file_path)
        repo.update_file(contents.path, commit_message, csv_data, contents.sha)
    except Exception as e:
        # If the file does not exist, create it
        repo.create_file(file_path, commit_message, csv_data)

@csrf_exempt
@require_GET
def generate_csv(request):
    """Generate a CSV file from data stored in the database."""
    # Query the database to get the required data
    colegios = (
        Colegio.objects.values("comunidad_autonoma")
        .annotate(
            encuestas_totales=Sum("pri_sid__encuestas_totales")
            + Sum("sec_sid__encuestas_totales")
            + Sum("pro_sid__encuestas_totales"),
            encuestas_cubiertas=Sum("pri_sid__encuestas_cubiertas")
            + Sum("sec_sid__encuestas_cubiertas")
            + Sum("pro_sid__encuestas_cubiertas"),
            encuestas_incompletas=Sum("pri_sid__encuestas_incompletas")
            + Sum("sec_sid__encuestas_incompletas")
            + Sum("pro_sid__encuestas_incompletas"),
            total_centros=Count("id"),
        )
        .annotate(
            porcentaje=ExpressionWrapper(
                F("encuestas_cubiertas") * 100.0 / F("encuestas_totales"),
                output_field=FloatField(),
            )
        )
        .values(
            "comunidad_autonoma",
            "encuestas_totales",
            "encuestas_cubiertas",
            "encuestas_incompletas",
            "porcentaje",
            "total_centros",
        )
    )

    
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="colegios_data.csv"'

    writer = csv.writer(response)
    # Write the header row
    writer.writerow(
        [
            "comunidad",
            "encuestas_totales",
            "encuestas_cubiertas",
            "encuestas_incompletas",
            "porcentaje",
            "total_centros",
        ]
    )

    # Write data rows
    for colegio in colegios:
        writer.writerow(
            [
                colegio["comunidad_autonoma"],
                colegio["encuestas_totales"],
                colegio["encuestas_cubiertas"],
                colegio["encuestas_incompletas"],
                colegio["porcentaje"],
                colegio["total_centros"],
            ]
        )
    # Upload csv_data to github
    csv_data =  response.getvalue()
    logging.debug(f"generate_csv. csv_data: {csv_data}")
    push_to_gh_repo(csv_data=csv_data)

    return None


class FileUploadView(views.APIView):
    parser_classes = [MultiPartParser]
    serializer_class = FileUploadSerializer
    
    def create(self, request):
        file_uploaded = request.FILES.get('file_uploaded')
        content_type = file_uploaded.content_type
        response = "POST API and you have uploaded a {} file".format(content_type)
        return Response(response)

    def put(self, request, filename, format=None):
        file_obj = request.data['file']
        # ...
        # do some stuff with uploaded file
        # ...
        return Response(status=204)