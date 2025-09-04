from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from .models import Rifa, Numero, NumeroRifa
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.conf import settings
import mercadopago
import json
import logging

logger = logging.getLogger(__name__)

# View protegida para sortear rifa pelo painel do site
@login_required
def sortear_rifa(request, rifa_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Apenas o administrador pode sortear a rifa.')
    rifa = get_object_or_404(Rifa, id=rifa_id)
    if rifa.encerrada:
        messages.warning(request, 'Esta rifa já está encerrada.')
        return redirect('raffle-detail', raffle_id=rifa.id)
    bilhetes = Numero.objects.filter(rifa=rifa, status='pago')
    if not bilhetes.exists():
        messages.warning(request, 'Nenhum bilhete pago para esta rifa.')
        return redirect('raffle-detail', raffle_id=rifa.id)
    import random
    sorteado = random.choice(list(bilhetes))
    user = getattr(sorteado, 'reservado_por', None)
    rifa.ganhador_nome = user.get_full_name() if user and user.get_full_name() else (user.username if user else sorteado.comprador_nome)
    rifa.ganhador_numero = sorteado.numero
    if user and hasattr(user, 'profile') and hasattr(user.profile, 'foto') and user.profile.foto:
        rifa.ganhador_foto = user.profile.foto
    rifa.encerrada = True
    rifa.save()
    # Enviar e-mail (opcional)
    email = user.email if user else sorteado.comprador_email
    if email:
        from django.template.loader import render_to_string
        from django.core.mail import send_mail
        html_message = render_to_string('emails/ganhador_rifa.html', {
            'nome_ganhador': rifa.ganhador_nome,
            'titulo_rifa': rifa.titulo,
            'numero_bilhete': rifa.ganhador_numero,
            'valor_premio': rifa.preco,
        })
        send_mail(
            '🎉 Parabéns! Seu bilhete foi sorteado. Receba o seu prêmio.',
            '',
            'Pantanal da Sorte <noreply@rifa.com>',
            [email],
            fail_silently=True,
            html_message=html_message
        )
    messages.success(request, f'Ganhador sorteado "{rifa.titulo}"!')
    return redirect('raffle-detail', raffle_id=rifa.id)
# --- IMPORTS ---
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from .models import Rifa, Numero, NumeroRifa
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
# models_profile defines UserProfile; import it and alias to Perfil so existing code continues to work
from .models_profile import UserProfile as Perfil
from django.contrib.auth import login


def meus_numeros(request):
    return render(request, 'rifa/meus_numeros.html')
# --- VIEWS ---
def meus_numeros(request):
    return render(request, 'rifa/meus_numeros.html')

def ganhadores(request):
    rifas_encerradas = Rifa.objects.filter(encerrada=True).order_by('-data_encerramento')
    return render(request, 'rifa/ganhadores.html', {'rifas_encerradas': rifas_encerradas})

@login_required
def sorteio_detail(request, id):
    rifa = get_object_or_404(Rifa, id=id)
    qtde_list = ['10', '20', '50', '100', '200', '500']  # Sugestão de quantidades para compra
    numeros_list = Numero.objects.filter(rifa=rifa).order_by('numero')
    return render(request, 'rifa/raffle_detail.html', {
        'rifa': rifa,
        'qtde_list': qtde_list,
        'numeros_list': numeros_list
    })

def login_view(request):
    if request.method == 'POST':
        # Copia os dados do POST para podermos normalizar o campo 'username'
        post = request.POST.copy()
        raw_user = post.get('username', '').strip()
        import re
        digits = re.sub(r'\D', '', raw_user)
        # Se o usuário digitou um CPF (formatado ou não), tenta usar os dígitos como username
        if len(digits) == 11 and User.objects.filter(username=digits).exists():
            post['username'] = digits
        else:
            # Se não for CPF, tenta localizar por e-mail (login via e-mail)
            try:
                user_by_email = User.objects.filter(email__iexact=raw_user).first()
                if user_by_email:
                    post['username'] = user_by_email.username
            except Exception:
                pass

        form = AuthenticationForm(request, data=post)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'rifa/login.html', {'form': form})

