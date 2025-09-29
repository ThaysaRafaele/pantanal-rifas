from django.core.management.base import BaseCommand
from rifa.models_profile import UserProfile
import re

class Command(BaseCommand):
    help = 'Corrige e padroniza todos os CPFs no banco'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', 
            action='store_true',
            help='Apenas mostra o que seria alterado sem salvar'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write("\n=== CORREÇÃO DE CPFs ===")
        if dry_run:
            self.stdout.write(self.style.WARNING("MODO DRY-RUN: Nenhuma alteração será salva"))
        
        profiles = UserProfile.objects.all()
        corrected = 0
        
        for profile in profiles:
            cpf_original = profile.cpf or ''
            if not cpf_original:
                continue
                
            # Extrai apenas dígitos
            digits = re.sub(r'\D', '', cpf_original)
            
            if len(digits) == 11:
                # Formato padrão: 000.000.000-00
                cpf_correto = f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
                
                if cpf_original != cpf_correto:
                    self.stdout.write(f"User {profile.user.username}:")
                    self.stdout.write(f"  Antes: '{cpf_original}'")
                    self.stdout.write(f"  Depois: '{cpf_correto}'")
                    
                    if not dry_run:
                        profile.cpf = cpf_correto
                        profile.save(update_fields=['cpf'])
                    
                    corrected += 1
            elif len(digits) > 0:
                self.stdout.write(self.style.ERROR(
                    f"CPF inválido para {profile.user.username}: '{cpf_original}' ({len(digits)} dígitos)"
                ))
        
        if corrected > 0:
            action = "seriam corrigidos" if dry_run else "foram corrigidos"
            self.stdout.write(self.style.SUCCESS(f"\n{corrected} CPFs {action}"))
        else:
            self.stdout.write(self.style.SUCCESS("\nTodos os CPFs já estão no formato correto"))

# Para executar:
# python manage.py fix_cpfs --dry-run  (apenas visualizar)
# python manage.py fix_cpfs             (aplicar correções)