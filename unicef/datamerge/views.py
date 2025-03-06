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
from django.db.models import Sum, Count, F, FloatField, ExpressionWrapper, Value, OuterRef, Subquery, IntegerField
from django.db.models.functions import Coalesce
import logging
import csv
import re
import io
import os
from io import StringIO
from github import Github
from dotenv import load_dotenv
from django.utils import timezone

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
# Hardcoded values for previstas and centros_previstos
PREVISTAS = {
    "ANDALUCÍA": 14271,
    "ARAGÓN": 3615,
    "CANARIAS": 4600,
    "CANTABRIA": 2667,
    "CASTILLA LEÓN": 4645,
    "CASTILLA LA MANCHA": 4759,
    "CATALUÑA": 12373,
    "MADRID": 11078,
    "NAVARRA": 2831,
    "COMUNIDAD VALENCIANA": 8903,
    "EXTREMADURA": 3280,
    "GALICIA": 4977,
    "BALEARES": 3431,
    "LA RIOJA": 2364,
    "PAIS VASCO": 4732,
    "MELILLA": 2092,
    "CEUTA": 2090,
    "ASTURIAS": 3002,
    "MURCIA": 4290
}

CENTROS_PREVISTOS = {
    "ANDALUCÍA": 72,
    "ARAGÓN": 18,
    "CANARIAS": 23,
    "CANTABRIA": 13,
    "CASTILLA LEÓN": 23,
    "CASTILLA LA MANCHA": 24,
    "CATALUÑA": 63,
    "MADRID": 56,
    "NAVARRA": 14,
    "COMUNIDAD VALENCIANA": 44,
    "EXTREMADURA": 16,
    "GALICIA": 25,
    "BALEARES": 17,
    "LA RIOJA": 12,
    "PAIS VASCO": 24,
    "MELILLA": 10,
    "CEUTA": 10,
    "ASTURIAS": 15,
    "MURCIA": 21
}

# Dictionary for CCAA name mappings
CCAA_NAME_MAPPINGS = {
    "MADRID": "COMUNIDAD DE MADRID",
    "CASTILLA LEÓN": "CASTILLA Y LEÓN",
    "CASTILLA LA MANCHA": "CASTILLA-LA MANCHA",
    "PAIS VASCO": "PAÍS VASCO",
    "NAVARRA": "COMUNIDAD FORAL DE NAVARRA",
    "ASTURIAS": "PRINCIPADO DE ASTURIAS",
    "BALEARES": "ISLAS BALEARES",
    "MURCIA": "REGIÓN DE MURCIA"
}

