from django.contrib.auth.models import Group, User
from unicef.datamerge.models import Encuesta
from rest_framework import serializers


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "username", "email", "groups"]


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ["url", "name"]


class EncuestaSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Encuesta
        fields = [
            "sid",
            "titulo",
            "fecha_inicio",
            "fecha_fin",
            "activa",
            "url",
            "encuestas_cubiertas",
            "encuestas_incompletas",
            "encuestas_totales",
        ]
