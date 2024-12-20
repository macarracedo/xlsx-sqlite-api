from django.contrib.auth.models import Group, User
from unicef.datamerge.models import Colegio, Encuesta
from rest_framework import serializers


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['url', 'username', 'email', 'groups']


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']
        
class ColegioSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Colegio
        fields = ['nombre', 'municipio', 'provincia', 'created', 'updated']

class EncuestaSerializer(serializers.HyperlinkedModelSerializer):
    colegio = ColegioSerializer(many=True, read_only=True)
    class Meta:
        model = Encuesta
        fields = ['nombre', 'url', 'num_respuestas', 'colegio', 'created', 'updated']