logging.basicConfig(level=logging.INFO)
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

        pri_encuesta = update_encuesta_by_sid(pri_sid, check_results=False) if pri_sid else None
        sec_encuesta = update_encuesta_by_sid(sec_sid, check_results=False) if sec_sid else None
        pro_encuesta = update_encuesta_by_sid(pro_sid, check_results=False) if pro_sid else None
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
            #     logging.debug(f"bulk_create_csv. colegio {nombre} with cid {cid} already exists. Skipping")
            #     continue

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

            # Check if Colegio already exists
            if Colegio.objects.filter(cid=cid).exists():
                logging.debug(f"bulk_create_csv. colegio {nombre} with cid {cid} already exists. Skipping")
                continue

            try:
                pri_encuesta = update_encuesta_by_sid(pri_sid, check_results=False) if pri_sid else None
                sec_encuesta = update_encuesta_by_sid(sec_sid, check_results=False) if sec_sid else None
                pro_encuesta = update_encuesta_by_sid(pro_sid, check_results=False) if pro_sid else None
            except Exception as e:
                logging.error(f"Error updating encuesta for Colegio {nombre} with cid {cid}. Error: {e}")
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


    @action(detail=False, methods=["get"])
    def generate_csv_completitud_by_comunidad(self, request, *args, **kwargs):
        """Generate a CSV file from data stored in the database, grouped by comunidad autónoma."""
        # Subqueries for the latest 'encuestas_totales'
        latest_pri_totales = EncuestaResult.objects.filter(
            encuesta=OuterRef('pri_sid')
        ).order_by('-date').values('encuestas_totales')[:1]
        latest_sec_totales = EncuestaResult.objects.filter(
            encuesta=OuterRef('sec_sid')
        ).order_by('-date').values('encuestas_totales')[:1]
        latest_pro_totales = EncuestaResult.objects.filter(
            encuesta=OuterRef('pro_sid')
        ).order_by('-date').values('encuestas_totales')[:1]

        # Subqueries for the latest 'encuestas_cubiertas'
        latest_pri_cubiertas = EncuestaResult.objects.filter(
            encuesta=OuterRef('pri_sid')
        ).order_by('-date').values('encuestas_cubiertas')[:1]
        latest_sec_cubiertas = EncuestaResult.objects.filter(
            encuesta=OuterRef('sec_sid')
        ).order_by('-date').values('encuestas_cubiertas')[:1]
        latest_pro_cubiertas = EncuestaResult.objects.filter(
            encuesta=OuterRef('pro_sid')
        ).order_by('-date').values('encuestas_cubiertas')[:1]

        # Subqueries for the latest 'encuestas_incompletas'
        latest_pri_incompletas = EncuestaResult.objects.filter(
            encuesta=OuterRef('pri_sid')
        ).order_by('-date').values('encuestas_incompletas')[:1]
        latest_sec_incompletas = EncuestaResult.objects.filter(
            encuesta=OuterRef('sec_sid')
        ).order_by('-date').values('encuestas_incompletas')[:1]
        latest_pro_incompletas = EncuestaResult.objects.filter(
            encuesta=OuterRef('pro_sid')
        ).order_by('-date').values('encuestas_incompletas')[:1]

        # Annotate each Colegio with its most recent results per encuesta field.
        colegios_qs = Colegio.objects.annotate(
            pri_totales=Coalesce(Subquery(latest_pri_totales, output_field=IntegerField()), Value(0)),
            sec_totales=Coalesce(Subquery(latest_sec_totales, output_field=IntegerField()), Value(0)),
            pro_totales=Coalesce(Subquery(latest_pro_totales, output_field=IntegerField()), Value(0)),
            
            pri_cubiertas=Coalesce(Subquery(latest_pri_cubiertas, output_field=IntegerField()), Value(0)),
            sec_cubiertas=Coalesce(Subquery(latest_sec_cubiertas, output_field=IntegerField()), Value(0)),
            pro_cubiertas=Coalesce(Subquery(latest_pro_cubiertas, output_field=IntegerField()), Value(0)),
            
            pri_incompletas=Coalesce(Subquery(latest_pri_incompletas, output_field=IntegerField()), Value(0)),
            sec_incompletas=Coalesce(Subquery(latest_sec_incompletas, output_field=IntegerField()), Value(0)),
            pro_incompletas=Coalesce(Subquery(latest_pro_incompletas, output_field=IntegerField()), Value(0)),
        ).annotate(
            # Sum the values from each encuesta relationship
            encuestas_totales=F('pri_totales') + F('sec_totales') + F('pro_totales'),
            encuestas_cubiertas=F('pri_cubiertas') + F('sec_cubiertas') + F('pro_cubiertas'),
            encuestas_incompletas=F('pri_incompletas') + F('sec_incompletas') + F('pro_incompletas')
        )

        # Group the data by comunidad_autonoma.
        colegios = colegios_qs.values('comunidad_autonoma').annotate(
            total_centros=Count('id'),
            encuestas_totales=Sum('encuestas_totales'),
            encuestas_cubiertas=Sum('encuestas_cubiertas'),
            encuestas_incompletas=Sum('encuestas_incompletas'),
        ).annotate(
            porcentaje=ExpressionWrapper(
                F('encuestas_cubiertas') * 100.0 / F('encuestas_totales'),
                output_field=FloatField()
            )
        ).values(
            "comunidad_autonoma",
            "encuestas_totales",
            "encuestas_cubiertas",
            "encuestas_incompletas",
            "porcentaje",
            "total_centros",
        )

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="completitud_by_comunidad.csv"'

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

        # Initialize totals
        total_encuestas_totales = 0
        total_encuestas_cubiertas = 0
        total_encuestas_incompletas = 0
        total_total_centros = 0

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
            # Accumulate totals
            total_encuestas_totales += colegio["encuestas_totales"]
            total_encuestas_cubiertas += colegio["encuestas_cubiertas"]
            total_encuestas_incompletas += colegio["encuestas_incompletas"]
            total_total_centros += colegio["total_centros"]

        # Calculate total percentage
        total_porcentaje = (total_encuestas_cubiertas * 100.0 / total_encuestas_totales) if total_encuestas_totales > 0 else 0

        # Write totals row
        writer.writerow(
            [
                "Totales",
                total_encuestas_totales,
                total_encuestas_cubiertas,
                total_encuestas_incompletas,
                total_porcentaje,
                total_total_centros,
            ]
        )
        response = update_ccaa_names_in_csv(response, filename="completitud_by_comunidad.csv")
        response = sort_csv_by_comunidad(response, filename="completitud_by_comunidad.csv")
        return response
    
    @action(detail=False, methods=["get"])
    def generate_csv_previstas_by_comunidad(self, request, *args, **kwargs):
        """Generate a CSV file from data stored in the database, grouped by comunidad autónoma."""
        
        # Subqueries to get the most recent EncuestaResult for each encuesta field
        latest_pri = EncuestaResult.objects.filter(
            encuesta=OuterRef('pri_sid')
        ).order_by('-date').values('encuestas_totales')[:1]

        latest_sec = EncuestaResult.objects.filter(
            encuesta=OuterRef('sec_sid')
        ).order_by('-date').values('encuestas_totales')[:1]

        latest_pro = EncuestaResult.objects.filter(
            encuesta=OuterRef('pro_sid')
        ).order_by('-date').values('encuestas_totales')[:1]

        # Annotate each Colegio with its latest results
        colegios_qs = Colegio.objects.annotate(
            pri_realizadas=Coalesce(Subquery(latest_pri, output_field=IntegerField()), Value(0)),
            sec_realizadas=Coalesce(Subquery(latest_sec, output_field=IntegerField()), Value(0)),
            pro_realizadas=Coalesce(Subquery(latest_pro, output_field=IntegerField()), Value(0)),
        ).annotate(
            # Sum the latest results from the three related encuestas
            realizadas=F('pri_realizadas') + F('sec_realizadas') + F('pro_realizadas')
        )

        # Group by comunidad_autonoma and aggregate over colegios
        colegios = colegios_qs.values('comunidad_autonoma').annotate(
            centros_actuales=Count('id'),
            realizadas=Sum('realizadas')
        ).values('comunidad_autonoma', 'realizadas', 'centros_actuales')

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="previstas_by_comunidad.csv"'

        writer = csv.writer(response)
        # Write the header row
        writer.writerow(
            [
                "CCAA",
                "Previstas",
                "Realizadas",
                "Faltan",
                "Porcentaje",
                "Centros previstos",
                "Centros actuales",
                "Porcentaje1",
            ]
        )

        # Initialize totals
        total_previstas = 0
        total_realizadas = 0
        total_faltan = 0
        total_centros_previstos = 0
        total_centros_actuales = 0

        # Write data rows
        for colegio in colegios:
            comunidad = colegio["comunidad_autonoma"]
            previstas = PREVISTAS.get(comunidad, 0)
            realizadas = colegio["realizadas"]
            faltan = previstas - realizadas
            porcentaje = (realizadas / previstas) * 100 if previstas > 0 else 0
            centros_previstos = CENTROS_PREVISTOS.get(comunidad, 0)
            centros_actuales = colegio["centros_actuales"]
            porcentaje1 = (centros_actuales / centros_previstos) * 100 if centros_previstos > 0 else 0

            writer.writerow(
                [
                    comunidad,
                    previstas,
                    realizadas,
                    faltan,
                    f"{porcentaje:.2f}%",
                    centros_previstos,
                    centros_actuales,
                    f"{porcentaje1:.2f}%",
                ]
            )

            # Accumulate totals
            total_previstas += previstas
            total_realizadas += realizadas
            total_faltan += faltan
            total_centros_previstos += centros_previstos
            total_centros_actuales += centros_actuales

        # Calculate total percentages
        total_porcentaje = (total_realizadas / total_previstas) * 100 if total_previstas > 0 else 0
        total_porcentaje1 = (total_centros_actuales / total_centros_previstos) * 100 if total_centros_previstos > 0 else 0

        # Write totals row
        writer.writerow(
            [
                "Totales",
                total_previstas,
                total_realizadas,
                total_faltan,
                f"{total_porcentaje:.2f}%",
                total_centros_previstos,
                total_centros_actuales,
                f"{total_porcentaje1:.2f}%",
            ]
        )
        response = update_ccaa_names_in_csv(response, filename="previstas_by_comunidad.csv")
        response = sort_csv_by_comunidad(response, filename="previstas_by_comunidad.csv")
        return response

