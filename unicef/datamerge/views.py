import requests
from django.shortcuts import render
from django.contrib.auth.models import Group, User
from rest_framework import permissions, viewsets, status
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
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

API_LIMESURVEY = "https://unicef.ccii.es//cciiAdmin/consultaDatosEncuesta.php"


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
        if not all([cid, nombre, comunidad_autonoma, telefono, email]):
            return Response(
                {"detail": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST
            )
        payload = {"nombre": nombre, "comunidad_autonoma": comunidad_autonoma, "telefono": telefono, "email": email}
        try:
            # Se realiza la petición POST al servicio externo
            Colegio.objects.update_or_create(
                cid=cid,
                defaults={
                    "nombre": nombre,
                    "comunidad_autonoma": comunidad_autonoma,
                    "telefono": telefono,
                    "email": email,
                },
            )
        except requests.RequestException as ex:
            return JsonResponse(
                {"error": "Error al actualizar o crear el objeto Colegio", "detalle": str(ex)},
                status=500,
            )
        return JsonResponse(payload)

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
    sid = request.POST.get("sid")
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