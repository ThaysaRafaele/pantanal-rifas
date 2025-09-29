from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from rifa.models import Numero

class Command(BaseCommand):
    help = 'Libera números reservados há mais de 24 horas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas simula a operação sem fazer alterações',
        )

    def handle(self, *args, **options):
        agora = timezone.now()
        limite_expiracao = agora - timedelta(hours=24)
        
        # Encontrar números reservados há mais de 24 horas
        numeros_expirados = Numero.objects.filter(
            status='reservado',
            reservado_em__lt=limite_expiracao
        )
        
        count = numeros_expirados.count()
        
        if count > 0:
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING(f'[DRY RUN] {count} números seriam liberados.')
                )
                for numero in numeros_expirados[:5]:  # Mostrar apenas os primeiros 5
                    self.stdout.write(f'  - Número {numero.numero} da rifa "{numero.rifa.titulo}"')
                if count > 5:
                    self.stdout.write(f'  ... e mais {count - 5} números')
            else:
                # Liberar números expirados
                numeros_expirados.update(
                    status='livre',
                    reservado_em=None,
                    comprador_nome='',
                    comprador_email='',
                    comprador_telefone='',
                    comprador_cpf=''
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'Liberados {count} números com reserva expirada.')
                )
        else:
            self.stdout.write(
                self.style.WARNING('Nenhum número com reserva expirada encontrado.')
            )

        # Estatísticas atuais
        total_reservados = Numero.objects.filter(status='reservado').count()
        total_pagos = Numero.objects.filter(status='pago').count()
        total_livres = Numero.objects.filter(status='livre').count()
        
        self.stdout.write(f'Estado atual: {total_livres} livres, {total_reservados} reservados, {total_pagos} pagos')