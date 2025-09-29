from django.db import models
from django.utils import timezone
from datetime import timedelta

STATUS_CHOICES = [
    ('livre', 'Livre'),
    ('reservado', 'Reservado'),
    ('pago', 'Pago'),
]

class Rifa(models.Model):
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    quantidade_numeros = models.PositiveIntegerField(default=100, help_text='Quantidade total de números disponíveis para esta rifa.')
    imagem = models.ImageField(upload_to='rifas/', blank=True, null=True)
    encerrada = models.BooleanField(default=False, help_text='Marque como encerrada para tornar os bilhetes indisponíveis.')
    data_encerramento = models.DateTimeField(null=True, blank=True, help_text='Data e hora de encerramento da rifa.')
    ganhador_nome = models.CharField(max_length=100, blank=True, null=True, help_text='Nome do ganhador.')
    ganhador_numero = models.CharField(max_length=20, blank=True, null=True, help_text='Número do bilhete sorteado.')
    ganhador_cpf = models.CharField(max_length=14, blank=True, null=True, help_text='CPF do ganhador.')
    ganhador_foto = models.ImageField(upload_to='ganhadores/', blank=True, null=True, help_text='Foto do ganhador.')

    def __str__(self):
        return self.titulo

from django.contrib.auth.models import User

class NumeroRifa(models.Model):
    numero = models.IntegerField()
    rifa = models.ForeignKey('Rifa', on_delete=models.CASCADE)
    reservado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reservado_em = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.numero} - {self.rifa.titulo}"

class Numero(models.Model):
    rifa = models.ForeignKey(Rifa, on_delete=models.CASCADE, related_name='numeros', verbose_name='Rifa')
    numero = models.PositiveIntegerField(verbose_name='Número do bilhete')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='livre', verbose_name='Status')
    comprador_nome = models.CharField(max_length=100, blank=True, verbose_name='Nome do comprador')
    comprador_email = models.EmailField(blank=True, verbose_name='E-mail do comprador')
    comprador_telefone = models.CharField(max_length=20, blank=True, verbose_name='Telefone do comprador')
    comprador_cpf = models.CharField(max_length=14, blank=True, verbose_name='CPF do comprador')
    
    # Campo para controlar expiração da reserva
    reservado_em = models.DateTimeField(null=True, blank=True, verbose_name='Data da reserva')

    class Meta:
        verbose_name = 'Bilhete'
        verbose_name_plural = 'Bilhetes'
        ordering = ['rifa', 'numero']
        unique_together = ('rifa', 'numero')

    def save(self, *args, **kwargs):
        # Definir data de reserva quando status muda para 'reservado'
        if self.status == 'reservado' and not self.reservado_em:
            self.reservado_em = timezone.now()
        elif self.status != 'reservado':
            self.reservado_em = None
            
        # Normaliza telefone e CPF antes de salvar
        if self.comprador_telefone:
            self.comprador_telefone = self.comprador_telefone.strip()
        if self.comprador_cpf:
            self.comprador_cpf = self.comprador_cpf.strip().replace('.', '').replace('-', '')
        super().save(*args, **kwargs)

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        # Validação extra para telefone e CPF
        if self.comprador_telefone and len(self.comprador_telefone) < 14:
            from django.core.exceptions import ValidationError
            raise ValidationError({'comprador_telefone': 'Telefone deve estar no formato (99) 99999-9999.'})
        if self.comprador_cpf and len(self.comprador_cpf) != 11:
            from django.core.exceptions import ValidationError
            raise ValidationError({'comprador_cpf': 'CPF deve conter 11 dígitos.'})

    def __str__(self):
        return f"Bilhete {self.numero} - {self.rifa.titulo} [{self.status}]"

    def get_status_display(self):
        return dict(STATUS_CHOICES).get(self.status, self.status)

    def get_comprador(self):
        return self.comprador_nome or self.comprador_email or self.comprador_telefone or self.comprador_cpf or '---'

    def is_reserva_expirada(self):
        """Verifica se a reserva expirou (24 horas)"""
        if self.status != 'reservado' or not self.reservado_em:
            return False
        
        tempo_limite = self.reservado_em + timedelta(hours=24)
        return timezone.now() > tempo_limite
    
    def tempo_restante_reserva(self):
        """Retorna tempo restante da reserva em segundos (ou None se não aplicável)"""
        if self.status != 'reservado' or not self.reservado_em:
            return None
            
        tempo_limite = self.reservado_em + timedelta(hours=24)
        tempo_restante = tempo_limite - timezone.now()
        
        if tempo_restante.total_seconds() <= 0:
            return 0
        return int(tempo_restante.total_seconds())

    @classmethod
    def liberar_reservas_expiradas(cls):
        """Libera automaticamente reservas expiradas"""
        agora = timezone.now()
        limite_expiracao = agora - timedelta(hours=24)
        
        # Encontrar números reservados há mais de 24 horas
        numeros_expirados = cls.objects.filter(
            status='reservado',
            reservado_em__lt=limite_expiracao
        )
        
        # Liberar números expirados
        count = numeros_expirados.count()
        if count > 0:
            numeros_expirados.update(
                status='livre',
                reservado_em=None,
                comprador_nome='',
                comprador_email='',
                comprador_telefone='',
                comprador_cpf=''
            )
        
        return count

    def clean(self):
        from django.core.exceptions import ValidationError
        import re
        # Validação de telefone brasileiro
        if self.comprador_telefone:
            telefone_regex = r'^\(\d{2}\) \d{4,5}-\d{4}$'
            if not re.match(telefone_regex, self.comprador_telefone):
                raise ValidationError({'comprador_telefone': 'Telefone deve estar no formato (99) 99999-9999.'})
        # Validação de CPF
        if self.comprador_cpf:
            cpf = re.sub(r'\D', '', self.comprador_cpf)
            if len(cpf) != 11 or not cpf.isdigit() or cpf == cpf[0]*11:
                raise ValidationError({'comprador_cpf': 'CPF inválido.'})
            def cpf_valido(cpf):
                def calc_digito(cpf, peso):
                    soma = sum(int(d)*p for d, p in zip(cpf, peso))
                    resto = soma % 11
                    return '0' if resto < 2 else str(11-resto)
                d1 = calc_digito(cpf[:9], range(10,1,-1))
                d2 = calc_digito(cpf[:10], range(11,1,-1))
                return cpf[-2:] == d1+d2
            if not cpf_valido(cpf):
                raise ValidationError({'comprador_cpf': 'CPF inválido.'})
        # Nome obrigatório se reservado ou pago
        if self.status in ['reservado', 'pago'] and not self.comprador_nome:
            raise ValidationError({'comprador_nome': 'Nome do comprador é obrigatório para bilhetes reservados ou pagos.'})
        # Feedback visual para admin
        if not self.rifa:
            raise ValidationError({'rifa': 'Selecione uma rifa válida.'})


