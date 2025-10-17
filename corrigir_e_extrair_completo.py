import os
import sys
import django
import csv
from datetime import datetime
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rifa.settings')
django.setup()

from rifa.models import Numero

NOMES_PAGOS = [
    'LENNON', 'CAMILA', 'MAYARA', 'CLEYTON', 'PAULO', 'ALESON',
    'LUANA', 'ARTHUR', 'LIDILAINE', 'EMERSON', 'IZADIR', 'WALLACE',
    'THAIZA', 'DIEGO', 'ARLINDO', 'RAYSSA', 'JUAN', 'IVETE',
    'THAYNARA', 'VANESSA', 'JEFFERSON', 'DANIEL', 'KETLLYN',
    'ADREVAN', 'JESSICA', 'CESAR', 'CRISTIELLEN', 'JUBIARA',
    'PATRICIA', 'PATRICK', 'VICTOR', 'ELIVELTON', 'CAROLINA',
    'JUSTINO', 'WAGNER', 'DORIS', 'LUIS', 'MARIA', 'WALTER'
]

PRECO_BILHETE = Decimal('1.97')

print("="*80)
print("CORRECAO E EXTRACAO COMPLETA - PANTANAL DA SORTE")
print("="*80)

print("\nPASSO 1: Corrigindo status dos bilhetes...")
corrigidos = 0

for nome in NOMES_PAGOS:
    bilhetes = Numero.objects.filter(
        comprador_nome__icontains=nome,
        status__iexact='reservado'
    )
    
    if bilhetes.exists():
        print(f"Corrigindo {nome}: {bilhetes.count()} bilhetes")
        for bilhete in bilhetes:
            bilhete.status = 'Pago'
            bilhete.save()
            corrigidos += 1

print(f"\nTotal de bilhetes corrigidos: {corrigidos}")

print("\nPASSO 2: Extraindo todos os bilhetes pagos...")

bilhetes_pagos = Numero.objects.filter(status__iexact='pago').order_by('comprador_email')

print(f"Total de bilhetes PAGOS: {bilhetes_pagos.count()}")

compradores = {}

for bilhete in bilhetes_pagos:
    email = (bilhete.comprador_email or '').lower().strip()
    nome = (bilhete.comprador_nome or 'Nao informado').strip()
    telefone = (bilhete.comprador_telefone or 'Nao informado').strip()
    cpf = getattr(bilhete, 'comprador_cpf', 'Nao informado')
    
    chave = email if email else f"sem_email_{nome.lower().replace(' ', '_')}"
    
    if chave not in compradores:
        compradores[chave] = {
            'nome': nome,
            'email': email or 'Nao informado',
            'telefone': telefone,
            'cpf': cpf,
            'numeros': [],
            'quantidade': 0,
            'valor_total': Decimal('0.00')
        }
    
    compradores[chave]['numeros'].append(str(bilhete.numero))
    compradores[chave]['quantidade'] += 1
    compradores[chave]['valor_total'] += PRECO_BILHETE

compradores_ordenados = sorted(
    compradores.values(),
    key=lambda x: x['valor_total'],
    reverse=True
)

print("\nPASSO 3: Gerando planilha completa...")

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
arquivo_csv = f'reembolso_completo_{timestamp}.csv'

with open(arquivo_csv, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    
    writer.writerow([
        'Nome Completo', 'Email', 'Telefone/WhatsApp', 'CPF',
        'Quantidade de Bilhetes', 'Numeros', 'Valor a Reembolsar'
    ])
    
    for comp in compradores_ordenados:
        numeros_str = ', '.join(sorted(comp['numeros'], key=lambda x: int(x))[:20])
        if len(comp['numeros']) > 20:
            numeros_str += f" ... (+{len(comp['numeros'])-20} numeros)"
        
        writer.writerow([
            comp['nome'],
            comp['email'],
            comp['telefone'],
            comp['cpf'],
            comp['quantidade'],
            numeros_str,
            f"R$ {comp['valor_total']:.2f}"
        ])

print(f"Arquivo gerado: {arquivo_csv}")

print("\n" + "="*80)
print("RESUMO FINAL")
print("="*80)

total_compradores = len(compradores)
total_bilhetes = sum(c['quantidade'] for c in compradores.values())
total_valor = sum(c['valor_total'] for c in compradores.values())

print(f"Total de Compradores: {total_compradores}")
print(f"Total de Bilhetes Pagos: {total_bilhetes}")
print(f"Valor Total a Reembolsar: R$ {total_valor:.2f}")
print(f"Valor Recebido (Mercado Pago): R$ 596,92")
print(f"Diferenca: R$ {596.92 - float(total_valor):.2f}")
print("="*80)

print("\nTOP 10 COMPRADORES:\n")
for i, comp in enumerate(compradores_ordenados[:10], 1):
    print(f"{i}. {comp['nome']}")
    print(f"   Email: {comp['email']}")
    print(f"   Telefone: {comp['telefone']}")
    print(f"   Bilhetes: {comp['quantidade']}")
    print(f"   Valor: R$ {comp['valor_total']:.2f}\n")

print("CORRECAO CONCLUIDA!")
print(f"Arquivo salvo: {arquivo_csv}")