import os
import django
import csv
from datetime import datetime
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rifa.settings')
django.setup()

from rifa.models import Numero

# Lista completa de pagamentos do Mercado Pago
PAGAMENTOS_MP = [
    ('Jessica Francielly Mendonza Ferreira', 5.91),
    ('JENNIFER CAMPOS GARAI', 11.82),
    ('GLADYS SANCHEZ CAMPOS', 21.67),
    ('CARLOS DAVID JIMENEZ PAZ JUNIOR', 21.67),
    ('Suanny Valheco De Oliveira', 1.97),
    ('Renan Peterson Salvatierra da Costa', 21.67),
    ('LAURA DE ARRUDA MAGALHAES', 9.85),
    ('Thiago Dolacio', 21.67),
    ('Richard Wiliam Queiroz Pereira', 9.85),
    ('LUCAS DE SOUZA BARRETO', 1.97),
    ('Anna Júlia', 1.97),
    ('Maria Joice Soares Silva Santos', 1.97),
    ('Leonel de barros lima', 1.97),
    ('RAFAEL SANCHEZ CAMPOS RODRIGUES', 1.97),
    ('Elton lenon', 1.97),
    ('Kellen Amorim Ferro', 1.97),
    ('VIVIANE DA SILVA', 13.79),
    ('WALDECIR SOUZA DE ALMEIDA', 11.82),
    ('Sulivan saucedo de souza', 1.97),
    ('Wagner Souza Sarath', 1.97),
    ('Mayara Pereira Canavarros', 9.85),
    ('CAMILA DA SILVA CUBILLOS', 11.82),
    ('Kethyleen Yonny da Silva Candea', 5.91),
    ('VANICE GUTIERRES', 11.82),
    ('Erica dos Santos Lemos', 13.79),
    ('Joyce dos Santos Oliveira', 11.82),
    ('THIAGO HENRIQUE DO NASCIMENTO', 1.97),
    ('Leonel De Barros Lima', 1.97),
    ('Cleyton Abraão', 11.82),
    ('SILVANA CARRELO', 21.67),
    ('Ivete Ribeiro Da Silva', 9.85),
    ('THAYNARA APARECIDA', 1.97),
    ('Vanessa Vieira Davilas', 1.97),
    ('Vanessa Duarte Sabala', 1.97),
    ('Jefferson Augusto Centurion', 5.91),
    ('Daniel Goncalves de Lima', 21.67),
    ('KETLLYN SOARES DA SILVA', 1.97),
    ('Adrevan Lemos Gomes', 9.85),
    ('Thaiza Rodrigues Dias', 9.85),
    ('Wallace Candia Rodrigues', 5.91),
    ('EMERSON SOARES DA SILVA', 1.97),
    ('Izadir Medina Guimaraes', 11.82),
    ('LIDILAINE SOARES DA SILVA', 1.97),
    ('Camila amorim morel', 5.91),
    ('ARTHUR LAEL LESSA SOARES', 1.97),
    ('LUANA MONTANA MERCADO', 5.91),
    ('ALESON KELVE ROSA VILAGRA', 29.55),
    ('Juan Douglas Marques', 1.97),
    ('RAYSSA CAETANO DE OLIVEIRA', 21.67),
    ('ARLINDO PEREIRA DA SILVA FILHO', 1.97),
    ('DIEGO CAETANO DA COSTA', 5.91),
    ('Jessica Jeanne Alle Pereira', 5.91),
    ('Cesar Bispo de Souza', 11.82),
    ('Cristiellen Teixeira de Amorim', 5.91),
    ('PAULO HIGOR MANCILHA DE LIMA', 41.38),
    ('LENNON DE OLIVEIRA DUARTE', 9.85),
    ('Daniel Ferreira da Costa', 1.97),
    ('Victor Hugo Fernandes Menacho', 1.97),
    ('Elivelton Pessoa Machado', 1.97),
    ('CAROLINA APARECIDA PACHECO', 7.88),
    ('Jubiara Matos Peres', 1.97),
    ('PATRICIA OTILIA DA SILVA', 9.85),
    ('PATRICK DOS REIS GONCALVES', 21.67),
    ('Justino Ferreira Silva', 11.82),
    ('Wagner Moreira De Oliveira', 1.97),
    ('Doris Nogueira Goncalves', 1.97),
    ('LUIS JULIANO DA SILVA', 1.97),
    ('Maria Luiza Pacehco de Lima', 1.97),
    ('Walter César da Silva', 9.85),
]