def cadastro(request):
    if request.method == 'POST':
        nome = request.POST['nomeCompleto']
        social = request.POST.get('nomeSocial', '')
        cpf = request.POST['cpf']
        data = request.POST['dataNascimento']
        email = request.POST['email']
        senha = request.POST['senha']
        senha2 = request.POST['senha2']

        if senha != senha2:
            messages.error(request, "As senhas não coincidem.")
            return redirect('cadastro')

        # Normaliza CPF para salvar no perfil
        import re
        cpf_digits = re.sub(r'\D','', cpf)
        cpf_formatted = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}" if len(cpf_digits)==11 else cpf

        # Verifica se o CPF já existe em UserProfile (tanto formatado quanto somente dígitos)
        from rifa.models_profile import UserProfile as _UP
        exists_profile = _UP.objects.filter(cpf__in=[cpf_formatted, cpf_digits]).first()
        if not exists_profile:
            # fallback: varredura para normalizar possíveis formatos diferentes
            for p in _UP.objects.all():
                if re.sub(r'\D','', p.cpf or '') == cpf_digits:
                    exists_profile = p
                    break
        if exists_profile:
            messages.error(request, "CPF já cadastrado.")
            return redirect('cadastro')

        # Usa nomeSocial como username (sanitiza e garante unicidade). Nunca usar CPF como username.
        raw_username = (social or '').strip()
        if not raw_username:
            # fallback: usar primeiro nome ou parte do email
            if nome:
                raw_username = nome.split()[0]
            else:
                raw_username = (email.split('@',1)[0] if email else 'user')

        # sanitize: permitir apenas chars suportados por Django username (@ . + - _ e alfanum)
        username_base = re.sub(r"[^A-Za-z0-9@.\+\-_]", '_', raw_username)[:140]
        username = username_base
        suffix = 0
        while User.objects.filter(username=username).exists():
            suffix += 1
            tail = str(suffix)
            allowed_len = 150 - len(tail)
            username = (username_base[:allowed_len] + tail)

        # cria usuário com username derivado de nomeSocial (NUNCA CPF) e salva perfil com CPF formatado
        user = User.objects.create_user(username=username, email=email, password=senha, first_name=nome)
        Perfil.objects.create(user=user, cpf=cpf_formatted, nome_social=social, data_nascimento=data)

        login(request, user)  # loga automaticamente
        messages.success(request, "Cadastro realizado com sucesso!")
        return redirect('home')

    return render(request, 'rifa/cadastro.html')

@login_required
def premios(request):
    rifas = Rifa.objects.all()
    return render(request, 'rifa/premios.html', {'rifas': rifas})

def home(request):
    rifas = Rifa.objects.all()
    return render(request, 'rifa/home.html', {'rifas': rifas, 'user': request.user})
