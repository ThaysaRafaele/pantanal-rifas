from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    nome_social = models.CharField('Nome Social', max_length=150, blank=True)
    
    # CPF não obrigatório, mas único quando preenchido
    cpf = models.CharField('CPF', max_length=14, blank=True, null=True, unique=True)
    
    data_nascimento = models.CharField('Data de nascimento', max_length=10, blank=True)
    telefone = models.CharField('Telefone', max_length=20, blank=True)
    cep = models.CharField('CEP', max_length=9, blank=True)
    logradouro = models.CharField('Logradouro', max_length=100, blank=True)
    numero = models.CharField('Número', max_length=10, blank=True)
    bairro = models.CharField('Bairro', max_length=100, blank=True)
    complemento = models.CharField('Complemento', max_length=100, blank=True)
    uf = models.CharField('UF', max_length=2, blank=True)
    cidade = models.CharField('Cidade', max_length=100, blank=True)
    referencia = models.CharField('Ponto de referência', max_length=100, blank=True)

    def __str__(self):
        return f"Perfil de {self.user.username}"
    
    class Meta:
        verbose_name = 'Perfil de Usuário'
        verbose_name_plural = 'Perfis de Usuários'