PRECO_BILHETE = Decimal('1.97')

print("="*80)
print("CRUZAMENTO: MERCADO PAGO x BANCO DE DADOS")
print("="*80)

total_mp = sum(valor for _, valor in PAGAMENTOS_MP)
print(f"\nTotal recebido no Mercado Pago: R$ {total_mp:.2f}")
print(f"Total de pagamentos: {len(PAGAMENTOS_MP)}")

# Buscar e marcar bilhetes baseado nos nomes do MP
compradores_encontrados = {}
nao_encontrados = []

for nome_mp, valor_mp in PAGAMENTOS_MP:
    # Pegar primeiros 2 nomes para busca
    palavras = nome_mp.split()
    primeiro_nome = palavras[0] if palavras else ''
    segundo_nome = palavras[1] if len(palavras) > 1 else ''
    
    # Buscar bilhetes
    bilhetes = Numero.objects.filter(
        comprador_nome__icontains=primeiro_nome
    )
    
    # Refinar busca com segundo nome se houver múltiplos resultados
    if bilhetes.count() > 1 and segundo_nome:
        bilhetes = bilhetes.filter(comprador_nome__icontains=segundo_nome)
    
    if bilhetes.exists():
        # Calcular quantidade esperada
        qtd_esperada = int(valor_mp / 1.97)
        qtd_encontrada = bilhetes.count()
        
        # Marcar como pago se ainda não for
        bilhetes_marcados = 0
        for bilhete in bilhetes[:qtd_esperada]:  # Limitar à quantidade esperada
            if bilhete.status.lower() != 'pago':
                bilhete.status = 'Pago'
                bilhete.save()
                bilhetes_marcados += 1
        
        # Pegar dados do primeiro bilhete
        primeiro = bilhetes.first()
        email = primeiro.comprador_email or 'Não informado'
        telefone = primeiro.comprador_telefone or 'Não informado'
        
        if email not in compradores_encontrados:
            compradores_encontrados[email] = {
                'nome': nome_mp,
                'email': email,
                'telefone': telefone,
                'valor': Decimal(str(valor_mp)),
                'bilhetes': qtd_esperada,
                'status': f"Encontrado ({bilhetes_marcados} marcados como pago)"
            }
        
        print(f"✅ {nome_mp}: {qtd_esperada} bilhetes | {bilhetes_marcados} marcados")
    else:
        nao_encontrados.append((nome_mp, valor_mp))
        print(f"❌ {nome_mp}: NÃO ENCONTRADO no banco")

# Adicionar bilhetes já marcados como pago que não estavam na lista do MP
bilhetes_pagos_existentes = Numero.objects.filter(status__iexact='pago')
for bilhete in bilhetes_pagos_existentes:
    email = (bilhete.comprador_email or '').lower().strip()
    nome = bilhete.comprador_nome or 'Não informado'
    telefone = bilhete.comprador_telefone or 'Não informado'
    
    chave = email if email else f"sem_email_{nome.lower().replace(' ', '_')}"
    
    if chave not in compradores_encontrados:
        compradores_encontrados[chave] = {
            'nome': nome,
            'email': email or 'Não informado',
            'telefone': telefone,
            'valor': PRECO_BILHETE,
            'bilhetes': 1,
            'status': 'Já estava como pago'
        }
    else:
        # Apenas incrementar se já existir
        compradores_encontrados[chave]['bilhetes'] += 1
        compradores_encontrados[chave]['valor'] += PRECO_BILHETE

# Gerar CSV final
arquivo_csv = f'lista_reembolso_final_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

with open(arquivo_csv, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    writer.writerow([
        'Nome Completo', 'Email', 'Telefone/WhatsApp', 
        'Quantidade de Bilhetes', 'Valor a Reembolsar', 'Status'
    ])
    
    for comp in sorted(compradores_encontrados.values(), key=lambda x: x['valor'], reverse=True):
        writer.writerow([
            comp['nome'],
            comp['email'],
            comp['telefone'],
            comp['bilhetes'],
            f"R$ {comp['valor']:.2f}",
            comp['status']
        ])