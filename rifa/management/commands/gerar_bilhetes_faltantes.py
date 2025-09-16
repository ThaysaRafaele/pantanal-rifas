import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rifa.settings')
django.setup()

from django.core.management.base import BaseCommand
from django.db import transaction
from rifa.models import Rifa, Numero

class Command(BaseCommand):
    help = 'Gera bilhetes faltantes para atingir o limite de quantidade_numeros da rifa'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rifa-id',
            type=int,
            help='ID específico da rifa para gerar bilhetes',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Executa sem fazer alterações, apenas mostra o que seria feito',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Quantidade de bilhetes a criar por vez (default: 1000)',
        )

    def handle(self, *args, **options):
        rifa_id = options.get('rifa_id')
        dry_run = options['dry_run']
        batch_size = options['batch_size']

        if rifa_id:
            rifas = Rifa.objects.filter(id=rifa_id)
        else:
            rifas = Rifa.objects.all()

        if not rifas.exists():
            self.stdout.write(
                self.style.ERROR(f'Nenhuma rifa encontrada com ID {rifa_id}' if rifa_id else 'Nenhuma rifa encontrada')
            )
            return

        for rifa in rifas:
            self.processar_rifa(rifa, dry_run, batch_size)

    def processar_rifa(self, rifa, dry_run, batch_size):
        self.stdout.write(f'\n=== PROCESSANDO RIFA: {rifa.titulo} (ID: {rifa.id}) ===')
        self.stdout.write(f'Limite configurado: {rifa.quantidade_numeros:,} bilhetes')
        
        # Verificar quantos bilhetes já existem
        numeros_existentes = set(Numero.objects.filter(rifa=rifa).values_list('numero', flat=True))
        total_existentes = len(numeros_existentes)
        
        self.stdout.write(f'Bilhetes já existentes: {total_existentes:,}')
        
        # Calcular quantos faltam
        limite = rifa.quantidade_numeros
        faltantes = limite - total_existentes
        
        if faltantes <= 0:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Rifa já possui {total_existentes:,} bilhetes (limite: {limite:,})')
            )
            return
        
        self.stdout.write(f'Bilhetes faltantes: {faltantes:,}')
        
        # Determinar quais números criar (1 até limite, excluindo os existentes)
        numeros_para_criar = []
        for numero in range(1, limite + 1):
            if numero not in numeros_existentes:
                numeros_para_criar.append(numero)
        
        self.stdout.write(f'Números a serem criados: {len(numeros_para_criar):,}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'[DRY RUN] Seriam criados {len(numeros_para_criar):,} bilhetes')
            )
            if numeros_para_criar:
                self.stdout.write(f'Exemplos: {numeros_para_criar[:10]}...')
            return
        
        # Criar bilhetes em lotes
        total_criados = 0
        for i in range(0, len(numeros_para_criar), batch_size):
            lote = numeros_para_criar[i:i + batch_size]
            
            try:
                with transaction.atomic():
                    bilhetes_para_criar = [
                        Numero(
                            rifa=rifa,
                            numero=numero,
                            status='livre'
                        ) for numero in lote
                    ]
                    
                    Numero.objects.bulk_create(bilhetes_para_criar, ignore_conflicts=True)
                    total_criados += len(lote)
                    
                    self.stdout.write(f'✓ Lote {i//batch_size + 1}: {len(lote):,} bilhetes criados (Total: {total_criados:,})')
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Erro no lote {i//batch_size + 1}: {e}')
                )
                continue
        
        # Verificação final
        total_final = Numero.objects.filter(rifa=rifa).count()
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ CONCLUÍDO: Rifa "{rifa.titulo}" agora possui {total_final:,} bilhetes'
            )
        )
        
        # Estatísticas dos status
        stats = Numero.objects.filter(rifa=rifa).values('status').annotate(
            total=django.db.models.Count('id')
        )
        
        self.stdout.write('\n📊 ESTATÍSTICAS:')
        for stat in stats:
            self.stdout.write(f"  - {stat['status'].title()}: {stat['total']:,}")