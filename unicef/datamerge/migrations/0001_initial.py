# Generated by Django 5.1.4 on 2025-02-03 11:35

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Encuesta",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("sid", models.CharField(max_length=20)),
                ("titulo_encuesta", models.CharField(max_length=100)),
                ("fecha_inicio", models.DateTimeField(blank=True, null=True)),
                ("fecha_fin", models.DateTimeField(blank=True, null=True)),
                ("activa", models.CharField(max_length=1)),
                ("url", models.URLField()),
                ("encuestas_cubiertas", models.IntegerField()),
                ("encuestas_incompletas", models.IntegerField()),
                ("encuestas_totales", models.IntegerField()),
            ],
        ),
    ]
