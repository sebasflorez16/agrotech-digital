from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("agronomic_alerts", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="alertaoperativa",
            name="indice_afectado",
            field=models.CharField(
                choices=[
                    ("ndvi", "NDVI"),
                    ("ndmi", "NDMI"),
                    ("savi", "SAVI"),
                    ("evi", "EVI"),
                    ("ndre", "NDRE"),
                ],
                help_text="Índice satelital cuyo valor disparó la alerta.",
                max_length=10,
            ),
        ),
    ]
