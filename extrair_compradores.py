import os
import sys
import django
import csv
from datetime import datetime
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rifa.settings')
django.setup()

from django.db.models import Sum, Count, Q
from django.contrib.auth.models import User
from rifa.models import Pedido, Numero, Rifa
from rifa.models_profile import UserProfile

def extrair_dados_compradores():
    """
    Extrai dados de todos os compradores com pedidos pagos ou pendentes
    """
    print("\n" + "="*70)
    print("🔍 INICIANDO EXTRAÇÃO DE DADOS DOS COMPRADORES")
    print("="*70 + "\n")
    
    # Buscar todos os pedidos pagos ou pendentes
    pedidos = Pedido.objects.filter(
        Q(status='pago') | Q(status='pendente')
    ).select_related('user', 'rifa').order_by('created_at')
    
    if not pedidos.exists():
        print("❌ Nenhum pedido encontrado!")
        print("   Statuses verificados: 'pago' e 'pendente'\n")
        return
    
    print(f"✅ Encontrados {pedidos.count()} pedidos\n")
    
    # Preparar dados para os CSVs
    dados_detalhados = []
    compradores_agrupados = {}
    total_geral = Decimal('0.00')
    
    for pedido in pedidos:
        usuario = pedido.user  # Nome do campo é 'user', não 'usuario'
        
        # Buscar números comprados neste pedido
        numeros_query = Numero.objects.filter(pedido=pedido)
        numeros_lista = ', '.join(map(str, sorted(numeros_query.values_list('numero', flat=True))))
        quantidade_numeros = numeros_query.count()
        
        # Calcular valor total do pedido
        valor_unitario = pedido.rifa.preco if hasattr(pedido.rifa, 'preco') else Decimal('0.00')
        valor_total = Decimal(quantidade_numeros) * valor_unitario
        total_geral += valor_total
        
        # Nome completo
        nome_completo = pedido.nome if hasattr(pedido, 'nome') and pedido.nome else ''
        if not nome_completo and usuario:
            nome_completo = f"{usuario.first_name} {usuario.last_name}".strip()
        if not nome_completo and usuario:
            nome_completo = usuario.username
        if not nome_completo:
            nome_completo = 'Não informado'
        
        # CPF - pode estar no pedido ou no perfil do usuário
        cpf = pedido.cpf if hasattr(pedido, 'cpf') and pedido.cpf else 'Não informado'
        if cpf == 'Não informado' and usuario and hasattr(usuario, 'profile'):
            cpf = usuario.profile.cpf if hasattr(usuario.profile, 'cpf') else 'Não informado'
        
        # Telefone - pode estar no pedido ou no perfil do usuário
        telefone = pedido.telefone if hasattr(pedido, 'telefone') and pedido.telefone else 'Não informado'
        if telefone == 'Não informado' and usuario and hasattr(usuario, 'profile'):
            telefone = usuario.profile.telefone if hasattr(usuario.profile, 'telefone') else 'Não informado'
        
        # Email
        email = usuario.email if usuario and hasattr(usuario, 'email') else 'Não informado'
        
        # Dados detalhados (uma linha por pedido)
        dados_detalhados.append({
            'ID Pedido': pedido.id,
            'Nome Completo': nome_completo,
            'CPF/CNPJ': cpf,
            'Email': email,
            'Telefone': telefone,
            'WhatsApp': telefone,
            'Rifa': pedido.rifa.titulo if hasattr(pedido.rifa, 'titulo') else 'Não informado',
            'Quantidade de Números': quantidade_numeros,
            'Números Comprados': numeros_lista if numeros_lista else 'Nenhum',
            'Valor por Número': f"R$ {valor_unitario:.2f}",
            'Valor Total': f"R$ {valor_total:.2f}",
            'Status Pedido': pedido.status,
            'Data da Compra': pedido.created_at.strftime('%d/%m/%Y %H:%M') if hasattr(pedido, 'created_at') else 'Não informado',
        })
        
        # Agrupar por usuário (usar ID do pedido se usuário for None)
        user_id = usuario.id if usuario else f"pedido_{pedido.id}"
        if user_id not in compradores_agrupados:
            compradores_agrupados[user_id] = {
                'Nome Completo': nome_completo,
                'CPF/CNPJ': cpf,
                'Email': email,
                'Telefone': telefone,
                'Total de Números': 0,
                'Valor Total': Decimal('0.00'),
                'Quantidade de Pedidos': 0,
                'Pedidos': []
            }
        
        compradores_agrupados[user_id]['Total de Números'] += quantidade_numeros
        compradores_agrupados[user_id]['Valor Total'] += valor_total
        compradores_agrupados[user_id]['Quantidade de Pedidos'] += 1
        compradores_agrupados[user_id]['Pedidos'].append({
            'ID': pedido.id,
            'Data': pedido.created_at.strftime('%d/%m/%Y') if hasattr(pedido, 'created_at') else 'N/A',
            'Valor': f"R$ {valor_total:.2f}",
            'Status': pedido.status
        })
    
    # Gerar timestamp para os arquivos
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # ========== ARQUIVO 1: DETALHADO (todos os pedidos) ==========
    arquivo_detalhado = f'compradores_detalhado_{timestamp}.csv'
    
    print("📝 Gerando arquivo detalhado...")
    with open(arquivo_detalhado, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = [
            'ID Pedido', 'Nome Completo', 'CPF/CNPJ', 'Email', 'Telefone', 'WhatsApp',
            'Rifa', 'Quantidade de Números', 'Números Comprados', 'Valor por Número',
            'Valor Total', 'Status Pedido', 'Data da Compra'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dados_detalhados)
    
    print(f"✅ Arquivo detalhado criado: {arquivo_detalhado}\n")
    
    # ========== ARQUIVO 2: RESUMIDO (agrupado por comprador) ==========
    arquivo_resumido = f'compradores_resumido_{timestamp}.csv'
    
    print("📝 Gerando arquivo resumido...")
    with open(arquivo_resumido, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = [
            'Nome Completo', 'CPF/CNPJ', 'Email', 'Telefone/WhatsApp',
            'Quantidade de Pedidos', 'Total de Números Comprados', 'Valor Total a Reembolsar'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for dados in compradores_agrupados.values():
            writer.writerow({
                'Nome Completo': dados['Nome Completo'],
                'CPF/CNPJ': dados['CPF/CNPJ'],
                'Email': dados['Email'],
                'Telefone/WhatsApp': dados['Telefone'],
                'Quantidade de Pedidos': dados['Quantidade de Pedidos'],
                'Total de Números Comprados': dados['Total de Números'],
                'Valor Total a Reembolsar': f"R$ {dados['Valor Total']:.2f}"
            })
    
    print(f"✅ Arquivo resumido criado: {arquivo_resumido}\n")
    
    # ========== RESUMO GERAL ==========
    print("=" * 70)
    print("📊 RESUMO DA EXTRAÇÃO")
    print("=" * 70)
    print(f"Total de compradores únicos: {len(compradores_agrupados)}")
    print(f"Total de pedidos: {len(dados_detalhados)}")
    print(f"Valor total a reembolsar: R$ {total_geral:.2f}")
    print("=" * 70 + "\n")
    
    # ========== LISTA DETALHADA DE COMPRADORES ==========
    print("👥 LISTA DE COMPRADORES (ordenados por valor):\n")
    
    compradores_ordenados = sorted(
        compradores_agrupados.values(),
        key=lambda x: x['Valor Total'],
        reverse=True
    )
    
    for i, dados in enumerate(compradores_ordenados, 1):
        print(f"{i}. 👤 {dados['Nome Completo']}")
        print(f"   📱 WhatsApp: {dados['Telefone']}")
        print(f"   📧 Email: {dados['Email']}")
        print(f"   🎫 Números comprados: {dados['Total de Números']}")
        print(f"   💰 Valor a reembolsar: R$ {dados['Valor Total']:.2f}")
        print(f"   📦 Pedidos realizados: {dados['Quantidade de Pedidos']}")
        
        # Mostrar detalhes dos pedidos
        if dados['Pedidos']:
            print(f"   📋 Detalhes dos pedidos:")
            for pedido in dados['Pedidos']:
                print(f"      • Pedido #{pedido['ID']} - {pedido['Data']} - {pedido['Valor']} - Status: {pedido['Status']}")
        print()
    
    # ========== ESTATÍSTICAS ADICIONAIS ==========
    print("\n" + "=" * 70)
    print("📈 ESTATÍSTICAS ADICIONAIS")
    print("=" * 70)
    
    # Média de valor por comprador
    media_por_comprador = total_geral / len(compradores_agrupados) if compradores_agrupados else Decimal('0.00')
    print(f"Média de valor por comprador: R$ {media_por_comprador:.2f}")
    
    # Média de números por comprador
    total_numeros = sum(d['Total de Números'] for d in compradores_agrupados.values())
    media_numeros = total_numeros / len(compradores_agrupados) if compradores_agrupados else 0
    print(f"Média de números por comprador: {media_numeros:.1f}")
    
    # Maior e menor comprador
    if compradores_ordenados:
        maior = compradores_ordenados[0]
        menor = compradores_ordenados[-1]
        print(f"\n🥇 Maior comprador: {maior['Nome Completo']} - R$ {maior['Valor Total']:.2f}")
        print(f"🥉 Menor comprador: {menor['Nome Completo']} - R$ {menor['Valor Total']:.2f}")
    
    print("=" * 70 + "\n")

if __name__ == '__main__':
    try:
        extrair_dados_compradores()
        
        print("✅ EXTRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("\n📁 Arquivos CSV gerados na pasta do projeto:")
        print("   • compradores_detalhado_[timestamp].csv")
        print("   • compradores_resumido_[timestamp].csv")
        print("\n💡 Dica: Abra os arquivos CSV no Excel ou Google Sheets")
        print("   para melhor visualização e organização dos reembolsos.\n")
        
    except Exception as e:
        print(f"\n❌ ERRO ao extrair dados: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)