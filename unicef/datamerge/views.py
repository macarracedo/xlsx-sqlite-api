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
import re
from io import StringIO
from github import Github
from dotenv import load_dotenv
from django.utils import timezone

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
    def cocina_csv_old(self, request, *args, **kwargs):
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

            # remove all letter P, D and S contained in the string
            cid = re.sub(r'[PDS]', '', cid)
            if not all([cid, nombre, comunidad_autonoma, ssid, url, tipologia]):
                return Response(
                    {"detail": "Missing parameters for one or more colegios"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if Colegio already exists
            # if Colegio.objects.filter(cid=cid).exists():
            #    continue

            try:
                # Create or update Encuesta. Also gets its results from LimeSurvey
                # Check SIDs exist in database, if not, run UpdateEncuesta
                encuesta = update_encuesta_by_sid(ssid, check_results=False) if ssid else None
            except Exception as e:
                logging.error(f"Error updating encuesta for SSID {ssid}: {e}")
                continue

            # Create or update Colegio
            try:
                colegio = Colegio.objects.get(cid=cid)
                colegio.nombre = nombre
                colegio.comunidad_autonoma = comunidad_autonoma
                colegio.telefono = colegio.telefono or ""
                colegio.email = colegio.email or ""
                colegio.pri_sid = encuesta if "Primaria" in nivel else colegio.pri_sid
                colegio.sec_sid = encuesta if "Secundaria" in nivel else colegio.sec_sid
                colegio.pro_sid = encuesta if "Profesorado" in nivel else colegio.pro_sid
                colegio.save()
                created = False
            except Colegio.DoesNotExist:
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
            logging.debug(f"bulk_create_csv. colegio {colegio} created")
            created_colegios.append(colegio)

        serializer = ColegioSerializer(created_colegios, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser], serializer_class=FileUploadSerializer)
    def cocina_csv_new(self, request, *args, **kwargs):
        """This method is used to create multiple Colegio objects from a CSV file with a new format.
        Args:
            request (_type_): _description_

        Returns:
            _type_: _description_

        """
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
            nombre = row["CENTRO"]
            comunidad_autonoma = row["CA"]
            cod_cid = row["Codigo interno"]
            pri_url = row["PRIMARIA"]
            sec_url = row["SECUNDARIA"]
            pro_url = row["PROFESORADO"]
            
            pri_sid = re.search(r'sid=(\d{6})', pri_url).group(1) if pri_url else None
            sec_sid = re.search(r'sid=(\d{6})', sec_url).group(1) if sec_url else None
            pro_sid = re.search(r'sid=(\d{6})', pro_url).group(1) if pro_url else None
            

            # Remove all letter P, D and S contained in the string from each ID
            cid = re.sub(r'[PDS]', '', cod_cid) # este se usará para el id del colegio (cid)
            sec_sid = re.sub(r'[PDS]', '', sec_sid)
            pro_sid = re.sub(r'[PDS]', '', pro_sid)

            if not all([nombre, comunidad_autonoma, pri_sid, pri_url, sec_sid, sec_url, pro_sid, pro_url]):
                return Response(
                    {"detail": "Missing parameters for one or more colegios"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                pri_encuesta = update_encuesta_by_sid(pri_sid, check_results=False) if pri_sid else None
                sec_encuesta = update_encuesta_by_sid(sec_sid, check_results=False) if sec_sid else None
                pro_encuesta = update_encuesta_by_sid(pro_sid, check_results=False) if pro_sid else None
            except Exception as e:
                logging.error(f"Error updating encuesta for Colegio {nombre} with SIDs {pri_sid}, {sec_sid}, {pro_sid}: {e}")
                continue

            try:
                colegio = Colegio.objects.get(cid=cid)
                colegio.nombre = nombre
                colegio.comunidad_autonoma = comunidad_autonoma
                colegio.telefono = colegio.telefono or ""
                colegio.email = colegio.email or ""
                colegio.pri_sid = pri_encuesta
                colegio.sec_sid = sec_encuesta
                colegio.pro_sid = pro_encuesta
                colegio.save()
                created = False
            except Colegio.DoesNotExist:
                colegio, created = Colegio.objects.update_or_create(
                    cid=cid,
                    defaults={
                        "nombre": nombre,
                        "comunidad_autonoma": comunidad_autonoma,
                        "telefono": "",
                        "email": "",
                        "pri_sid": pri_encuesta,
                        "sec_sid": sec_encuesta,
                        "pro_sid": pro_encuesta,
                    },
                )
            logging.debug(f"bulk_create_csv. colegio {colegio} created")
            created_colegios.append(colegio)

        serializer = ColegioSerializer(created_colegios, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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