# View para busca de pedidos por telefone
@csrf_exempt
def buscar_pedidos(request):
    if request.method == 'POST':
        telefone = request.POST.get('telefone', '').strip()
        cpf = request.POST.get('cpf', '').strip().replace('.', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
        
        numeros = []
        
        if telefone:
            # Remove formatação do telefone para busca mais flexível
            telefone_limpo = telefone.replace('(', '').replace(')', '').replace(' ', '').replace('-', '')
            numeros = Numero.objects.filter(comprador_telefone__icontains=telefone_limpo).select_related('rifa')
        elif cpf and len(cpf) == 11 and cpf.isdigit():
            numeros = Numero.objects.filter(comprador_cpf=cpf).select_related('rifa')
        
        if numeros:
            # Retorna informações mais detalhadas dos números
            numeros_data = []
            for numero in numeros:
                numeros_data.append({
                    'numero': numero.numero,
                    'rifa_titulo': numero.rifa.titulo if numero.rifa else 'Sem título',
                    'status': numero.get_status_display(),
                    'comprador_nome': numero.comprador_nome or 'Não informado'
                })
            return JsonResponse({'status': 'success', 'numeros': numeros_data})
        else:
            return JsonResponse({'status': 'not_found', 'message': 'Nenhum número encontrado neste telefone.'})

    return JsonResponse({'status': 'error', 'message': 'Método inválido ou dados não fornecidos.'})

def sorteios(request):
    rifas = Rifa.objects.all()
    return render(request, 'rifa/sorteios.html', {'rifas': rifas})

# View para busca de números pelo telefone
@csrf_exempt
def buscar_numeros_por_telefone(request):
    if request.method == 'POST':
        telefone = request.POST.get('telefone', '').strip()
        cpf = request.POST.get('cpf', '').strip().replace('.', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
        
        numeros = []
        
        if telefone:
            # Remove formatação do telefone para busca mais flexível
            telefone_limpo = telefone.replace('(', '').replace(')', '').replace(' ', '').replace('-', '')
            numeros = Numero.objects.filter(comprador_telefone__icontains=telefone_limpo).select_related('rifa')
        elif cpf and len(cpf) == 11 and cpf.isdigit():
            numeros = Numero.objects.filter(comprador_cpf=cpf).select_related('rifa')
        
        if numeros:
            # Retorna informações mais detalhadas dos números
            numeros_data = []
            for numero in numeros:
                numeros_data.append({
                    'numero': numero.numero,
                    'rifa_titulo': numero.rifa.titulo if numero.rifa else 'Sem título',
                    'status': numero.get_status_display(),
                    'comprador_nome': numero.comprador_nome or 'Não informado'
                })
            return JsonResponse({'status': 'success', 'numeros': numeros_data})
        else:
            return JsonResponse({'status': 'not_found', 'message': 'Nenhum número encontrado neste telefone.'})

    return JsonResponse({'status': 'error', 'message': 'Método inválido ou dados não fornecidos.'})

def raffle_detail(request, raffle_id):
    rifa = get_object_or_404(Rifa, id=raffle_id)
    qtde_list = ['10', '20', '50', '100', '200', '500']  # Sugestão de quantidades para compra
    numeros_list = Numero.objects.filter(rifa=rifa).order_by('numero')
    if request.method == 'POST':
        numero_id = request.POST.get('numero')
        numero_obj = get_object_or_404(Numero, id=numero_id, rifa=rifa)
        if numero_obj.status == 'livre':
            numero_obj.status = 'reservado'
            from django.utils import timezone
            numero_obj.save()
            messages.success(request, f'Número {numero_obj.numero} reservado com sucesso!')
        else:
            messages.error(request, f'O número {numero_obj.numero} já está reservado.')
        return redirect('raffle-detail', raffle_id=rifa.id)
    return render(request, 'rifa/raffle_detail.html', {
        'rifa': rifa,
        'qtde_list': qtde_list,
        'numeros_list': numeros_list,
        'user': request.user
    })

@login_required
def reservar_numero(request, raffle_id, number_id):
    rifa = get_object_or_404(Rifa, id=raffle_id)
    from .models import Numero
    numero_obj = Numero.objects.filter(rifa=rifa, id=number_id).first()
    if not numero_obj:
        # Cria novo bilhete se não existir
        numero_obj = Numero.objects.create(rifa=rifa, numero=number_id, status='livre')

    if request.method == 'POST':
        if numero_obj.status == 'livre':
            numero_obj.status = 'reservado'
            numero_obj.save()
            messages.success(request, 'Número reservado com sucesso! Envie o pagamento via Pix e aguarde confirmação.')
        else:
            messages.error(request, 'Este número já foi reservado.')
        return redirect('raffle_detail', raffle_id=rifa.id)

    # GET: exibe formulário simples para reservar
    return render(request, 'rifa/reservar_numero.html', {'raffle': rifa, 'numero': numero_obj, 'user': request.user})

@login_required
def criar_rifa(request):
    """View para administradores criarem rifas pelo painel do site"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Apenas administradores podem criar rifas.')
        return redirect('sorteios')
    
    if request.method == 'POST':
        try:
            # Criar nova rifa com os dados do formulário
            rifa = Rifa()
            rifa.titulo = request.POST.get('titulo')
            rifa.descricao = request.POST.get('descricao', '')
            rifa.preco = float(request.POST.get('preco', 0))
            rifa.quantidade_numeros = int(request.POST.get('quantidade_numeros', 100))
            
            # Data de encerramento (opcional)
            data_encerramento = request.POST.get('data_encerramento')
            if data_encerramento:
                from django.utils import timezone
                import datetime
                rifa.data_encerramento = timezone.make_aware(
                    datetime.datetime.fromisoformat(data_encerramento)
                )
            
            # Status da rifa
            rifa.encerrada = 'encerrada' in request.POST
            
            # Upload de imagem
            if 'imagem' in request.FILES:
                rifa.imagem = request.FILES['imagem']
            
            rifa.save()
            
            # Criar os números da rifa automaticamente
            from .models import Numero
            for numero in range(1, rifa.quantidade_numeros + 1):
                Numero.objects.create(
                    rifa=rifa,
                    numero=numero,
                    status='livre'
                )
            
            messages.success(request, f'Rifa "{rifa.titulo}" criada com sucesso! {rifa.quantidade_numeros} números gerados.')
            
            # Redirecionamento com parâmetro para evitar reenvio do formulário
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            return HttpResponseRedirect(reverse('sorteios') + '?created=1')
            
        except Exception as e:
            messages.error(request, f'Erro ao criar rifa: {str(e)}')
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            return HttpResponseRedirect(reverse('sorteios') + '?error=1')
    
    # Se não for POST, redireciona para sorteios
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    return HttpResponseRedirect(reverse('sorteios'))

@login_required
def editar_rifa(request, rifa_id):
    """View para administradores editarem rifas"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Apenas administradores podem editar rifas.')
        return redirect('sorteios')
    
    rifa = get_object_or_404(Rifa, id=rifa_id)
    
    if request.method == 'POST':
        try:
            # Atualizar dados da rifa
            rifa.titulo = request.POST.get('titulo', rifa.titulo)
            rifa.descricao = request.POST.get('descricao', rifa.descricao)
            rifa.preco = float(request.POST.get('preco', rifa.preco))
            
            # Data de encerramento (opcional)
            data_encerramento = request.POST.get('data_encerramento')
            if data_encerramento:
                from django.utils import timezone
                import datetime
                rifa.data_encerramento = timezone.make_aware(
                    datetime.datetime.fromisoformat(data_encerramento)
                )
            else:
                rifa.data_encerramento = None
            
            # Status da rifa
            rifa.encerrada = 'encerrada' in request.POST
            
            # Upload de nova imagem (opcional)
            if 'imagem' in request.FILES:
                rifa.imagem = request.FILES['imagem']
            
            rifa.save()
            
            messages.success(request, f'Rifa "{rifa.titulo}" editada com sucesso!')
            
            # Redirecionamento com parâmetro para evitar reenvio
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            return HttpResponseRedirect(reverse('sorteios') + '?edited=1')
            
        except Exception as e:
            messages.error(request, f'Erro ao editar rifa: {str(e)}')
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            return HttpResponseRedirect(reverse('sorteios') + '?error=1')
    
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    return HttpResponseRedirect(reverse('sorteios'))

@login_required
def excluir_rifa(request, rifa_id):
    """View para administradores excluírem rifas"""
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Permissão negada'}, status=403)
    
    if request.method == 'POST':
        try:
            rifa = get_object_or_404(Rifa, id=rifa_id)
            titulo = rifa.titulo
            
            # Excluir todos os números relacionados
            from .models import Numero
            Numero.objects.filter(rifa=rifa).delete()
            
            # Excluir a rifa
            rifa.delete()
            
            return JsonResponse({
                'success': True, 
                'message': f'Rifa "{titulo}" excluída com sucesso!',
                'redirect': True
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Erro ao excluir rifa: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Método não permitido'}, status=405)

@login_required
def api_rifa_detail(request, rifa_id):
    """API para obter dados de uma rifa (para edição)"""
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Permissão negada'}, status=403)
    
    try:
        rifa = get_object_or_404(Rifa, id=rifa_id)
        
        # Contar números vendidos
        numeros_vendidos = Numero.objects.filter(
            rifa=rifa, 
            status='pago'
        ).count()
        
        data = {
            'id': rifa.id,
            'titulo': rifa.titulo,
            'descricao': rifa.descricao,
            'preco': float(rifa.preco),
            'quantidade_numeros': rifa.quantidade_numeros,
            'encerrada': rifa.encerrada,
            'data_encerramento': rifa.data_encerramento.isoformat() if rifa.data_encerramento else None,
            'numeros_vendidos': numeros_vendidos,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def api_usuario_por_cpf(request):
    """Busca usuário pelo CPF e retorna dados mascarados.
    GET cpf=000.000.000-00 ou somente dígitos.
    Retorno: {found:bool, nome, email, telefone}
    """
    cpf_raw = (request.GET.get('cpf') or '').strip()
    import re
    digits = re.sub(r'\D','', cpf_raw)
    if len(digits) != 11:
        return JsonResponse({'found': False, 'message': 'CPF inválido.'}, status=400)
    formatted = f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    try:
        from rifa.models_profile import UserProfile
        from django.db.models import Q
        profile = UserProfile.objects.select_related('user').filter(Q(cpf=formatted)|Q(cpf=digits)).first()
        if not profile:
            # fallback normalizando tudo
            for p in UserProfile.objects.select_related('user').all():
                if re.sub(r'\D','', p.cpf or '') == digits:
                    profile = p; break
        if not profile:
            return JsonResponse({'found': False, 'message': 'Não existe conta cadastrada neste CPF.'})
        user = profile.user
        nome = (user.first_name or '').strip() or user.username
        email = (user.email or '').strip()
        telefone = (getattr(profile,'telefone','') or '').strip()
        def mask_email(e):
            if not e or '@' not in e: return ''
            u,d = e.split('@',1)
            return (u[0] + '*'*(len(u)-1)) + '@' + d if len(u)>1 else '*'+'@'+d
        def mask_phone(p):
            if not p: return ''
            digs = re.sub(r'\D','', p)
            if len(digs) <= 7: return digs
            return digs[:4] + '*'*(len(digs)-7) + digs[-3:]
        return JsonResponse({
            'found': True,
            'nome': nome,
            'email': mask_email(email),
            'telefone': mask_phone(telefone)
        })
    except Exception:
        return JsonResponse({'found': False, 'message': 'Erro ao buscar CPF.'}, status=500)

from django.utils import timezone
from django.db import transaction
import uuid, decimal, re, random
from .models import Pedido, PremioBilhete
@csrf_exempt
def criar_pedido(request):
    """Cria pedido reservando bilhetes aleatórios.
    POST: rifa_id, cpf, quantidade
    Retorna: {success, pedido_id, redirect, premios_ganhos:[{numero,valor}]}
    """
    if request.method != 'POST':
        return JsonResponse({'error':'Método inválido'}, status=405)
    try:
        rifa_id = request.POST.get('rifa_id')
        cpf_raw = (request.POST.get('cpf') or '').strip()
        qtd = int(request.POST.get('quantidade','0'))
        if qtd <= 0:
            return JsonResponse({'error':'Quantidade inválida'}, status=400)
        rifa = get_object_or_404(Rifa, id=rifa_id)
        # Sanitiza CPF
        digits = re.sub(r'\D','', cpf_raw)
        if len(digits) != 11:
            return JsonResponse({'error':'CPF inválido'}, status=400)
        cpf_fmt = f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
        # Localiza usuário pelo CPF (UserProfile)
        from rifa.models_profile import UserProfile
        profile = UserProfile.objects.select_related('user').filter(cpf__in=[cpf_fmt, digits]).first()
        if not profile:
            # varredura fallback
            for p in UserProfile.objects.select_related('user').all():
                if re.sub(r'\D','', p.cpf or '') == digits:
                    profile = p; break
        if not profile:
            return JsonResponse({'error':'CPF não cadastrado'}, status=400)
        user = profile.user
        preco = decimal.Decimal(rifa.preco)
        total_max = rifa.quantidade_numeros
        if total_max <= 0:
            return JsonResponse({'error':'Rifa sem limite de números configurado.'}, status=400)
        with transaction.atomic():
            # Conjunto de ocupados (reservado, pago ou já atribuído livremente a outro pedido em andamento)
            ocupados = set(Numero.objects.select_for_update(skip_locked=True)
                           .filter(rifa=rifa)
                           .exclude(status='livre')
                           .values_list('numero', flat=True))
            # Inclui os livres existentes (podem ser reutilizados se ainda livres)
            livres_existentes = {n.numero: n for n in Numero.objects.filter(rifa=rifa, status='livre')}
            disponiveis = [n for n in range(1, total_max+1) if n not in ocupados]
            if len(disponiveis) < qtd:
                return JsonResponse({'error':'Não há bilhetes suficientes disponíveis.'}, status=400)
            escolhidos = random.sample(disponiveis, qtd)
            objetos = []
            for numero in escolhidos:
                obj = livres_existentes.get(numero)
                if not obj:
                    obj = Numero(rifa=rifa, numero=numero, status='livre')
                    obj.save()
                objetos.append(obj)
            numeros_reservados = []
            for bilhete in objetos:
                bilhete.status='reservado'
                bilhete.comprador_nome = user.first_name or user.username
                bilhete.comprador_email = user.email
                bilhete.comprador_cpf = digits
                bilhete.comprador_telefone = getattr(profile, 'telefone', '')
                bilhete.save()
                numeros_reservados.append(str(bilhete.numero))
        valor_total = preco * qtd
        txid = uuid.uuid4().hex[:25]
        # Payload PIX simples placeholder (pode ser substituído por geração EMV se quiser depois)
        pix_codigo = f"TXID:{txid}|RIFA:{rifa.id}|TOTAL:{valor_total:.2f}"
        pedido = Pedido.objects.create(
            user=user,
            rifa=rifa,
            quantidade=qtd,
            valor_unitario=preco,
            valor_total=valor_total,
            numeros_reservados=','.join(numeros_reservados),
            cpf=cpf_fmt,
            nome=user.first_name or user.username,
            telefone=getattr(profile,'telefone',''),
            pix_codigo=pix_codigo,
            pix_txid=txid,
            expires_at=timezone.now()+timezone.timedelta(hours=1)
        )
        # Tentar criar pagamento PIX no provedor e salvar QR/código retornados
        try:
            from .mercadopago_service import criar_pagamento_pix
            mp_resp = criar_pagamento_pix(float(valor_total), payer_email=user.email if user.email else None, external_reference=str(pedido.id), description=f'Rifa {rifa.id} - Pedido {pedido.id}')
            # Extrai id e point_of_interaction
            if isinstance(mp_resp, dict):
                mp_id = mp_resp.get('id') or (mp_resp.get('response') or {}).get('id')
                if mp_id:
                    pedido.mercado_pago_payment_id = str(mp_id)
                # tenta extrair qr base64
                poi = (mp_resp.get('point_of_interaction') or (mp_resp.get('response') or {}).get('point_of_interaction') or {})
                tx = (poi.get('transaction_data') or {}) if isinstance(poi, dict) else {}
                qr_base64 = tx.get('qr_code_base64') or None
                qr_text = tx.get('qr_code') or None
                if qr_base64:
                    pedido.pix_qr_base64 = qr_base64
                if qr_text and not pedido.pix_qr_base64:
                    # quando só temos texto do QR, também salvamos no pix_codigo para exibir
                    pedido.pix_codigo = qr_text
                # atualiza pix_txid/mercado id
                try:
                    pedido.save(update_fields=['mercado_pago_payment_id','pix_qr_base64','pix_codigo','pix_txid'])
                except Exception:
                    pedido.save()
        except Exception as e:
            logger.exception('Não foi possível criar pagamento PIX automático: %s', e)
        # Checa prêmios ganhos
        numeros_int = [int(x) for x in numeros_reservados]
        premios_ativos = PremioBilhete.objects.filter(rifa=rifa, ativo=True, ganho_por__isnull=True, numero_premiado__in=numeros_int)
        premios_ganhos = []
        if premios_ativos.exists():
            for premio in premios_ativos:
                premio.ganho_por = user
                premio.pedido = pedido
                premio.ganho_em = timezone.now()
                premio.save(update_fields=['ganho_por','pedido','ganho_em'])
                premios_ganhos.append({'numero':premio.numero_premiado,'valor':float(premio.valor_premio)})
        return JsonResponse({'success':True,'pedido_id':pedido.id,'redirect':f"/pedido/{pedido.id}/pix/",'premios_ganhos':premios_ganhos})
    except Exception as e:
        return JsonResponse({'error':str(e)}, status=500)

def pedido_pix(request, pedido_id):
    try:
        pedido = get_object_or_404(Pedido, id=pedido_id)
        if pedido.expirado():
            pedido.status = 'expirado'
            pedido.save(update_fields=['status'])
        # passa dados de QR / PIX já gerados (se existirem)
        pix_qr_base64 = getattr(pedido, 'pix_qr_base64', None)
        pix_codigo = getattr(pedido, 'pix_codigo', None)
        mercado_pago_payment_id = getattr(pedido, 'mercado_pago_payment_id', None)
        return render(request, 'rifa/pedido_pix.html', {
            'pedido': pedido,
            'pix_qr_base64': pix_qr_base64,
            'pix_codigo': pix_codigo,
            'mercado_pago_payment_id': mercado_pago_payment_id,
        })
    except Exception as e:
        # Log and return a simple error page to avoid blank screen
        logger.exception('Erro ao renderizar pedido_pix: %s', e)
        from django.http import HttpResponse
        if getattr(settings, 'DEBUG', False):
            return HttpResponse(f'<h1>Erro ao abrir pedido #{pedido_id}</h1><pre>{str(e)}</pre>', status=500)
        return HttpResponse('<h1>Erro ao abrir pedido</h1>', status=500)


@csrf_exempt
def gerar_qr_code(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido. Use POST.'}, status=405)

    try:
        try:
            data = json.loads(request.body.decode('utf-8') or '{}')
        except Exception:
            data = request.POST.dict()

        pedido_id = data.get('pedido_id') or data.get('order_id')

        # se pedido_id fornecido, usar valor do pedido
        amount = float(data.get('amount', 0) or 0)
        description = data.get('description', 'Pagamento de Rifa')
        if pedido_id:
            pedido = get_object_or_404(Pedido, id=pedido_id)
            amount = float(pedido.valor_total)
            description = f'Rifa #{pedido.rifa.id} - Pedido {pedido.id}'

            # Se já existe QR salvo no pedido, retorna imediatamente
            existing_qr = getattr(pedido, 'pix_qr_base64', None)
            if existing_qr:
                return JsonResponse({
                    "success": True,
                    "payment_id": getattr(pedido, 'mercado_pago_payment_id', None),
                    "qr_code_base64": existing_qr,
                    "status": pedido.status,
                    "pix_codigo": getattr(pedido, 'pix_codigo', None),
                })

        try:
            sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        except Exception as e:
            # SDK não disponível ou token inválido; retorna erro amigável
            logger.exception('SDK MercadoPago indisponível: %s', e)
            # Se temos pedido, devolve o pix_codigo para que a UI exiba algo útil
            if pedido_id:
                try:
                    pedido = Pedido.objects.filter(id=int(pedido_id)).first()
                    return JsonResponse({
                        'success': False,
                        'error': 'SDK MercadoPago indisponível',
                        'pix_codigo': getattr(pedido, 'pix_codigo', None)
                    }, status=502)
                except Exception:
                    pass
            return JsonResponse({'success': False, 'error': 'SDK MercadoPago indisponível'}, status=502)

        payment_data = {
            "transaction_amount": amount or 0.0,
            "description": description,
            "payment_method_id": "pix",
            "payer": {
                "email": (getattr(request.user, 'email', None) if request.user and request.user.is_authenticated else None) or data.get('email') or 'test_user_123456@testuser.com'
            }
        }

        if pedido_id:
            payment_data['external_reference'] = str(pedido.id)

        payment_response = sdk.payment().create(payment_data)
        # o SDK retorna dict com chave 'response'
        payment = None
        if isinstance(payment_response, dict):
            payment = payment_response.get('response') or payment_response.get('result') or payment_response
        else:
            payment = payment_response

        if not payment or not isinstance(payment, dict) or 'id' not in payment:
            return JsonResponse({'error': 'Resposta inválida do provedor de pagamento', 'detail': payment_response}, status=502)

        # extrai dados do point_of_interaction
        poi = payment.get('point_of_interaction') or {}
        tx = poi.get('transaction_data') or {}
        qr_code = tx.get('qr_code')
        qr_code_base64 = tx.get('qr_code_base64')
        payment_id = payment.get('id')

        # persiste no pedido se houver
        if pedido_id:
            try:
                pedido_obj = Pedido.objects.filter(id=int(pedido_id)).first()
                if pedido_obj:
                    pedido_obj.mercado_pago_payment_id = str(payment_id)
                    if qr_code_base64:
                        pedido_obj.pix_qr_base64 = qr_code_base64
                    # tenta salvar id como txid também para compatibilidade
                    pedido_obj.pix_txid = str(payment_id)
                    pedido_obj.save()
            except Exception:
                logger.exception('Erro ao salvar pagamento no Pedido %s', pedido_id)

        return JsonResponse({
            "success": True,
            "payment_id": payment_id,
            "qr_code": qr_code,
            "qr_code_base64": qr_code_base64,
            "status": payment.get('status'),
            "payment": payment,
        })
    except Exception as e:
        logger.exception('Erro ao gerar QR via MercadoPago: %s', e)
        return JsonResponse({'error': 'Erro interno', 'details': str(e)}, status=500)


@csrf_exempt
def pagamento_webhook(request):
    """Endpoint para receber notificações do MercadoPago (webhook).

    O MercadoPago envia um JSON com referência ao recurso alterado.
    Este handler tenta extrair o payment_id do payload, recuperar os dados
    do pagamento via SDK e atualizar o Pedido correspondente (usando
    external_reference quando disponível).
    """
    try:
        raw = request.body.decode('utf-8') or ''
        logger.info('Webhook recebido: %s', raw)
        # Tenta parsear JSON
        payload = {}
        try:
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {}

        # Extração comum: {"type":"payment","data":{"id": 123456789}}
        payment_id = None
        if isinstance(payload, dict):
            # v1/v2 compatibility
            data = payload.get('data') or payload.get('resource') or {}
            if isinstance(data, dict):
                payment_id = data.get('id') or data.get('payment', {}).get('id')
            # sometimes payload itself has an 'id'
            if not payment_id:
                payment_id = payload.get('id')

        if not payment_id:
            # Não conseguimos extrair payment id; apenas acknowledge
            return JsonResponse({'status': 'ok', 'message': 'no_payment_id'})

        # Se não há credencial configurada, não tentamos buscar
        if not getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None):
            logger.error('MERCADOPAGO_ACCESS_TOKEN ausente ao processar webhook')
            return JsonResponse({'status': 'error', 'message': 'gateway_not_configured'}, status=500)

        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        mp_resp = sdk.payment().get(payment_id)
        result = mp_resp.get('response') if isinstance(mp_resp, dict) else mp_resp

        # Extrai possível external_reference para localizar Pedido
        external_ref = None
        if isinstance(result, dict):
            external_ref = result.get('external_reference') or (result.get('metadata') or {}).get('order_id')
            status = result.get('status')
            # tenta também pegar qr_code_base64
            poi = result.get('point_of_interaction') or {}
            tx_data = poi.get('transaction_data') if isinstance(poi, dict) else None
            qr_code_base64 = tx_data.get('qr_code_base64') if tx_data else None
        else:
            status = None
            qr_code_base64 = None

        # Se encontramos external_reference, atualiza Pedido
        if external_ref:
            try:
                pedido = Pedido.objects.filter(id=int(external_ref)).first()
            except Exception:
                pedido = None

            if pedido:
                # Marca como pago se status indica aprovação
                if status and status.lower() in ['approved','paid']:
                    pedido.status = 'pago'
                # Salva qr_code_base64 em campo
                if qr_code_base64:
                    pedido.pix_qr_base64 = qr_code_base64
                # Armazena payment id no pedido para rastrear (campo mercado_pago_payment_id)
                try:
                    mp_id = result.get('id')
                    if mp_id:
                        pedido.mercado_pago_payment_id = str(mp_id)
                except Exception:
                    pass
                # Tenta salvar txid também
                try:
                    pedido.pix_txid = result.get('id') or pedido.pix_txid
                except Exception:
                    pass
                pedido.save()

        return JsonResponse({'status': 'ok'})

    except Exception as e:
        logger.exception('Erro no processamento do webhook: %s', e)
        return JsonResponse({'status': 'error', 'details': str(e)}, status=500)


def mostrar_qr(request, pedido_id):
    """Renderiza um template simples mostrando o QR Code em base64.

    Espera encontrar o campo `qr_code_base64` no Pedido (caso você salve),
    ou via querystring (?qr_code_base64=...)
    """
    pedido = get_object_or_404(Pedido, id=pedido_id)

    # Preferência: qr_code armazenado no pedido (campo pix_qr_base64 ou similar)
    qr_code_base64 = getattr(pedido, 'pix_qr_base64', None)

    # Fallback: aceitar via query param (útil para testes)
    if not qr_code_base64:
        qr_code_base64 = request.GET.get('qr_code_base64')

    return render(request, 'rifa/mostrar_qr.html', {'pedido': pedido, 'qr_code_base64': qr_code_base64})

def api_premios_rifa(request, rifa_id):
    rifa = get_object_or_404(Rifa, id=rifa_id)
    premios = [{
        'numero': p.numero_premiado,
        'valor': float(p.valor_premio),
        'ganho': bool(p.ganho_por),
    } for p in rifa.premios.all().order_by('numero_premiado')]
    return JsonResponse({'premios': premios})

@login_required
@csrf_exempt
def excluir_premio(request, rifa_id, premio_id):
    if request.method not in ['POST','DELETE']:
        return JsonResponse({'error':'Método não permitido'}, status=405)
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error':'Sem permissão'}, status=403)
    premio = get_object_or_404(PremioBilhete, id=premio_id, rifa_id=rifa_id)
    if premio.ganho_por:
        return JsonResponse({'error':'Já ganho; não pode excluir.'}, status=400)
    premio.delete()
    rifa = get_object_or_404(Rifa, id=rifa_id)
    premios = [{
        'id': p.id,
        'numero': p.numero_premiado,
        'valor': str(p.valor_premio),
        'ativo': p.ativo,
        'ganho_por': p.ganho_por.username if p.ganho_por else None
    } for p in rifa.premios.all().order_by('numero_premiado')]
    return JsonResponse({'success':True,'premios':premios})

@login_required
@csrf_exempt
def definir_premio(request, rifa_id):
    rifa = get_object_or_404(Rifa, id=rifa_id)
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error':'Sem permissão'}, status=403)
    if request.method != 'POST':
        premios = [{
            'id': p.id,
            'numero': p.numero_premiado,
            'valor': str(p.valor_premio),
            'ativo': p.ativo,
            'ganho_por': p.ganho_por.username if p.ganho_por else None
        } for p in rifa.premios.all()]
        return JsonResponse({'premios': premios})
    try:
        numero = int(request.POST.get('numero_premiado',''))
        if numero <=0:
            return JsonResponse({'error':'Número inválido'}, status=400)
        from decimal import Decimal
        valor_raw = (request.POST.get('valor_premio') or '').strip().replace(',','.')
        if not valor_raw:
            return JsonResponse({'error':'Valor obrigatório'}, status=400)
        valor = Decimal(valor_raw)
        premio, created = PremioBilhete.objects.get_or_create(rifa=rifa, numero_premiado=numero, defaults={'valor_premio':valor})
        if not created:
            if premio.ganho_por:
                return JsonResponse({'error':'Já ganho; não altera.'}, status=400)
            premio.valor_premio = valor
            premio.ativo = True
            premio.save(update_fields=['valor_premio','ativo'])
        premios = [{
            'id': p.id,
            'numero': p.numero_premiado,
            'valor': str(p.valor_premio),
            'ativo': p.ativo,
            'ganho_por': p.ganho_por.username if p.ganho_por else None
        } for p in rifa.premios.all().order_by('numero_premiado')]
        return JsonResponse({'success':True,'id':premio.id,'created':created,'premios':premios})
    except Exception as e:
        return JsonResponse({'error':str(e)}, status=500)


@login_required
def sortear_rifa_ajax(request, rifa_id):
    """Função para sortear uma rifa via AJAX"""
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Permissão negada'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    try:
        import random
        from django.template.loader import render_to_string
        from django.core.mail import send_mail
        
        rifa = get_object_or_404(Rifa, id=rifa_id)
        
        # Verificar se a rifa já está encerrada
        if rifa.encerrada:
            return JsonResponse({
                'success': False,
                'message': 'Esta rifa já está encerrada.'
            })
        
        # Buscar números vendidos (status 'pago') apenas desta rifa específica
        numeros_vendidos = Numero.objects.filter(
            rifa=rifa, 
            status='pago'
        )
        
        if not numeros_vendidos.exists():
            return JsonResponse({
                'success': False,
                'message': 'Nenhum número foi vendido para esta rifa ainda.'
            })
        
        # Realizar o sorteio - escolher um número aleatório entre os vendidos
        numero_sorteado = random.choice(list(numeros_vendidos))
        
        # Obter dados do comprador
        comprador_nome = numero_sorteado.comprador_nome or 'Nome não informado'
        comprador_cpf = numero_sorteado.comprador_cpf or 'CPF não informado'
        comprador_email = numero_sorteado.comprador_email
        
        # Atualizar a rifa com os dados do ganhador
        rifa.ganhador_nome = comprador_nome
        rifa.ganhador_numero = numero_sorteado.numero
        rifa.ganhador_cpf = comprador_cpf
        rifa.encerrada = True
        rifa.save()
        
        # Enviar e-mail para o ganhador (opcional)
        if comprador_email:
            try:
                html_message = render_to_string('emails/ganhador_rifa.html', {
                    'nome_ganhador': comprador_nome,
                    'titulo_rifa': rifa.titulo,
                    'numero_bilhete': numero_sorteado.numero,
                    'valor_premio': rifa.preco,
                })
                send_mail(
                    f'🎉 Parabéns! Você ganhou: {rifa.titulo}',
                    f'Parabéns {comprador_nome}! Seu número {numero_sorteado.numero} foi sorteado na rifa "{rifa.titulo}".',
                    'Pantanal da Sorte <noreply@rifas.com>',
                    [comprador_email],
                    fail_silently=True,
                    html_message=html_message
                )
            except Exception as email_error:
                print(f"Erro ao enviar email: {email_error}")
        
        return JsonResponse({
            'success': True,
            'message': 'Sorteio realizado com sucesso!',
            'numero_sorteado': numero_sorteado.numero,
            'nome_ganhador': comprador_nome,
            'cpf_ganhador': comprador_cpf,
            'rifa_titulo': rifa.titulo
        })
        
    except Exception as e:
        print(f"Erro no sorteio: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno no servidor. Tente novamente.'
        }, status=500)


# --- VIEWS PARA INTEGRAÇÃO MERCADOPAGO / TESTES ---
from django.shortcuts import redirect
from .mercadopago_service import criar_preferencia
from django.http import HttpResponse

def teste_pagamento(request):
    # Exemplo: criar um pagamento de teste
    try:
        preference = criar_preferencia("Rifa Teste", 10.00)
    except Exception as e:
        # Retorna uma resposta amigável em caso de erro de criação da preferência
        return HttpResponse(f"Erro ao criar preferência de pagamento: {str(e)}", status=500)

    # Redireciona para o checkout do Mercado Pago
    init_point = None
    if isinstance(preference, dict):
        init_point = preference.get("init_point") or preference.get('sandbox_init_point')
    try:
        if not init_point:
            # Se não houver init_point, tenta obter do objeto direto
            init_point = preference['init_point']
    except Exception:
        pass

    if not init_point:
        return HttpResponse('Preferência criada, mas init_point não disponível.', status=502)

    return redirect(init_point)


def pagamento_sucesso(request):
    return HttpResponse("✅ Pagamento aprovado com sucesso!")


def pagamento_falha(request):
    return HttpResponse("❌ O pagamento falhou!")


def pagamento_pendente(request):
    return HttpResponse("⏳ O pagamento está pendente.")