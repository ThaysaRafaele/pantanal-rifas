from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rifa.models_profile import UserProfile

class Command(BaseCommand):
    help = 'Verifica e cria perfis faltantes'

    def handle(self, *args, **options):
        usuarios_sem_perfil = 0
        perfis_criados = 0
        
        for user in User.objects.all():
            try:
                user.profile
            except UserProfile.DoesNotExist:
                usuarios_sem_perfil += 1
                # Criar perfil vazio
                UserProfile.objects.create(user=user, cpf='')
                perfis_criados += 1
                self.stdout.write(
                    self.style.WARNING(f'Perfil criado para: {user.username}')
                )
        
        if usuarios_sem_perfil == 0:
            self.stdout.write(self.style.SUCCESS('✅ Todos os usuários têm perfis!'))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✅ {perfis_criados} perfis criados')
            )