from django.db import migrations, models
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('rifa', '0008_rifa_ganhador_cpf_rifa_quantidade_numeros_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Pedido',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantidade', models.PositiveIntegerField()),
                ('valor_unitario', models.DecimalField(decimal_places=2, max_digits=10)),
                ('valor_total', models.DecimalField(decimal_places=2, max_digits=10)),
                ('numeros_reservados', models.TextField(blank=True, help_text='Lista de números reservados separados por vírgula.')),
                ('cpf', models.CharField(max_length=14)),
                ('nome', models.CharField(max_length=150)),
                ('telefone', models.CharField(blank=True, max_length=20)),
                ('pix_codigo', models.TextField(blank=True)),
                ('pix_txid', models.CharField(blank=True, max_length=35)),
                ('status', models.CharField(choices=[('pendente', 'Pendente'), ('pago', 'Pago'), ('expirado', 'Expirado'), ('cancelado', 'Cancelado')], default='pendente', max_length=10)),
                ('expires_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('rifa', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='pedidos', to='rifa.rifa')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
