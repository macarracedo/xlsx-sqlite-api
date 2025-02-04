from django.db import models


class Colegio(models.Model):
    cid = models.CharField(max_length=30) # L1A001 - Primaria 
    nombre = models.CharField(max_length=100)
    comunidad_autonoma = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.cid

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
    related_encuestas = models.ManyToManyField('self', blank=True)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='encuestas', default=0)

    def __str__(self):
        return self.url
