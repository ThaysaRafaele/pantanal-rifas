from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rifa', '0010_alter_userprofile_optional_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='PremioBilhete',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero_premiado', models.PositiveIntegerField(help_text='Número específico que concede o prêmio ao comprador.')),
                ('valor_premio', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10)),
                ('descricao', models.CharField(blank=True, max_length=120)),
                ('ativo', models.BooleanField(default=True, help_text='Se desativado, não será mais concedido.')),
                ('ganho_em', models.DateTimeField(blank=True, null=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('ganho_por', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name='premios_ganhos', to='auth.user')),
                ('pedido', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name='premios_vinculados', to='rifa.pedido')),
                ('rifa', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='premios', to='rifa.rifa')),
            ],
            options={
                'ordering': ['rifa', 'numero_premiado'],
                'unique_together': {('rifa', 'numero_premiado')},
            },
        ),
    ]
