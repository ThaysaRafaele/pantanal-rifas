import os
import django
import csv
from datetime import datetime
from decimal import Decimal
from collections import defaultdict

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rifa.settings')
django.setup()

from rifa.models import Numero

print("=" * 80)
print("ANÁLISE DA LISTA CONSOLIDADA EXISTENTE")
print("=" * 80)

# Ler o arquivo existente
compradores = {}
valor_total_arquivo = Decimal('0.00')

try:
    with open('LISTA_REEMBOLSO_CONSOLIDADA.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            nome = row['Nome Completo']
            valor_str = row['Valor a Reembolsar'].replace('R$ ', '').replace(',', '.')
            valor = Decimal(valor_str)
            email = row['Email']
            telefone = row['Telefone/WhatsApp']
            status = row['Status']
            
            compradores[nome] = {
                'nome': nome,
                'email': email,
                'telefone': telefone,
                'valor': valor,
                'status': status
            }
            valor_total_arquivo += valor
    
    print(f"\n✅ Arquivo lido com sucesso!")
    print(f"   Total de compradores: {len(compradores)}")
    print(f"   Valor total no arquivo: R$ {valor_total_arquivo:.2f}")
except FileNotFoundError:
    print("\n❌ Arquivo LISTA_REEMBOLSO_CONSOLIDADA.csv não encontrado!")
    exit(1)

# Lista oficial do Mercado Pago
PAGAMENTOS_MP = {
    'Jessica Francielly Mendonza Ferreira': 5.91,
    'JENNIFER CAMPOS GARAI': 11.82,
    'GLADYS SANCHEZ CAMPOS': 21.67,
    'CARLOS DAVID JIMENEZ PAZ JUNIOR': 21.67,
    'Suanny Valheco De Oliveira': 1.97,
    'Renan Peterson Salvatierra da Costa': 21.67,
    'LAURA DE ARRUDA MAGALHAES': 9.85,
    'Thiago Dolacio': 21.67,
    'Richard Wiliam Queiroz Pereira': 9.85,
    'LUCAS DE SOUZA BARRETO': 1.97,
    'Anna Júlia': 1.97,
    'Maria Joice Soares Silva Santos': 1.97,
    'Leonel de barros lima': 1.97,
    'RAFAEL SANCHEZ CAMPOS RODRIGUES': 1.97,
    'Elton lenon': 1.97,
    'Kellen Amorim Ferro': 1.97,
    'VIVIANE DA SILVA': 13.79,
    'WALDECIR SOUZA DE ALMEIDA': 11.82,
    'Sulivan saucedo de souza': 1.97,
    'Wagner Souza Sarath': 1.97,
    'Mayara Pereira Canavarros': 9.85,
    'CAMILA DA SILVA CUBILLOS': 11.82,
    'Kethyleen Yonny da Silva Candea': 5.91,
    'VANICE GUTIERRES': 11.82,
    'Erica dos Santos Lemos': 13.79,
    'Joyce dos Santos Oliveira': 11.82,
    'THIAGO HENRIQUE DO NASCIMENTO': 1.97,
    'Leonel De Barros Lima': 1.97,
    'Cleyton Abraão': 11.82,
    'SILVANA CARRELO': 21.67,
    'Ivete Ribeiro Da Silva': 9.85,
    'THAYNARA APARECIDA': 1.97,
    'Vanessa Vieira Davilas': 1.97,
    'Vanessa Duarte Sabala': 1.97,
    'Jefferson Augusto Centurion': 5.91,
    'Daniel Goncalves de Lima': 21.67,
    'KETLLYN SOARES DA SILVA': 1.97,
    'Adrevan Lemos Gomes': 9.85,
    'Thaiza Rodrigues Dias': 9.85,
    'Wallace Candia Rodrigues': 5.91,
    'EMERSON SOARES DA SILVA': 1.97,
    'Izadir Medina Guimaraes': 11.82,
    'LIDILAINE SOARES DA SILVA': 1.97,
    'Camila amorim morel': 5.91,
    'ARTHUR LAEL LESSA SOARES': 1.97,
    'LUANA MONTANA MERCADO': 5.91,
    'ALESON KELVE ROSA VILAGRA': 29.55,
    'Juan Douglas Marques': 1.97,
    'RAYSSA CAETANO DE OLIVEIRA': 21.67,
    'ARLINDO PEREIRA DA SILVA FILHO': 1.97,
    'DIEGO CAETANO DA COSTA': 5.91,
    'Jessica Jeanne Alle Pereira': 5.91,
    'Cesar Bispo de Souza': 11.82,
    'Cristiellen Teixeira de Amorim': 5.91,
    'PAULO HIGOR MANCILHA DE LIMA': 41.38,
    'LENNON DE OLIVEIRA DUARTE': 9.85,
    'Daniel Ferreira da Costa': 1.97,
    'Victor Hugo Fernandes Menacho': 1.97,
    'Elivelton Pessoa Machado': 1.97,
    'CAROLINA APARECIDA PACHECO': 7.88,
    'Jubiara Matos Peres': 1.97,
    'PATRICIA OTILIA DA SILVA': 9.85,
    'PATRICK DOS REIS GONCALVES': 21.67,
    'Justino Ferreira Silva': 11.82,
    'Wagner Moreira De Oliveira': 1.97,
    'Doris Nogueira Goncalves': 1.97,
    'LUIS JULIANO DA SILVA': 1.97,
    'Maria Luiza Pacehco de Lima': 1.97,
    'Walter César da Silva': 9.85,
}

total_mp = sum(PAGAMENTOS_MP.values())
print(f"\n💰 Total CORRETO do Mercado Pago: R$ {total_mp:.2f}")
print(f"   Total de transações: {len(PAGAMENTOS_MP)}")

# Comparar
diferenca = valor_total_arquivo - Decimal(str(total_mp))
print(f"\n⚠️  DIFERENÇA: R$ {diferenca:.2f}")

if abs(diferenca) > 0.01:
    print("\n🔍 ANALISANDO DISCREPÂNCIAS...")
    
    # Verificar quem está na lista mas não pagou
    nomes_arquivo = set(c['nome'].upper() for c in compradores.values())
    nomes_mp = set(n.upper() for n in PAGAMENTOS_MP.keys())
    
    # Nomes no arquivo mas não no MP
    extras = []
    for nome_orig, dados in compradores.items():
        nome_upper = nome_orig.upper()
        # Tentar encontrar no MP
        encontrado = False
        for nome_mp in PAGAMENTOS_MP.keys():
            if nome_mp.upper() in nome_upper or nome_upper in nome_mp.upper():
                encontrado = True
                break
        
        if not encontrado:
            extras.append((nome_orig, dados['valor']))
    
    if extras:
        print(f"\n❌ Encontrados {len(extras)} compradores NA LISTA mas NÃO NO MERCADO PAGO:")
        total_extra = Decimal('0.00')
        for nome, valor in sorted(extras, key=lambda x: x[1], reverse=True):
            print(f"   - {nome}: R$ {valor:.2f}")
            total_extra += valor
        print(f"\n   Total a REMOVER: R$ {total_extra:.2f}")

# Gerar lista CORRETA baseada APENAS no Mercado Pago
print("\n" + "=" * 80)
print("GERANDO LISTA CORRETA (APENAS PAGAMENTOS CONFIRMADOS)")
print("=" * 80)

lista_correta = []

for nome_mp, valor_mp in PAGAMENTOS_MP.items():
    # Buscar dados do comprador no arquivo existente
    dados = None
    for nome_arq, info in compradores.items():
        if nome_mp.upper() in nome_arq.upper() or nome_arq.upper() in nome_mp.upper():
            dados = info
            break
    
    if dados:
        lista_correta.append({
            'nome': dados['nome'],
            'email': dados['email'],
            'telefone': dados['telefone'],
            'valor': Decimal(str(valor_mp)),
            'status': dados['status']
        })
    else:
        # Buscar no banco de dados
        palavras = nome_mp.split()
        primeiro = palavras[0] if palavras else ''
        
        bilhetes = Numero.objects.filter(comprador_nome__icontains=primeiro).order_by('-id')
        
        if bilhetes.exists():
            b = bilhetes.first()
            lista_correta.append({
                'nome': b.comprador_nome or nome_mp,
                'email': b.comprador_email or 'Verificar no MP',
                'telefone': b.comprador_telefone or 'Verificar no MP',
                'valor': Decimal(str(valor_mp)),
                'status': 'OK - Dados no sistema' if b.comprador_email else 'ATENÇÃO: Buscar contato no Mercado Pago'
            })
        else:
            lista_correta.append({
                'nome': nome_mp,
                'email': 'Verificar no MP',
                'telefone': 'Verificar no MP',
                'valor': Decimal(str(valor_mp)),
                'status': 'ATENÇÃO: Buscar contato no Mercado Pago'
            })

# Ordenar por valor
lista_correta.sort(key=lambda x: x['valor'], reverse=True)

# Gerar CSV final
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
arquivo_final = f'LISTA_REEMBOLSO_CORRIGIDA_{timestamp}.csv'

with open(arquivo_final, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    writer.writerow(['Nome Completo', 'Email', 'Telefone/WhatsApp', 'Valor a Reembolsar', 'Status'])
    
    for comp in lista_correta:
        writer.writerow([
            comp['nome'],
            comp['email'],
            comp['telefone'],
            f"R$ {comp['valor']:.2f}",
            comp['status']
        ])

print(f"\n✅ Lista corrigida gerada: {arquivo_final}")
print(f"   Total de compradores: {len(lista_correta)}")
print(f"   Valor total: R$ {sum(c['valor'] for c in lista_correta):.2f}")

# Estatísticas
completos = sum(1 for c in lista_correta if 'OK' in c['status'])
verificar = len(lista_correta) - completos

print(f"\n📊 ESTATÍSTICAS:")
print(f"   Dados completos: {completos}")
print(f"   A verificar no MP: {verificar}")

print("\n" + "=" * 80)
print("✅ PROCESSO CONCLUÍDO!")
print("=" * 80)