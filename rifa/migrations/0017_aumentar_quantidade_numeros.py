from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('rifa', '0016_seed_rifa_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rifa',
            name='quantidade_numeros',
            field=models.PositiveIntegerField(default=100000, help_text='Quantidade total de números disponíveis para esta rifa.'),
        ),
    ]