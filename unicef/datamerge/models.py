from django.db import models


class Encuesta(models.Model):
    sid = models.CharField(max_length=20)
    titulo = models.CharField(max_length=100)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    activa = models.CharField(max_length=1)
    url = models.URLField(max_length=200)
    encuestas_cubiertas = models.IntegerField()
    encuestas_incompletas = models.IntegerField()
    encuestas_totales = models.IntegerField()

    def __str__(self):
        return self.url
