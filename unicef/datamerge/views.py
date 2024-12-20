from django.shortcuts import render
from django.contrib.auth.models import Group, User
from rest_framework import permissions, viewsets, status

from unicef.datamerge.serializers import GroupSerializer, UserSerializer
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from openpyxl import load_workbook
from unicef.datamerge.models import Colegio, Encuesta

API_LIMESURVEY = 'https://unicef.ccii.es/index.php?r=admin/remotecontrol'

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    
class UploadXLSXView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        # Verificamos que se haya enviado un archivo
        file_obj = request.FILES.get('file', None)
        if file_obj is None:
            return Response({"detail": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            wb = load_workbook(file_obj)
            ws = wb.active  # Tomamos la primera hoja del libro

            # Suponiendo que la primera fila son los encabezados: Name, Email, Age
            # Empezamos a leer desde la fila 2
            created_count = 0
            for row in ws.iter_rows(min_row=2, values_only=True):
                nombre, municipio, provincia, url = row
                # Puedes agregar validaciones aquí si lo requieres
                Colegio.objects.create(nombre=nombre, municipio=municipio, provincia=provincia)
                Encuesta.objects.create(url=url, num_respuestas=None)
                created_count += 1

            return Response({"detail": f"{created_count} records created."}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class UpdateEncuesta(APIView):
    """ This method is used to update the number of responses of an Encuesta object.
        Sends a GET request with the url of the Encuesta object to LimeSurvey API and retrives the number of responses.
    Args:
        APIView (_type_): _description_
    """
    def get_num_respuestas(url):
        # Get the number of responses from the API_LIMESURVEY
        
        
    def get(self, request, url, format=None):
        # Get the Encuesta object
        encuesta = Encuesta.objects.get(url=url)
        # Get the number of responses from the API
        num_respuestas = get_num_respuestas(url)
        # Update the Encuesta object
        encuesta.num_respuestas = num_respuestas
        encuesta.save()
        return Response({"detail": f"Encuesta {url} updated with {num_respuestas} responses."}, status=status.HTTP_200_OK)