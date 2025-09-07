from django.db import migrations

def criar_rifa_inicial(apps, schema_editor):
    Rifa = apps.get_model('rifa', 'Rifa')
    Numero = apps.get_model('rifa', 'Numero')
    
    # Verificar se já existe
    if Rifa.objects.filter(titulo="CONCORRA A ESTA INCRIVEL XRE 300").exists():
        return
    
    rifa = Rifa.objects.create(
        titulo="CONCORRA A ESTA INCRIVEL XRE 300",
        descricao="Concorra a esta incrível XRE 300",
        preco=1.99,
        quantidade_numeros=1000,
        encerrada=False
    )
    
    # Criar números em lotes para performance
    numeros = []
    for numero in range(1, 1001):
        numeros.append(Numero(
            rifa=rifa,
            numero=numero,
            status='livre'
        ))
    
    Numero.objects.bulk_create(numeros, batch_size=100)

def reverter_rifa_inicial(apps, schema_editor):
    Rifa = apps.get_model('rifa', 'Rifa')
    Rifa.objects.filter(titulo="CONCORRA A ESTA INCRIVEL XRE 300").delete()

class Migration(migrations.Migration):
    dependencies = [
        ('rifa', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(criar_rifa_inicial, reverter_rifa_inicial),
    ]