class Pedido(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('pago', 'Pago'),
        ('expirado', 'Expirado'),
        ('cancelado', 'Cancelado'),
    ]
    user = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    rifa = models.ForeignKey(Rifa, on_delete=models.CASCADE, related_name='pedidos')
    quantidade = models.PositiveIntegerField()
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    numeros_reservados = models.TextField(blank=True, help_text='Lista de números reservados separados por vírgula.')
    cpf = models.CharField(max_length=14)
    nome = models.CharField(max_length=150)
    telefone = models.CharField(max_length=20, blank=True)
    pix_codigo = models.TextField(blank=True)
    pix_txid = models.CharField(max_length=35, blank=True)
    # MercadoPago payment id (para rastrear o pagamento no provedor)
    mercado_pago_payment_id = models.CharField(max_length=80, blank=True, null=True)
    # Armazena QR Code em base64 retornado pelo MercadoPago (imagem)
    pix_qr_base64 = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendente')
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Pedido #{self.id} - {self.rifa.titulo} ({self.status})"

    def expirado(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at and self.status == 'pendente'


class PremioBilhete(models.Model):
    rifa = models.ForeignKey(Rifa, on_delete=models.CASCADE, related_name='premios')
    numero_premiado = models.PositiveIntegerField(help_text='Número específico que concede o prêmio ao comprador.')
    valor_premio = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    descricao = models.CharField(max_length=120, blank=True)
    ativo = models.BooleanField(default=True, help_text='Se desativado, não será mais concedido.')
    ganho_por = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='premios_ganhos')
    pedido = models.ForeignKey(Pedido, null=True, blank=True, on_delete=models.SET_NULL, related_name='premios_vinculados')
    ganho_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('rifa', 'numero_premiado')
        ordering = ['rifa', 'numero_premiado']

    def __str__(self):
        status = 'GANHO' if self.ganho_por else 'ATIVO' if self.ativo else 'INATIVO'
        return f"Premio #{self.numero_premiado} ({status}) - {self.rifa.titulo}"