@csrf_exempt
@require_GET
def update_csv_completitud_by_comunidad(request):
    
    response = ColegioViewSet().generate_csv_completitud_by_comunidad(request)
    
    # Upload csv_data to github
    csv_data =  response.getvalue()
    logging.debug(f"update_csv_completitud_by_comunidad. csv_data: {csv_data}")
    push_to_gh_repo(csv_data=csv_data, file_path="data/completitud_by_comunidad.csv")
    
    return HttpResponse("CSV updated successfully")

@csrf_exempt
@require_GET
def update_csv_previstas_by_comunidad(request):
    
    response = ColegioViewSet().generate_csv_previstas_by_comunidad(request)
    
    # Upload csv_data to github
    csv_data =  response.getvalue()
    logging.debug(f"update_csv_previstas_by_comunidad. csv_data: {csv_data}")
    push_to_gh_repo(csv_data=csv_data, file_path="data/previstas_by_comunidad.csv")
    
    return HttpResponse("CSV updated successfully")

def update_ccaa_names_in_csv(response, filename="colegios_data.csv"):
    """Update the names in the CCAA column of given CSV based on a constant dictionary."""
    # Get the CSV data from the generate_csv_previstas_by_comunidad method
    csv_data = response.content.decode('utf-8')

    # Read the CSV data
    csv_file = io.StringIO(csv_data)
    reader = csv.reader(csv_file)
    rows = list(reader)

    # Update the CCAA names
    header = rows[0]
    data_rows = rows[1:]
    updated_rows = [header]

    for row in data_rows:
        comunidad = row[0]
        updated_comunidad = CCAA_NAME_MAPPINGS.get(comunidad, comunidad)
        row[0] = updated_comunidad
        updated_rows.append(row)

    # Create the HttpResponse object with the updated CSV data
    updated_response = HttpResponse(content_type="text/csv")
    updated_response["Content-Disposition"] = f'attachment; filename={filename}'

    writer = csv.writer(updated_response)
    writer.writerows(updated_rows)

    return updated_response

