import requests
from django.shortcuts import render
from django.contrib.auth.models import Group, User
from rest_framework import permissions, viewsets, status
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.parsers import JSONParser
from rest_framework.decorators import action
from django.http import JsonResponse, HttpRequest
from unicef.datamerge.serializers import (
    GroupSerializer,
    UserSerializer,
    EncuestaSerializer,
    ColegioSerializer,
)
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from openpyxl import load_workbook
from unicef.datamerge.models import Encuesta, Colegio
from django.db.models import Sum
from django.db import IntegrityError
import logging

API_LIMESURVEY = "https://unicef.ccii.es//cciiAdmin/consultaDatosEncuesta.php"
INTERNAL_LS_USER = "ccii"
INTERNAL_LS_PASS = "ccii2024"
logging.basicConfig(level=logging.DEBUG)

class MockRequest(HttpRequest):
    def __init__(self, data):
        super().__init__()
        self.method = 'POST'
        self.POST = data
        
def update_encuesta_by_sid(sid):
    if not Encuesta.objects.filter(sid=sid).exists():
        logging.debug(f"update_encuesta_by_sid. sid: {sid}")
        try:
            request_data = {
                "sid": sid,
                "usr": INTERNAL_LS_USER,
                "pass": INTERNAL_LS_PASS
            }
            mock_request = MockRequest(request_data)
            logging.debug(f"update_encuesta_by_sid. mock_request: {mock_request.__dict__}")
            UpdateEncuesta(mock_request)
            encuesta = Encuesta.objects.get(sid=sid) if sid else None
            logging.debug(f"update_encuesta_by_sid. encuesta: {encuesta}")
            return encuesta
        except Exception as e:
            raise Exception(f"Error updating Encuesta with SID: {sid}, error: {str(e)}")
    return Encuesta.objects.get(sid=sid)

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

    def update(self, request, *args, **kwargs):
        """This method is used to update the number of responses of an Encuesta object.
        Sends a GET request with the url of the Encuesta object to LimeSurvey API and retrives the number of responses.
        Args:
            request (_type_): _description_

        Returns:
            _type_: _description_

        """
        instance = self.get_object()
        sid = instance.sid
        usr = request.POST.get("usr")
        password = request.POST.get("pass")

        if not all([sid, usr, password]):
            return Response(
                {"detail": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST
            )

        payload = {"sid": sid, "usr": usr, "pass": password}

        try:
            # Se realiza la petición POST al servicio externo
            response = requests.post(API_LIMESURVEY, data=payload, verify=False)
            response.raise_for_status()  # Lanza excepción en caso de error HTTP
            data_externa = response.json()  # Se decodifica la respuesta JSON
            logging.debug("Encuesta. update. data_externa:", data_externa)
            # Aquí se puede actualizar la base de datos local utilizando data_externa
            # Por ejemplo, se podría actualizar o crear un objeto Survey:
            Encuesta.objects.update_or_create(
                sid=data_externa.get("Encuesta", {}).get("SID"),
                defaults={
                    "titulo": data_externa.get("Encuesta", {}).get("Titulo encuesta"),
                    "activa": data_externa.get("Encuesta", {}).get("Activa"),
                    "url": data_externa.get("Encuesta", {}).get("Url"),
                    "fecha_inicio": data_externa.get("Encuesta", {}).get(
                        "Fecha inicio"
                    ),
                    "fecha_fin": data_externa.get("Encuesta", {}).get("Fecha fin"),
                    "encuestas_cubiertas": data_externa.get("Encuesta", {}).get(
                        "Encuestas cubiertas"
                    ),
                    "encuestas_incompletas": data_externa.get("Encuesta", {}).get(
                        "Encuestas incompletas"
                    ),
                    "encuestas_totales": data_externa.get("Encuesta", {}).get(
                        "Encuestas totales"
                    ),
                    # Otros campos según sea necesario
                },
            )
        except requests.RequestException as ex:
            return JsonResponse(
                {
                    "error": "Error en la petición al servicio externo",
                    "detalle": str(ex),
                },
                status=500,
            )
        except ValueError as ex:
            return JsonResponse(
                {"error": "Respuesta JSON inválida", "detalle": str(ex)}, status=500
            )

        return JsonResponse(data_externa)
    
    @action(detail=False, methods=["post"], parser_classes=[JSONParser])
    def bulk_create(self, request, *args, **kwargs):
        """This method is used to create multiple Encuesta objects.
        Args:
            request (_type_): _description_

        Returns:
            _type_: _description_

        """
        encuestas = request.data.get("encuestas", [])
        if not encuestas:
            return Response(
                {"detail": "No encuestas provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        created_encuestas = []
        for encuesta_data in encuestas:
            sid = encuesta_data.get("sid")
            titulo = encuesta_data.get("titulo")
            activa = encuesta_data.get("activa")
            url = encuesta_data.get("url")
            fecha_inicio = encuesta_data.get("fecha_inicio")
            fecha_fin = encuesta_data.get("fecha_fin")
            encuestas_cubiertas = encuesta_data.get("encuestas_cubiertas")
            encuestas_incompletas = encuesta_data.get("encuestas_incompletas")
            encuestas_totales = encuesta_data.get("encuestas_totales")
            if not all([sid, titulo, activa]):
                return Response(
                    {"detail": "Missing parameters for one or more encuestas"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                encuesta, created = Encuesta.objects.update_or_create(
                    sid=sid,
                    defaults={
                        "titulo": titulo,
                        "activa": activa,
                        "url": url,
                        "fecha_inicio": fecha_inicio,
                        "fecha_fin": fecha_fin,
                        "encuestas_cubiertas": encuestas_cubiertas,
                        "encuestas_incompletas": encuestas_incompletas,
                        "encuestas_totales": encuestas_totales,
                    },
                )
                created_encuestas.append(encuesta)
            except IntegrityError as e:
                return Response(
                    {"detail": "Foreign key constraint failed", "error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = self.get_serializer(created_encuestas, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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

    @action(detail=False, methods=["post"], parser_classes=[JSONParser])
    def bulk_create(self, request, *args, **kwargs):
        """This method is used to create multiple Colegio objects.
        Args:
            request (_type_): _description_

        Returns:
            _type_: _description_

        """
        colegios = request.data.get("colegios", [])
        if not colegios:
            return Response(
                {"detail": "No colegios provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        created_colegios = []
        for colegio_data in colegios:
            cid = colegio_data.get("cid")
            nombre = colegio_data.get("nombre")
            comunidad_autonoma = colegio_data.get("comunidad_autonoma")
            telefono = colegio_data.get("telefono")
            email = colegio_data.get("email")
            pri_sid = colegio_data.get("pri_sid")
            sec_sid = colegio_data.get("sec_sid")
            pro_sid = colegio_data.get("pro_sid")
            if not all([cid, nombre, comunidad_autonoma]):
                return Response(
                    {"detail": "Missing parameters for one or more colegios"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Check SIDs exist in database, if not, run UpdateEncuesta
            pri_encuesta = update_encuesta_by_sid(pri_sid) if pri_sid else None
            sec_encuesta = update_encuesta_by_sid(sec_sid) if sec_sid else None
            pro_encuesta = update_encuesta_by_sid(pro_sid) if pro_sid else None

            try:
                colegio, created = Colegio.objects.update_or_create(
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
                created_colegios.append(colegio)
            except IntegrityError as e:
                return JsonResponse(
                    {
                        "detalle": "Foreign key constraint failed",
                        "error": str(e)
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except Exception as e:
                return JsonResponse(
                    {
                        "detalle": "Error al actualizar o crear el objeto Colegio", 
                        "error": str(e)
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = self.get_serializer(created_colegios, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@csrf_exempt
@require_POST
def UpdateEncuesta(request):
    """This method is used to update the number of responses of an Encuesta object.
        Sends a GET request with the url of the Encuesta object to LimeSurvey API and retrives the number of responses.
    Args:
        request (_type_): _description_

    Returns:
        _type_: _description_

    """
    logging.debug(f"UpdateEncuesta. request: {request.__dict__}")
    sid = request.POST.get("sid")
    usr = request.POST.get("usr")
    password = request.POST.get("pass")
    logging.debug(f"UpdateEncuesta. sid: {sid}")
    if not all([sid, usr, password]):
        return Response(
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
        # Aquí se puede actualizar la base de datos local utilizando data_externa
        # Por ejemplo, se podría actualizar o crear un objeto Survey:
        Encuesta.objects.update_or_create(
            sid=data_externa.get("Encuesta", {}).get("SID"),
            defaults={
                "titulo": data_externa.get("Encuesta", {}).get("Titulo encuesta"),
                "activa": data_externa.get("Encuesta", {}).get("Activa"),
                "url": data_externa.get("Encuesta", {}).get("Url"),
                "fecha_inicio": data_externa.get("Encuesta", {}).get("Fecha inicio"),
                "fecha_fin": data_externa.get("Encuesta", {}).get("Fecha fin"),
                "encuestas_cubiertas": data_externa.get("Encuesta", {}).get(
                    "Encuestas cubiertas"
                ),
                "encuestas_incompletas": data_externa.get("Encuesta", {}).get(
                    "Encuestas incompletas"
                ),
                "encuestas_totales": data_externa.get("Encuesta", {}).get(
                    "Encuestas totales"
                ),
                # Otros campos según sea necesario
            },
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

    return JsonResponse(data_externa)


@csrf_exempt
@require_POST
def UpdateEntradas(request):
    """This method is used to update the number of responses for all Encuesta objects stored in the database.
        Sends a POST request with the sid, usr, and pass parameters to the LimeSurvey API for each Encuesta object and retrieves the number of responses.
    Args:
        request (HttpRequest): The HTTP request containing the usr and pass parameters.

    Returns:
        JsonResponse: A JSON response containing the updated data or an error message.
    """
    usr = request.POST.get("usr")
    password = request.POST.get("pass")

    if not all([usr, password]):
        return Response(
            {"detail": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST
        )
    stored_sids = Encuesta.objects.values_list("sid", flat=True)
    payload_array = []
    for sid in stored_sids:
        payload = {"sid": sid, "usr": usr, "pass": password}
        payload_array.append(payload)

    try:
        data_externa_array = []
        # Se realiza la petición POST al servicio externo
        for payload in payload_array:
            response = requests.post(API_LIMESURVEY, data=payload, verify=False)
            response.raise_for_status()  # Lanza excepción en caso de error HTTP
            data_externa = response.json()  # Se decodifica la respuesta JSON
            data_externa_array.append(data_externa)

        # Aquí se puede actualizar la base de datos local utilizando data_externa
        # Por ejemplo, se podría actualizar o crear un objeto Survey:
        for data_externa in data_externa_array:
            Encuesta.objects.update_or_create(
                sid=data_externa.get("Encuesta", {}).get("SID"),
                defaults={
                    "titulo": data_externa.get("Encuesta", {}).get("Titulo encuesta"),
                    "activa": data_externa.get("Encuesta", {}).get("Activa"),
                    "url": data_externa.get("Encuesta", {}).get("Url"),
                    "fecha_inicio": data_externa.get("Encuesta", {}).get(
                        "Fecha inicio"
                    ),
                    "fecha_fin": data_externa.get("Encuesta", {}).get("Fecha fin"),
                    "encuestas_cubiertas": data_externa.get("Encuesta", {}).get(
                        "Encuestas cubiertas"
                    ),
                    "encuestas_incompletas": data_externa.get("Encuesta", {}).get(
                        "Encuestas incompletas"
                    ),
                    "encuestas_totales": data_externa.get("Encuesta", {}).get(
                        "Encuestas totales"
                    ),
                    # Otros campos según sea necesario
                },
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

    return JsonResponse(data_externa)

class DashboardViewSet(viewsets.ViewSet):
    """
    API endpoint that allows the dashboard to be viewed.
    """

    def list(self, request):
        """This method is used to list the data of the dashboard.
        Args:
            request (_type_): _description_

        Returns:
            _type_: _description_

        """
        # Get the number of Encuestas
        num_encuestas = Encuesta.objects.count()
        # Get the number of Colegios
        num_colegios = Colegio.objects.count()
        # Get the number of responses
        num_responses = Encuesta.objects.aggregate(
            total=Sum("encuestas_totales")
        )["total"]
        # Get the number of responses covered
        num_responses_covered = Encuesta.objects.aggregate(
            total=Sum("encuestas_cubiertas")
        )["total"]
        # Get the number of responses incomplete
        num_responses_incomplete = Encuesta.objects.aggregate(
            total=Sum("encuestas_incompletas")
        )["total"]
        # Get the number of responses not covered
        num_responses_not_covered = num_responses - num_responses_covered
        # Get the number of responses complete
        num_responses_complete = num_responses_covered - num_responses_incomplete
        # Get the number of responses per Colegio
        responses_per_colegio = Colegio.objects.annotate(
            num_responses=Sum("encuestas_totales")
        ).values("nombre", "num_responses")
        # Get the number of responses per Encuesta
        responses_per_encuesta = Encuesta.objects.values(
            "titulo", "encuestas_totales", "encuestas_cubiertas", "encuestas_incompletas"
        )
        # Get the number of responses per Comunidad Autonoma
        responses_per_comunidad_autonoma = Colegio.objects.values(
            "comunidad_autonoma"
        ).annotate(
            num_responses=Sum("encuestas_totales"),
            num_responses_covered=Sum("encuestas_cubiertas"),
            num_responses_incomplete=Sum("encuestas_incompletas"),
        )

        return Response(
            {
                "num_encuestas": num_encuestas,
                "num_colegios": num_colegios,
                "num_responses": num_responses,
                "num_responses_covered": num_responses_covered,
                "num_responses_incomplete": num_responses_incomplete,
                "num_responses_not_covered": num_responses_not_covered,
                "num_responses_complete": num_responses_complete,
                "responses_per_colegio": responses_per_colegio,
                "responses_per_encuesta": responses_per_encuesta,
                "responses_per_comunidad_autonoma": responses_per_comunidad_autonoma,
            }
        )
                

@csrf_exempt
@require_POST
def PostData(request):
    """_summary_
    This method post csv data to github repository.

    Args:
        request (_type_): _description_
    """

    # Get the data from the request
    data = request.POST.get("data")
    # Get the file name
    file_name = request.POST.get("file_name")
    # Get the repository name
    repository_name = request.POST.get("repository_name")
    # Get the branch name
    branch_name = request.POST.get("branch_name")
    # Get the access token
    access_token = request.POST.get("access_token")
    # Get the commit message
    commit_message = request.POST.get("commit_message")
    # Get the user name
    user_name = request.POST.get("user_name")
    # Get the email
    email = request.POST.get("email")

    # Create the url
    url = f"https://api.github.com/repos/{user_name}/{repository_name}/contents/{file_name}"
    # Create the headers
    headers = {
        "Authorization": f"token {access_token}",
        "Content-Type": "application/json",
    }
    # Create the data
    data = {
        "message": commit_message,
        "content": data,
        "branch": branch_name,
        "committer": {
            "name": user_name,
            "email": email,
        },
    }
    # Make the request
    response = requests.put(url, headers=headers, data=data)
    # Return the response
    return JsonResponse(response.json())
