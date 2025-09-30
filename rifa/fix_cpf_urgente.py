#!/usr/bin/env python
"""
Script emergencial para recuperar CPFs perdidos
Executar: python manage.py shell < fix_cpf_urgente.py
"""

import os
import django
import re

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rifa.settings')
django.setup()

from django.contrib.auth.models import User
from rifa.models_profile import UserProfile
from rifa.models import Numero
from django.db import transaction

def normalizar_cpf(cpf):
    """Remove formatação"""
    if not cpf:
        return None
    digits = re.sub(r'\D', '', cpf)
    return digits if len(digits) == 11 else None

def formatar_cpf(cpf_digits):
    """Adiciona formatação"""
    if len(cpf_digits) == 11:
        return f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"
    return cpf_digits

def recuperar_cpfs():
    print("🚨 INICIANDO RECUPERAÇÃO EMERGENCIAL DE CPFs...\n")
    
    # Mapear CPFs das compras (fonte verdadeira de dados)
    print("📊 Mapeando CPFs das compras...")
    mapeamento_email = {}
    mapeamento_nome = {}
    
    for numero in Numero.objects.exclude(comprador_cpf__in=['', None]):
        cpf = normalizar_cpf(numero.comprador_cpf)
        if not cpf:
            continue
            
        email = (numero.comprador_email or '').strip().lower()
        nome = (numero.comprador_nome or '').strip()
        
        if email:
            mapeamento_email[email] = cpf
        if nome:
            mapeamento_nome[nome] = cpf
    
    print(f"✅ Encontrados {len(mapeamento_email)} CPFs únicos por email")
    print(f"✅ Encontrados {len(mapeamento_nome)} CPFs únicos por nome\n")
    
    # Processar usuários
    corrigidos = 0
    criados = 0
    erros = 0
    
    for user in User.objects.all():
        try:
            # Tentar buscar CPF
            cpf_encontrado = None
            
            # 1. Por email
            if user.email:
                cpf_encontrado = mapeamento_email.get(user.email.lower())
            
            # 2. Por nome
            if not cpf_encontrado and user.first_name:
                cpf_encontrado = mapeamento_nome.get(user.first_name)
            
            if not cpf_encontrado:
                continue
            
            cpf_formatado = formatar_cpf(cpf_encontrado)
            
            with transaction.atomic():
                # Verificar se perfil existe
                try:
                    profile = user.profile
                    
                    # Só atualizar se estiver vazio
                    if not normalizar_cpf(profile.cpf):
                        profile.cpf = cpf_formatado
                        profile.save()
                        print(f"✅ {user.username}: CPF atualizado para {cpf_formatado}")
                        corrigidos += 1
                        
                except UserProfile.DoesNotExist:
                    # Criar novo perfil
                    UserProfile.objects.create(
                        user=user,
                        cpf=cpf_formatado,
                        nome_social='',
                        data_nascimento='',
                        telefone='',
                        cep='',
                        logradouro='',
                        numero='',
                        bairro='',
                        uf='',
                        cidade=''
                    )
                    print(f"✅ {user.username}: Perfil criado com CPF {cpf_formatado}")
                    criados += 1
                    
        except Exception as e:
            print(f"❌ {user.username}: Erro - {str(e)}")
            erros += 1
    
    print(f"\n📊 RESULTADO:")
    print(f"   Perfis atualizados: {corrigidos}")
    print(f"   Perfis criados: {criados}")
    print(f"   Erros: {erros}")
    
    # Criar perfis vazios para usuários restantes
    print(f"\n🔧 Criando perfis vazios para usuários sem perfil...")
    criados_vazios = 0
    
    for user in User.objects.all():
        try:
            user.profile
        except UserProfile.DoesNotExist:
            try:
                # CPF temporário único baseado no ID do usuário
                cpf_temp = f"{user.id:011d}"  # 11 dígitos
                cpf_formatado = formatar_cpf(cpf_temp)
                
                UserProfile.objects.create(
                    user=user,
                    cpf=cpf_formatado,
                    nome_social='',
                    data_nascimento='',
                    telefone='',
                    cep='',
                    logradouro='',
                    numero='',
                    bairro='',
                    uf='',
                    cidade=''
                )
                print(f"⚠️  {user.username}: Perfil criado com CPF temporário")
                criados_vazios += 1
            except Exception as e:
                print(f"❌ {user.username}: Erro ao criar perfil vazio - {str(e)}")
    
    print(f"\n✅ CONCLUÍDO!")
    print(f"   Perfis vazios criados: {criados_vazios}")
    
    return {
        'corrigidos': corrigidos,
        'criados': criados,
        'erros': erros,
        'vazios': criados_vazios
    }

if __name__ == '__main__':
    resultado = recuperar_cpfs()
else:
    resultado = recuperar_cpfs()