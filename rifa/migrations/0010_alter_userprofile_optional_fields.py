from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rifa', '0009_pedido'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='data_nascimento',
            field=models.CharField(blank=True, max_length=10, verbose_name='Data de nascimento'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='telefone',
            field=models.CharField(blank=True, max_length=20, verbose_name='Telefone'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='cep',
            field=models.CharField(blank=True, max_length=9, verbose_name='CEP'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='logradouro',
            field=models.CharField(blank=True, max_length=100, verbose_name='Logradouro'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='numero',
            field=models.CharField(blank=True, max_length=10, verbose_name='Número'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='bairro',
            field=models.CharField(blank=True, max_length=100, verbose_name='Bairro'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='uf',
            field=models.CharField(blank=True, max_length=2, verbose_name='UF'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='cidade',
            field=models.CharField(blank=True, max_length=100, verbose_name='Cidade'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='referencia',
            field=models.CharField(blank=True, max_length=100, verbose_name='Ponto de referência'),
        ),
    ]