def sort_csv_by_comunidad(response, filename="sorted_colegios_data.csv"):
    """Sort the rows of a CSV file alphabetically by the CCAA or comunidad_autonoma column."""
    # Get the CSV data from the update_ccaa_names_in_csv method
    csv_data = response.content.decode('utf-8')

    # Read the CSV data
    csv_file = io.StringIO(csv_data)
    reader = csv.reader(csv_file)
    rows = list(reader)

    # Identify the column index for CCAA or comunidad
    header = rows[0]
    data_rows = rows[1:]
    if "CCAA" in header:
        sort_index = header.index("CCAA")
    elif "comunidad" in header:
        sort_index = header.index("comunidad")
    else:
        # If neither column is found, return the original response
        return response

    # Sort the data rows alphabetically by the identified column
    sorted_data_rows = sorted(data_rows, key=lambda row: row[sort_index])
    
    # Move the last row to the top
    if sorted_data_rows:
        last_row = sorted_data_rows.pop()
        sorted_data_rows.insert(0, last_row)

    # Create the HttpResponse object with the sorted CSV data
    sorted_response = HttpResponse(content_type="text/csv")
    sorted_response["Content-Disposition"] = f'attachment; filename={filename}'

    writer = csv.writer(sorted_response)
    writer.writerow(header)
    writer.writerows(sorted_data_rows)

    return sorted_response

def push_to_gh_repo(csv_data, file_path="data/test/colegios_data.csv", commit_message="[BOT] Update colegios data CSV"):
    """This method pushes csv data to a GitHub repository.

    Args:
        csv_data (str): The CSV data to be pushed.
    """
    # GitHub repository and file details
    repo_name = "macarracedo/xlsx-sqlite-api"


    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(repo_name)
    
    print(f"github token: {GITHUB_TOKEN}")
    print(f"repo: {repo}")

    try:
        # Get the file if it exists
        contents = repo.get_contents(file_path)
        repo.update_file(contents.path, commit_message, csv_data, contents.sha)
    except Exception as e:
        # If the file does not exist, create it
        repo.create_file(file_path, commit_message, csv_data)