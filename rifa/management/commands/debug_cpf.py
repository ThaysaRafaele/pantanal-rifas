from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rifa.models_profile import UserProfile
import re

class Command(BaseCommand):
    help = 'Diagnostica problemas com CPF específico'

    def add_arguments(self, parser):
        parser.add_argument('cpf', type=str, help='CPF para diagnosticar')

    def handle(self, *args, **options):
        cpf_input = options['cpf']
        digits = re.sub(r'\D', '', cpf_input)
        
        self.stdout.write(f"\n=== DIAGNÓSTICO CPF: {cpf_input} ===")
        self.stdout.write(f"Dígitos extraídos: '{digits}' (len: {len(digits)})")
        
        if len(digits) != 11:
            self.stdout.write(self.style.ERROR("CPF deve ter 11 dígitos"))
            return
        
        # Formatos possíveis
        formatted = f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
        self.stdout.write(f"CPF formatado: '{formatted}'")
        
        # Busca direta
        profiles_direct = UserProfile.objects.filter(cpf__in=[digits, formatted])
        self.stdout.write(f"\nBusca direta por '{digits}' ou '{formatted}':")
        self.stdout.write(f"Encontrados: {profiles_direct.count()}")
        
        # Lista todos os perfis e normaliza
        self.stdout.write(f"\n=== VERIFICAÇÃO COMPLETA ===")
        found_match = False
        
        for profile in UserProfile.objects.all():
            cpf_db = profile.cpf or ''
            cpf_db_digits = re.sub(r'\D', '', cpf_db)
            
            if cpf_db_digits == digits:
                found_match = True
                self.stdout.write(self.style.SUCCESS(
                    f"✓ MATCH! User: {profile.user.username} (ID: {profile.user.id})"
                ))
                self.stdout.write(f"  CPF no banco: '{cpf_db}'")
                self.stdout.write(f"  Nome: {profile.user.first_name}")
                self.stdout.write(f"  Email: {profile.user.email}")
                self.stdout.write(f"  Telefone: {getattr(profile, 'telefone', 'N/A')}")
                
                # Teste de login
                self.stdout.write(f"\n=== TESTE DE LOGIN ===")
                user = profile.user
                if user.check_password('02052125@'):
                    self.stdout.write(self.style.SUCCESS("✓ Senha correta"))
                else:
                    self.stdout.write(self.style.ERROR("❌ Senha incorreta"))
                
                self.stdout.write(f"User ativo: {user.is_active}")
                break
        
        if not found_match:
            self.stdout.write(self.style.ERROR("❌ Nenhum perfil encontrado com este CPF"))
        
        # Busca por username que seja o CPF
        user_by_username = User.objects.filter(username=digits).first()
        if user_by_username:
            self.stdout.write(f"\n✓ Usuário com username='{digits}': {user_by_username.username}")
            try:
                profile = user_by_username.profile
                self.stdout.write(f"  Perfil CPF: '{profile.cpf}'")
            except:
                self.stdout.write("  ❌ Sem perfil associado")
        else:
            self.stdout.write(f"\n❌ Nenhum usuário com username='{digits}'")