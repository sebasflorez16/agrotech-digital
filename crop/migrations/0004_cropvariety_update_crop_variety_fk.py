import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crop", "0003_add_crop_catalog_phenological_stage_crop_cycle"),
        ("inventario", "0001_initial"),
    ]

    operations = [
        # 1. Crear el nuevo modelo CropVariety
        migrations.CreateModel(
            name="CropVariety",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, verbose_name="Nombre de la variedad")),
                ("cycle_days", models.IntegerField(blank=True, null=True, verbose_name="Días de ciclo (aprox.)")),
                ("description", models.TextField(blank=True, null=True, verbose_name="Descripción")),
                (
                    "crop_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="varieties",
                        to="crop.croptype",
                        verbose_name="Tipo de cultivo",
                    ),
                ),
            ],
            options={
                "verbose_name": "Variedad de cultivo",
                "verbose_name_plural": "Variedades de cultivo",
                "ordering": ["crop_type", "name"],
                "unique_together": {("name", "crop_type")},
            },
        ),
        # 2. Eliminar el FK antiguo (Supply → inventario)
        migrations.RemoveField(
            model_name="crop",
            name="variety",
        ),
        # 3. Agregar el nuevo FK (CropVariety)
        migrations.AddField(
            model_name="crop",
            name="variety",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="crop.cropvariety",
                verbose_name="Variedad",
            ),
        ),
    ]
