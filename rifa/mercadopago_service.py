import os
import logging
import json
import requests
from decimal import Decimal
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MercadoPagoService:
    """
    Serviço completo para integração com Mercado Pago PIX
    """
    
    def __init__(self):
        self.access_token = self._get_access_token()
        self.base_url = "https://api.mercadopago.com"
        
    def _get_access_token(self) -> str:
        """Obtém o access token das configurações"""
        try:
            from django.conf import settings
            token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None)
        except Exception:
            token = None
            
        if not token:
            token = os.getenv('MERCADOPAGO_ACCESS_TOKEN')
            
        if not token:
            raise RuntimeError('MERCADOPAGO_ACCESS_TOKEN não configurado')
            
        return token
    
    def criar_pagamento_pix(
        self, 
        amount: float, 
        description: str = "Pagamento PIX",
        payer_email: Optional[str] = None,
        external_reference: Optional[str] = None,
        payer_cpf: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cria um pagamento PIX no Mercado Pago
        
        Args:
            amount: Valor do pagamento
            description: Descrição do pagamento
            payer_email: Email do pagador (opcional)
            external_reference: Referência externa (ID do pedido)
            payer_cpf: CPF do pagador (opcional)
            
        Returns:
            Dict com dados do pagamento incluindo QR Code
        """
        try:
            url = f"{self.base_url}/v1/payments"
            
            # Headers da requisição
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'X-Idempotency-Key': f"pix_{external_reference or 'payment'}_{int(amount * 100)}"
            }
            
            # Preparar dados do pagador
            payer_data = {
                "email": payer_email or "test_user@testuser.com"
            }
            
            # Adicionar CPF se fornecido
            if payer_cpf:
                # Limpar CPF (manter apenas números)
                cpf_clean = ''.join(filter(str.isdigit, payer_cpf))
                if len(cpf_clean) == 11:
                    payer_data["identification"] = {
                        "type": "CPF",
                        "number": cpf_clean
                    }
            
            # Dados do pagamento
            payment_data = {
                "transaction_amount": float(amount),
                "description": description,
                "payment_method_id": "pix",
                "payer": payer_data
            }
            
            # Adicionar referência externa se fornecida
            if external_reference:
                payment_data["external_reference"] = str(external_reference)
            
            logger.info(f"Criando pagamento PIX: {payment_data}")
            
            # Fazer requisição para Mercado Pago
            response = requests.post(
                url, 
                headers=headers, 
                data=json.dumps(payment_data),
                timeout=30
            )
            
            logger.info(f"Status da resposta MP: {response.status_code}")
            
            # Verificar se a requisição foi bem-sucedida
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Resposta completa do Mercado Pago: {json.dumps(result, indent=2)}")
            
            # Extrair informações importantes
            payment_info = {
                "success": True,
                "payment_id": result.get("id"),
                "status": result.get("status"),
                "qr_code": None,
                "qr_code_base64": None,
                "pix_code": None,
                "raw_response": result
            }
            
            # Extrair QR Code e dados PIX
            point_of_interaction = result.get("point_of_interaction", {})
            transaction_data = point_of_interaction.get("transaction_data", {})
            
            if transaction_data:
                payment_info["qr_code"] = transaction_data.get("qr_code")
                payment_info["qr_code_base64"] = transaction_data.get("qr_code_base64")
                payment_info["pix_code"] = transaction_data.get("qr_code")  # Código PIX para copiar
                
                logger.info(f"QR Code extraído - Base64: {'SIM' if payment_info['qr_code_base64'] else 'NÃO'}, "
                          f"Texto: {'SIM' if payment_info['qr_code'] else 'NÃO'}")
            else:
                logger.warning("Nenhum transaction_data encontrado na resposta")
            
            return payment_info
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erro HTTP ao criar pagamento PIX: {e}")
            logger.error(f"Resposta do servidor: {e.response.text if e.response else 'N/A'}")
            return {
                "success": False,
                "error": f"Erro HTTP {e.response.status_code if e.response else 'unknown'}",
                "details": e.response.text if e.response else str(e)
            }
        except requests.exceptions.RequestException as e:
            logger.exception(f"Erro de rede ao criar pagamento PIX: {e}")
            return {
                "success": False,
                "error": "Erro de conexão com Mercado Pago",
                "details": str(e)
            }
        except Exception as e:
            logger.exception(f"Erro inesperado ao criar pagamento PIX: {e}")
            return {
                "success": False,
                "error": "Erro interno",
                "details": str(e)
            }
    
    def verificar_pagamento(self, payment_id: str) -> Dict[str, Any]:
        """
        Verifica o status de um pagamento
        
        Args:
            payment_id: ID do pagamento no Mercado Pago
            
        Returns:
            Dict com status do pagamento
        """
        try:
            url = f"{self.base_url}/v1/payments/{payment_id}"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "success": True,
                "payment_id": result.get("id"),
                "status": result.get("status"),
                "status_detail": result.get("status_detail"),
                "external_reference": result.get("external_reference"),
                "transaction_amount": result.get("transaction_amount"),
                "date_created": result.get("date_created"),
                "date_approved": result.get("date_approved"),
                "raw_response": result
            }
            
        except requests.exceptions.RequestException as e:
            logger.exception(f"Erro ao verificar pagamento {payment_id}: {e}")
            return {
                "success": False,
                "error": "Erro de conexão",
                "details": str(e)
            }
        except Exception as e:
            logger.exception(f"Erro inesperado ao verificar pagamento {payment_id}: {e}")
            return {
                "success": False,
                "error": "Erro interno",
                "details": str(e)
            }

    def testar_conexao(self) -> Dict[str, Any]:
        """
        Testa a conexão com a API do Mercado Pago
        
        Returns:
            Dict com resultado do teste
        """
        try:
            url = f"{self.base_url}/users/me"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            user_data = response.json()
            
            return {
                "success": True,
                "user_id": user_data.get("id"),
                "nickname": user_data.get("nickname"),
                "email": user_data.get("email"),
                "country_id": user_data.get("country_id"),
                "message": "Conexão com Mercado Pago OK"
            }
            
        except Exception as e:
            logger.exception(f"Erro ao testar conexão: {e}")
            return {
                "success": False,
                "error": "Falha na conexão",
                "details": str(e)
            }


# Funções de compatibilidade com o código existente
def criar_preferencia(titulo: str, preco: float) -> Dict[str, Any]:
    """
    Cria uma preferência de pagamento no Mercado Pago (para checkout)
    Mantido para compatibilidade
    """
    try:
        service = MercadoPagoService()
        access_token = service.access_token
        
        url = 'https://api.mercadopago.com/checkout/preferences'
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
            ],
            "back_urls": {
                "success": "https://pantanaldasortems.com/pagamento/sucesso/",
                "failure": "https://pantanaldasortems.com/pagamento/falha/",
                "pending": "https://pantanaldasortems.com/pagamento/pendente/"
            },
            "auto_return": "approved"
        }
        
        response = requests.post(
            url, 
            headers=headers, 
            data=json.dumps(payload),
            timeout=10
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        logger.exception(f'Erro ao criar preferência Mercado Pago: {e}')
        raise


def criar_pagamento_pix(
    amount: float, 
    payer_email: str = None, 
    external_reference: str = None, 
    description: str = 'Pagamento PIX',
    payer_cpf: str = None
) -> Dict[str, Any]:
    """
    Função de compatibilidade para criar pagamento PIX
    """
    service = MercadoPagoService()
    return service.criar_pagamento_pix(
        amount=amount,
        description=description,
        payer_email=payer_email,
        external_reference=external_reference,
        payer_cpf=payer_cpf
    )