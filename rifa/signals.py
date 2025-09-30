from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models_profile import UserProfile

@receiver(post_save, sender=User)
def criar_perfil_usuario(sender, instance, created, **kwargs):
    """
    Cria automaticamente um perfil quando um usuário é criado
    """
    if created:
        try:
            UserProfile.objects.get_or_create(
                user=instance,
                defaults={
                    'cpf': '',
                    'nome_social': '',
                    'data_nascimento': '',
                    'telefone': '',
                    'cep': '',
                    'logradouro': '',
                    'numero': '',
                    'bairro': '',
                    'uf': '',
                    'cidade': '',
                    'complemento': '',
                    'referencia': ''
                }
            )
        except Exception as e:
            print(f"Erro ao criar perfil para {instance.username}: {e}")