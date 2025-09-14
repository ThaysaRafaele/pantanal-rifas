#!/usr/bin/env python3
"""
Script para migração de dados do ambiente anterior (pantanal-rifas.onrender.com)
para o novo ambiente (pantanaldasortems.com)

ATENÇÃO: Execute este script no ambiente de DESTINO (novo ambiente)
"""

import os
import sys
import django
import json
import requests
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rifa.settings')
django.setup()

from django.contrib.auth.models import User
from django.db import transaction
from rifa.models import Rifa, Numero, NumeroRifa, PremioBilhete
from rifa.models_profile import UserProfile

class MigracaoDados:
    def __init__(self):
        self.url_origem = "https://pantanal-rifas.onrender.com"
        self.stats = {
            'usuarios_migrados': 0,
            'bilhetes_migrados': 0,
            'rifas_migradas': 0,
            'erros': []
        }
        
    def log(self, mensagem):
        """Log com timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {mensagem}")
        
    def fazer_backup_atual(self):
        """Faz backup do estado atual antes da migração"""
        self.log("📦 Fazendo backup do estado atual...")
        
        backup_data = {
            'usuarios': [],
            'rifas': [],
            'bilhetes': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Backup usuários
        for user in User.objects.all():
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'date_joined': user.date_joined.isoformat() if user.date_joined else None
            }
            
            # Adicionar perfil se existir
            if hasattr(user, 'profile'):
                profile = user.profile
                user_data['profile'] = {
                    'cpf': profile.cpf,
                    'telefone': profile.telefone,
                    'nome_social': profile.nome_social,
                    'data_nascimento': profile.data_nascimento,
                    'cep': profile.cep,
                    'logradouro': profile.logradouro,
                    'numero': profile.numero,
                    'bairro': profile.bairro,
                    'uf': profile.uf,
                    'cidade': profile.cidade
                }
            
            backup_data['usuarios'].append(user_data)
        
        # Backup rifas
        for rifa in Rifa.objects.all():
            backup_data['rifas'].append({
                'id': rifa.id,
                'titulo': rifa.titulo,
                'descricao': rifa.descricao,
                'preco': float(rifa.preco),
                'encerrada': rifa.encerrada,
                'ganhador_nome': rifa.ganhador_nome,
                'ganhador_numero': rifa.ganhador_numero
            })
        
        # Backup bilhetes
        for numero in Numero.objects.all():
            backup_data['bilhetes'].append({
                'id': numero.id,
                'numero': numero.numero,
                'rifa_id': numero.rifa.id,
                'status': numero.status,
                'comprador_nome': numero.comprador_nome,
                'comprador_email': numero.comprador_email,
                'comprador_telefone': numero.comprador_telefone,
                'comprador_cpf': getattr(numero, 'comprador_cpf', '')
            })
        
        # Salvar backup
        with open(f'backup_pre_migracao_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        self.log(f"✅ Backup salvo: {len(backup_data['usuarios'])} usuários, {len(backup_data['rifas'])} rifas, {len(backup_data['bilhetes'])} bilhetes")
        
    def buscar_dados_origem(self):
        """Busca dados do ambiente anterior via API"""
        self.log("🔍 Buscando dados do ambiente anterior...")
        
        try:
            # Tentar buscar via API de exportação (se existir)
            response = requests.get(f"{self.url_origem}/api/exportar-dados/", timeout=30)
            
            if response.status_code == 200:
                dados = response.json()
                self.log(f"✅ Dados obtidos via API: {len(dados.get('users', []))} usuários, {len(dados.get('rifas', []))} rifas")
                return dados
            else:
                self.log(f"❌ API não disponível (status {response.status_code})")
                
        except Exception as e:
            self.log(f"❌ Erro ao acessar API: {e}")
        
        # Se não conseguir via API, usar dados do arquivo local_backup.json
        self.log("📂 Tentando carregar dados do arquivo local_backup.json...")
        
        try:
            with open('local_backup.json', 'r', encoding='utf-8') as f:
                dados = json.load(f)
                self.log(f"✅ Dados carregados do arquivo: {len(dados.get('users', []))} usuários")
                return dados
        except FileNotFoundError:
            self.log("❌ Arquivo local_backup.json não encontrado")
            return None
        except Exception as e:
            self.log(f"❌ Erro ao carregar arquivo: {e}")
            return None
    
    def migrar_usuarios(self, usuarios_data):
        """Migra usuários do ambiente anterior"""
        self.log("👥 Iniciando migração de usuários...")
        
        for user_data in usuarios_data:
            try:
                username = user_data.get('username', '')
                email = user_data.get('email', '')
                
                if not username:
                    continue
                
                # Verificar se usuário já existe
                if User.objects.filter(username=username).exists():
                    self.log(f"⚠️  Usuário {username} já existe, pulando...")
                    continue
                
                # Criar usuário
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=user_data.get('first_name', ''),
                    last_name=user_data.get('last_name', ''),
                    password='temp123456'  # Senha temporária - usuário deve redefinir
                )
                
                # Criar perfil se tiver dados
                profile_data = user_data.get('profile', {})
                if profile_data:
                    UserProfile.objects.create(
                        user=user,
                        cpf=profile_data.get('cpf', ''),
                        telefone=profile_data.get('telefone', ''),
                        nome_social=profile_data.get('nome_social', ''),
                        data_nascimento=profile_data.get('data_nascimento', ''),
                        cep=profile_data.get('cep', ''),
                        logradouro=profile_data.get('logradouro', ''),
                        numero=profile_data.get('numero', ''),
                        bairro=profile_data.get('bairro', ''),
                        uf=profile_data.get('uf', ''),
                        cidade=profile_data.get('cidade', '')
                    )
                
                self.stats['usuarios_migrados'] += 1
                self.log(f"✅ Usuário {username} migrado com sucesso")
                
            except Exception as e:
                erro = f"Erro ao migrar usuário {user_data.get('username', 'N/A')}: {e}"
                self.log(f"❌ {erro}")
                self.stats['erros'].append(erro)
    
    def migrar_rifas(self, rifas_data):
        """Migra rifas do ambiente anterior"""
        self.log("🎯 Iniciando migração de rifas...")
        
        for rifa_data in rifas_data:
            try:
                titulo = rifa_data.get('titulo', '')
                
                if not titulo:
                    continue
                
                # Verificar se rifa já existe
                if Rifa.objects.filter(titulo=titulo).exists():
                    self.log(f"⚠️  Rifa '{titulo}' já existe, pulando...")
                    continue
                
                # Criar rifa
                rifa = Rifa.objects.create(
                    titulo=titulo,
                    descricao=rifa_data.get('descricao', ''),
                    preco=rifa_data.get('preco', 10.0),
                    encerrada=rifa_data.get('encerrada', False),
                    ganhador_nome=rifa_data.get('ganhador_nome', ''),
                    ganhador_numero=rifa_data.get('ganhador_numero')
                )
                
                self.stats['rifas_migradas'] += 1
                self.log(f"✅ Rifa '{titulo}' migrada com sucesso")
                
            except Exception as e:
                erro = f"Erro ao migrar rifa {rifa_data.get('titulo', 'N/A')}: {e}"
                self.log(f"❌ {erro}")
                self.stats['erros'].append(erro)
    
    def migrar_bilhetes(self, bilhetes_data):
        """Migra bilhetes do ambiente anterior"""
        self.log("🎫 Iniciando migração de bilhetes...")
        
        for bilhete_data in bilhetes_data:
            try:
                numero = bilhete_data.get('numero')
                rifa_id = bilhete_data.get('rifa_id')
                
                if not numero or not rifa_id:
                    continue
                
                # Buscar rifa correspondente
                try:
                    rifa = Rifa.objects.get(id=rifa_id)
                except Rifa.DoesNotExist:
                    self.log(f"⚠️  Rifa ID {rifa_id} não encontrada para bilhete {numero}")
                    continue
                
                # Verificar se bilhete já existe
                if Numero.objects.filter(rifa=rifa, numero=numero).exists():
                    self.log(f"⚠️  Bilhete {numero} da rifa {rifa.titulo} já existe, pulando...")
                    continue
                
                # Criar bilhete
                Numero.objects.create(
                    rifa=rifa,
                    numero=numero,
                    status=bilhete_data.get('status', 'livre'),
                    comprador_nome=bilhete_data.get('comprador_nome', ''),
                    comprador_email=bilhete_data.get('comprador_email', ''),
                    comprador_telefone=bilhete_data.get('comprador_telefone', ''),
                    comprador_cpf=bilhete_data.get('comprador_cpf', '')
                )
                
                self.stats['bilhetes_migrados'] += 1
                
                if self.stats['bilhetes_migrados'] % 100 == 0:
                    self.log(f"📊 {self.stats['bilhetes_migrados']} bilhetes migrados...")
                
            except Exception as e:
                erro = f"Erro ao migrar bilhete {bilhete_data.get('numero', 'N/A')}: {e}"
                self.log(f"❌ {erro}")
                self.stats['erros'].append(erro)
    
    def executar_migracao(self):
        """Executa a migração completa"""
        self.log("🚀 Iniciando processo de migração...")
        
        # 1. Fazer backup do estado atual
        self.fazer_backup_atual()
        
        # 2. Buscar dados do ambiente anterior
        dados_origem = self.buscar_dados_origem()
        
        if not dados_origem:
            self.log("❌ Não foi possível obter dados do ambiente anterior")
            return False
        
        # 3. Executar migração dentro de transação
        try:
            with transaction.atomic():
                # Migrar usuários
                usuarios = dados_origem.get('users', [])
                if usuarios:
                    self.migrar_usuarios(usuarios)
                
                # Migrar rifas
                rifas = dados_origem.get('rifas', [])
                if rifas:
                    self.migrar_rifas(rifas)
                
                # Migrar bilhetes
                bilhetes = dados_origem.get('numeros', [])
                if bilhetes:
                    self.migrar_bilhetes(bilhetes)
                
                self.log("✅ Migração concluída com sucesso!")
                
        except Exception as e:
            self.log(f"❌ Erro durante migração: {e}")
            self.log("🔄 Transação revertida")
            return False
        
        # 4. Exibir relatório
        self.exibir_relatorio()
        return True
    
    def exibir_relatorio(self):
        """Exibe relatório da migração"""
        self.log("\n" + "="*50)
        self.log("📊 RELATÓRIO DA MIGRAÇÃO")
        self.log("="*50)
        self.log(f"👥 Usuários migrados: {self.stats['usuarios_migrados']}")
        self.log(f"🎯 Rifas migradas: {self.stats['rifas_migradas']}")
        self.log(f"🎫 Bilhetes migrados: {self.stats['bilhetes_migrados']}")
        self.log(f"❌ Erros encontrados: {len(self.stats['erros'])}")
        
        if self.stats['erros']:
            self.log("\n🔍 DETALHES DOS ERROS:")
            for erro in self.stats['erros'][:10]:  # Mostrar apenas os primeiros 10
                self.log(f"  • {erro}")
            if len(self.stats['erros']) > 10:
                self.log(f"  ... e mais {len(self.stats['erros']) - 10} erros")
        
        self.log("="*50)

def main():
    """Função principal"""
    print("\n🔄 MIGRAÇÃO DE DADOS - PANTANAL RIFAS")
    print("="*50)
    
    resposta = input("⚠️  Confirma migração? Este processo pode demorar alguns minutos. (s/N): ")
    
    if resposta.lower() != 's':
        print("❌ Migração cancelada pelo usuário")
        return
    
    migracao = MigracaoDados()
    sucesso = migracao.executar_migracao()
    
    if sucesso:
        print("\n🎉 Migração concluída!")
        print("\n📋 PRÓXIMOS PASSOS:")
        print("1. Verificar dados migrados no admin Django")
        print("2. Testar login dos usuários (senha temporária: temp123456)")
        print("3. Enviar instruções para usuários redefinirem senhas")
        print("4. Verificar bilhetes pagos e status das rifas")
    else:
        print("\n❌ Migração falhou. Verifique os logs acima.")

if __name__ == "__main__":
    main()