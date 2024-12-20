from django.db import models
from enum import Enum

# Create your models here.
class TipoEncuesta(Enum):
    PRM = 'primaria'
    SEC = 'secundaria'
    PRO = 'profesorado'

class Colegio(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    municipio = models.CharField(max_length=100)
    provincia = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

class Encuesta(models.Model):
    url = models.URLField(unique=True)
    tipo_encuesta = models.CharField(max_length=20, choices=[(tag, tag.value) for tag in TipoEncuesta])
    num_respuestas = models.IntegerField()  # Numero de respuestas completadas
    colegio = models.ManyToManyField(Colegio, related_name='encuestas')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.url