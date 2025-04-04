from django.db import models
from django.utils import timezone

class Colegio(models.Model):
    cid = models.CharField(max_length=30)  # L1A001 - Primaria
    nombre = models.CharField(max_length=100)
    comunidad_autonoma = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(max_length=100, null=True, blank=True)
    pri_sid = models.ForeignKey('Encuesta', on_delete=models.SET_NULL, null=True, blank=True, related_name='primary_colegios')
    sec_sid = models.ForeignKey('Encuesta', on_delete=models.SET_NULL, null=True, blank=True, related_name='secondary_colegios')
    pro_sid = models.ForeignKey('Encuesta', on_delete=models.SET_NULL, null=True, blank=True, related_name='professional_colegios')

    def __str__(self):
        return self.cid


class Encuesta(models.Model):
    sid = models.CharField(max_length=20)
    titulo = models.CharField(max_length=100)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    activa = models.CharField(max_length=1)
    url = models.URLField(max_length=200)
    related_encuestas = models.ManyToManyField('self', blank=True)

    def __str__(self):
        return f"{self.titulo} ({self.sid})"

class EncuestaResult(models.Model):
    encuesta = models.ForeignKey(Encuesta, on_delete=models.CASCADE, related_name='results')
    date = models.DateTimeField(default=timezone.now)
    encuestas_cubiertas = models.IntegerField()
    encuestas_incompletas = models.IntegerField()
    encuestas_totales = models.IntegerField()

    class Meta:
        unique_together = ('encuesta', 'date')

    def __str__(self):
        return f"{self.encuesta.sid} - {self.date} [c({self.encuestas_cubiertas}) i({self.encuestas_incompletas}) t({self.encuestas_totales})]"
