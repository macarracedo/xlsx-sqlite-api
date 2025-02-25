from django.contrib.auth.models import Group, User
from unicef.datamerge.models import Encuesta, Colegio, EncuestaResult
from rest_framework import serializers


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "username", "email", "groups"]


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ["url", "name"]


class EncuestaResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = EncuestaResult
        fields = [
            "date",
            "encuestas_cubiertas",
            "encuestas_incompletas",
            "encuestas_totales",
        ]


class EncuestaSerializer(serializers.HyperlinkedModelSerializer):
    results = EncuestaResultSerializer(many=True, read_only=True)

    class Meta:
        model = Encuesta
        fields = [
            "sid",
            "titulo",
            "fecha_inicio",
            "fecha_fin",
            "activa",
            "url",
            "results",
        ]


class ColegioSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Colegio
        fields = [
            "cid",
            "nombre",
            "comunidad_autonoma",
            "telefono",
            "email",
            "pri_sid",
            "sec_sid",
            "pro_sid",
        ]
class FileUploadSerializer(serializers.Serializer):
    cocina_csv = serializers.FileField()