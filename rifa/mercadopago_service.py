import os
import logging
import json
from decimal import Decimal

logger = logging.getLogger(__name__)


def criar_preferencia(titulo: str, preco: float):
    """Cria uma preferência de pagamento no Mercado Pago e retorna o objeto de preferência.

    Retorna um dict com pelo menos a chave 'init_point' quando bem sucedido.
    """
    # Preferir leitura a partir das settings do Django quando disponível
    access_token = None
    try:
        from django.conf import settings
        access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None)
    except Exception:
        access_token = None

    if not access_token:
        access_token = os.getenv('MERCADOPAGO_ACCESS_TOKEN')

    if not access_token:
        raise RuntimeError('MERCADOPAGO_ACCESS_TOKEN não configurado')

    try:
        # Tenta usar o SDK se disponível
        try:
            import mercadopago
            sdk = mercadopago.SDK(access_token)
            preference_data = {
                "items": [
                    {
                        "title": titulo,
                        "quantity": 1,
                        "unit_price": Decimal(preco),
                    }
                ]
            }
            resp = sdk.preference().create(preference_data)
            if isinstance(resp, dict):
                # sdk retorna dict com chave 'response'
                return resp.get('response') or resp
            return resp
        except Exception:
            # Fallback: usar API HTTP
            import requests
            url = 'https://api.mercadolibre.com/checkout/preferences'
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            payload = {
                "items": [
                    {
                        "title": titulo,
                        "quantity": 1,
                        "unit_price": float(preco)
                    }
                ]
            }
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.exception('Erro ao criar preferência Mercado Pago: %s', e)
        raise


def criar_pagamento_pix(amount: float, payer_email: str = None, external_reference: str = None, description: str = 'Pagamento'):
    """Cria um pagamento do tipo PIX no Mercado Pago e retorna o dicionário de resposta do provedor.

    Retorno esperado: dict contendo pelo menos 'id' e, quando disponível, 'point_of_interaction' com transaction_data.qr_code_base64 ou qr_code.
    """
    # reusa lógica de token
    access_token = None
    try:
        from django.conf import settings
        access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None)
    except Exception:
        access_token = None

    if not access_token:
        access_token = os.getenv('MERCADOPAGO_ACCESS_TOKEN')

    if not access_token:
        raise RuntimeError('MERCADOPAGO_ACCESS_TOKEN não configurado')

    payment_data = {
        "transaction_amount": float(amount),
        "description": description,
        "payment_method_id": "pix",
        "payer": {
            "email": payer_email or 'test_user_123456@testuser.com'
        }
    }
    if external_reference:
        payment_data['external_reference'] = str(external_reference)

    try:
        try:
            import mercadopago
            sdk = mercadopago.SDK(access_token)
            resp = sdk.payment().create(payment_data)
            if isinstance(resp, dict):
                return resp.get('response') or resp
            return resp
        except Exception:
            import requests
            url = 'https://api.mercadopago.com/v1/payments'
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            r = requests.post(url, headers=headers, data=json.dumps(payment_data), timeout=10)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.exception('Erro ao criar pagamento PIX Mercado Pago: %s', e)
        raise
