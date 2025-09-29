from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('rifa', '0014_merge_20250901_1930'),
    ]

    operations = [
        migrations.AddField(
            model_name='numero',
            name='reservado_em',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Data da reserva'),
        ),
    ]