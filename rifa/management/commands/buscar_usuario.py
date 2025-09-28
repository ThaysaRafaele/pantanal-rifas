from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rifa.models_profile import UserProfile
import re

class Command(BaseCommand):
    help = 'Busca usuário por diferentes critérios'

    def add_arguments(self, parser):
        parser.add_argument('--senha', type=str, help='Buscar por senha específica')
        parser.add_argument('--listar-todos', action='store_true', help='Listar todos os usuários')

    def handle(self, *args, **options):
        senha = options.get('senha')
        listar_todos = options.get('listar_todos')
        
        if senha:
            self.stdout.write(f"\n=== BUSCANDO USUÁRIOS COM SENHA: {senha} ===")
            encontrados = 0
            for user in User.objects.all():
                if user.check_password(senha):
                    encontrados += 1
                    self.stdout.write(self.style.SUCCESS(f"✓ ENCONTRADO: {user.username}"))
                    self.stdout.write(f"  ID: {user.id}")
                    self.stdout.write(f"  Email: {user.email}")
                    self.stdout.write(f"  Nome: {user.first_name}")
                    self.stdout.write(f"  Ativo: {user.is_active}")
                    
                    try:
                        profile = user.profile
                        self.stdout.write(f"  CPF: {profile.cpf}")
                        self.stdout.write(f"  Telefone: {getattr(profile, 'telefone', 'N/A')}")
                    except:
                        self.stdout.write("  ❌ Sem perfil")
                    self.stdout.write("")
            
            if encontrados == 0:
                self.stdout.write(self.style.ERROR("❌ Nenhum usuário encontrado com essa senha"))
        
        if listar_todos:
            self.stdout.write(f"\n=== TODOS OS USUÁRIOS ===")
            for user in User.objects.all():
                cpf = "N/A"
                try:
                    cpf = user.profile.cpf
                except:
                    pass
                
                self.stdout.write(f"User: {user.username} | Email: {user.email} | CPF: {cpf}")
            
            self.stdout.write(f"\nTotal: {User.objects.count()} usuários")
            
            # Estatísticas de perfis
            total_profiles = UserProfile.objects.count()
            users_sem_profile = User.objects.filter(profile__isnull=True).count()
            
            self.stdout.write(f"Perfis: {total_profiles}")
            self.stdout.write(f"Usuários sem perfil: {users_sem_profile}")
            
            if users_sem_profile > 0:
                self.stdout.write("\nUsuários sem perfil:")
                for user in User.objects.filter(profile__isnull=True):
                    self.stdout.write(f"  - {user.username} (ID: {user.id})")