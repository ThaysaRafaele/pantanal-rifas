from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from django.urls import reverse_lazy
from django.core.mail import send_mail
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Q

from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from django.urls import reverse_lazy
from django.contrib.auth import logout

import mercadopago
import re
import json
import uuid
import random
import decimal
import logging
import hmac
import hashlib

from .models import Rifa, Numero, NumeroRifa, Pedido, PremioBilhete
from .models_profile import UserProfile as Perfil

logger = logging.getLogger(__name__)

# ===== VIEWS PERSONALIZADAS PARA RESET DE SENHA =====
class CustomPasswordResetView(PasswordResetView):
    template_name = 'registration/password_reset_form.html'
    success_url = reverse_lazy('password_reset_done')
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'registration/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'registration/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'registration/password_reset_complete.html'
    
# ===== LOGOUT VIEW =====
def logout_view(request):
    """View personalizada para logout"""
    logout(request)
    messages.success(request, 'Você foi desconectado com sucesso!')
    return redirect('home')

# ===== PÁGINAS PRINCIPAIS =====
def home(request):
    rifas = Rifa.objects.all()
    return render(request, 'rifa/home.html', {'rifas': rifas, 'user': request.user})

def sorteios(request):
    rifas = Rifa.objects.all()
    return render(request, 'rifa/sorteios.html', {'rifas': rifas})

@login_required
def premios(request):
    rifas = Rifa.objects.all()
    return render(request, 'rifa/premios.html', {'rifas': rifas})

def ganhadores(request):
    rifas_encerradas = Rifa.objects.filter(encerrada=True).order_by('-data_encerramento')
    return render(request, 'rifa/ganhadores.html', {'rifas_encerradas': rifas_encerradas})

def meus_numeros(request):
    return render(request, 'rifa/meus_numeros.html')

@login_required
def sorteio_detail(request, id):
    rifa = get_object_or_404(Rifa, id=id)
    qtde_list = ['5', '10', '20', '50', '100', '200']
    numeros_list = Numero.objects.filter(rifa=rifa).order_by('numero')
    return render(request, 'rifa/raffle_detail.html', {
        'rifa': rifa,
        'qtde_list': qtde_list,
        'numeros_list': numeros_list
    })

def raffle_detail(request, raffle_id):
    rifa = get_object_or_404(Rifa, id=raffle_id)
    qtde_list = ['5', '10', '20', '50', '100', '200']
    numeros_list = Numero.objects.filter(rifa=rifa).order_by('numero')
    
    if request.method == 'POST':
        numero_id = request.POST.get('numero')
        numero_obj = get_object_or_404(Numero, id=numero_id, rifa=rifa)
        if numero_obj.status == 'livre':
            numero_obj.status = 'reservado'
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

# ===== AUTENTICAÇÃO =====
def login_view(request):
    """Login melhorado que aceita username, email ou CPF"""
    if request.method == 'POST':
        post = request.POST.copy()
        raw_user = post.get('username', '').strip()
        
        # Normalização do campo de entrada
        import re
        digits = re.sub(r'\D', '', raw_user)
        
        # Se parece com CPF (11 dígitos), busca por CPF
        if len(digits) == 11:
            cpf_formatted = f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
            
            # Busca no perfil primeiro
            from .models_profile import UserProfile
            profile = UserProfile.objects.filter(
                cpf__in=[digits, cpf_formatted]
            ).select_related('user').first()
            
            # Fallback: busca normalizando todos os CPFs
            if not profile:
                for p in UserProfile.objects.select_related('user').all():
                    p_digits = re.sub(r'\D', '', p.cpf or '')
                    if p_digits == digits:
                        profile = p
                        break
            
            if profile:
                post['username'] = profile.user.username
            else:
                # Tenta buscar por username se for 11 dígitos exatos
                user = User.objects.filter(username=digits).first()
                if user:
                    post['username'] = digits
        
        # Se parece com email
        elif '@' in raw_user:
            user = User.objects.filter(email__iexact=raw_user).first()
            if user:
                post['username'] = user.username
        
        # Primeira tentativa de autenticação
        form = AuthenticationForm(request, data=post)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
        
        # Fallback: busca case-insensitive por username
        user = User.objects.filter(username__iexact=raw_user).first()
        if user:
            post['username'] = user.username
            form = AuthenticationForm(request, data=post)
            if form.is_valid():
                login(request, form.get_user())
                return redirect('home')
        
        # Fallback: busca por nome_social no perfil
        from .models_profile import UserProfile
        profile = UserProfile.objects.filter(
            nome_social__iexact=raw_user
        ).select_related('user').first()
        if profile:
            post['username'] = profile.user.username
            form = AuthenticationForm(request, data=post)
            if form.is_valid():
                login(request, form.get_user())
                return redirect('home')
    
    else:
        form = AuthenticationForm()
    
    return render(request, 'rifa/login.html', {'form': form})

def cadastro(request):
    if request.method == 'POST':
        nome = request.POST['nomeCompleto']
        username = request.POST.get('username', '')
        cpf = request.POST['cpf']
        email = request.POST['email']
        telefone = request.POST['telefone']
        confirma_telefone = request.POST['confirmaTelefone']
        senha = request.POST['password1']
        senha2 = request.POST['password2']

        # Validações
        if senha != senha2:
            messages.error(request, "As senhas não coincidem.")
            return redirect('cadastro')
            
        if telefone != confirma_telefone:
            messages.error(request, "Os telefones não coincidem.")
            return redirect('cadastro')

        # Normaliza CPF
        cpf_digits = re.sub(r'\D','', cpf)
        cpf_formatted = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}" if len(cpf_digits)==11 else cpf

        # Verifica CPF existente
        exists_profile = Perfil.objects.filter(cpf__in=[cpf_formatted, cpf_digits]).first()
        if not exists_profile:
            for p in Perfil.objects.all():
                if re.sub(r'\D','', p.cpf or '') == cpf_digits:
                    exists_profile = p
                    break
        if exists_profile:
            messages.error(request, "CPF já cadastrado.")
            return redirect('cadastro')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Nome de usuário já existe.")
            return redirect('cadastro')
            
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email já cadastrado.")
            return redirect('cadastro')

        try:
            user = User.objects.create_user(
                username=username, 
                email=email, 
                password=senha, 
                first_name=nome
            )
            
            # Criar perfil apenas com campos essenciais
            Perfil.objects.create(
                user=user, 
                cpf=cpf_formatted, 
                nome_social='',  # Campo vazio por padrão
                telefone=telefone,
                # Campos opcionais vazios por enquanto
                data_nascimento='',
                cep='',
                logradouro='',
                numero='',
                bairro='',
                complemento='',
                uf='',
                cidade='',
                referencia=''
            )

            login(request, user)
            messages.success(request, "Cadastro realizado com sucesso!")
            return redirect('home')
            
        except Exception as e:
            messages.error(request, f"Erro ao criar cadastro: {str(e)}")
            return redirect('cadastro')

    return render(request, 'rifa/cadastro.html')

# ===== GESTÃO DE RIFAS =====
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
    
    sorteado = random.choice(list(bilhetes))
    user = getattr(sorteado, 'reservado_por', None)
    
    rifa.ganhador_nome = user.get_full_name() if user and user.get_full_name() else (user.username if user else sorteado.comprador_nome)
    rifa.ganhador_numero = sorteado.numero
    rifa.encerrada = True
    rifa.save()
    
    # Enviar email
    email = user.email if user else sorteado.comprador_email
    if email:
        from django.template.loader import render_to_string
        html_message = render_to_string('emails/ganhador_rifa.html', {
            'nome_ganhador': rifa.ganhador_nome,
            'titulo_rifa': rifa.titulo,
            'numero_bilhete': rifa.ganhador_numero,
            'valor_premio': rifa.preco,
        })
        send_mail(
            '🎉 Parabéns! Seu bilhete foi sorteado.',
            '',
            'Pantanal da Sorte <noreply@rifa.com>',
            [email],
            fail_silently=True,
            html_message=html_message
        )
    
    messages.success(request, f'Ganhador sorteado "{rifa.titulo}"!')
    return redirect('raffle-detail', raffle_id=rifa.id)

@login_required
def sortear_rifa_ajax(request, rifa_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Permissão negada'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    try:
        rifa = get_object_or_404(Rifa, id=rifa_id)
        
        if rifa.encerrada:
            return JsonResponse({
                'success': False,
                'message': 'Esta rifa já está encerrada.'
            })
        
        numeros_vendidos = Numero.objects.filter(rifa=rifa, status='pago')
        if not numeros_vendidos.exists():
            return JsonResponse({
                'success': False,
                'message': 'Nenhum número foi vendido para esta rifa ainda.'
            })
        
        numero_sorteado = random.choice(list(numeros_vendidos))
        comprador_nome = numero_sorteado.comprador_nome or 'Nome não informado'
        comprador_cpf = numero_sorteado.comprador_cpf or 'CPF não informado'
        comprador_email = numero_sorteado.comprador_email
        
        rifa.ganhador_nome = comprador_nome
        rifa.ganhador_numero = numero_sorteado.numero
        rifa.ganhador_cpf = comprador_cpf
        rifa.encerrada = True
        rifa.save()
        
        # Enviar email
        if comprador_email:
            try:
                from django.template.loader import render_to_string
                html_message = render_to_string('emails/ganhador_rifa.html', {
                    'nome_ganhador': comprador_nome,
                    'titulo_rifa': rifa.titulo,
                    'numero_bilhete': numero_sorteado.numero,
                    'valor_premio': rifa.preco,
                })
                send_mail(
                    f'🎉 Parabéns! Você ganhou: {rifa.titulo}',
                    f'Parabéns {comprador_nome}! Seu número {numero_sorteado.numero} foi sorteado.',
                    'Pantanal da Sorte <noreply@rifas.com>',
                    [comprador_email],
                    fail_silently=True,
                    html_message=html_message
                )
            except Exception as email_error:
                logger.error(f"Erro ao enviar email: {email_error}")
        
        return JsonResponse({
            'success': True,
            'message': 'Sorteio realizado com sucesso!',
            'numero_sorteado': numero_sorteado.numero,
            'nome_ganhador': comprador_nome,
            'cpf_ganhador': comprador_cpf,
            'rifa_titulo': rifa.titulo
        })
        
    except Exception as e:
        logger.error(f"Erro no sorteio: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno no servidor.'
        }, status=500)

@login_required
def reservar_numero(request, raffle_id, number_id):
    rifa = get_object_or_404(Rifa, id=raffle_id)
    numero_obj = Numero.objects.filter(rifa=rifa, id=number_id).first()
    
    if not numero_obj:
        numero_obj = Numero.objects.create(rifa=rifa, numero=number_id, status='livre')

    if request.method == 'POST':
        if numero_obj.status == 'livre':
            numero_obj.status = 'reservado'
            numero_obj.save()
            messages.success(request, 'Número reservado com sucesso!')
        else:
            messages.error(request, 'Este número já foi reservado.')
        return redirect('raffle_detail', raffle_id=rifa.id)

    return render(request, 'rifa/reservar_numero.html', {'raffle': rifa, 'numero': numero_obj, 'user': request.user})

@login_required
def criar_rifa(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Apenas administradores podem criar rifas.')
        return redirect('sorteios')
    
    if request.method == 'POST':
        try:
            rifa = Rifa()
            rifa.titulo = request.POST.get('titulo')
            rifa.descricao = request.POST.get('descricao', '')
            rifa.preco = float(request.POST.get('preco', 0))
            rifa.quantidade_numeros = int(request.POST.get('quantidade_numeros', 100))
            
            data_encerramento = request.POST.get('data_encerramento')
            if data_encerramento:
                import datetime
                rifa.data_encerramento = timezone.make_aware(
                    datetime.datetime.fromisoformat(data_encerramento)
                )
            
            rifa.encerrada = 'encerrada' in request.POST
            
            if 'imagem' in request.FILES:
                rifa.imagem = request.FILES['imagem']
            
            rifa.save()
            
            # Criar números automaticamente
            for numero in range(1, rifa.quantidade_numeros + 1):
                Numero.objects.create(rifa=rifa, numero=numero, status='livre')
            
            messages.success(request, f'Rifa "{rifa.titulo}" criada com sucesso!')
            return redirect('sorteios')
            
        except Exception as e:
            messages.error(request, f'Erro ao criar rifa: {str(e)}')
            return redirect('sorteios')
    
    return redirect('sorteios')

@login_required
def editar_rifa(request, rifa_id):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Apenas administradores podem editar rifas.')
        return redirect('sorteios')
    
    rifa = get_object_or_404(Rifa, id=rifa_id)
    
    if request.method == 'POST':
        try:
            rifa.titulo = request.POST.get('titulo', rifa.titulo)
            rifa.descricao = request.POST.get('descricao', rifa.descricao)
            rifa.preco = float(request.POST.get('preco', rifa.preco))
            
            data_encerramento = request.POST.get('data_encerramento')
            if data_encerramento:
                import datetime
                rifa.data_encerramento = timezone.make_aware(
                    datetime.datetime.fromisoformat(data_encerramento)
                )
            else:
                rifa.data_encerramento = None
            
            rifa.encerrada = 'encerrada' in request.POST
            
            if 'imagem' in request.FILES:
                rifa.imagem = request.FILES['imagem']
            
            rifa.save()
            messages.success(request, f'Rifa "{rifa.titulo}" editada com sucesso!')
            return redirect('sorteios')
            
        except Exception as e:
            messages.error(request, f'Erro ao editar rifa: {str(e)}')
            return redirect('sorteios')
    
    return redirect('sorteios')

@login_required
def excluir_rifa(request, rifa_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Permissão negada'}, status=403)
    
    if request.method == 'POST':
        try:
            rifa = get_object_or_404(Rifa, id=rifa_id)
            titulo = rifa.titulo
            
            Numero.objects.filter(rifa=rifa).delete()
            rifa.delete()
            
            return JsonResponse({
                'success': True, 
                'message': f'Rifa "{titulo}" excluída com sucesso!',
                'redirect': True
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Erro ao excluir rifa: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Método não permitido'}, status=405)

# ===== APIS =====
@login_required
def api_rifa_detail(request, rifa_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Permissão negada'}, status=403)
    
    try:
        rifa = get_object_or_404(Rifa, id=rifa_id)
        numeros_vendidos = Numero.objects.filter(rifa=rifa, status='pago').count()
        
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
    """API para buscar usuário por CPF (GET)"""
    cpf_raw = request.GET.get('cpf', '').strip()
    
    import re
    digits = re.sub(r'\D', '', cpf_raw)
    if len(digits) != 11:
        return JsonResponse({'found': False, 'message': 'CPF deve ter 11 dígitos'})
    
    cpf_formatted = f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    
    try:
        from .models_profile import UserProfile
        
        # Busca por ambos os formatos
        profile = UserProfile.objects.filter(
            cpf__in=[digits, cpf_formatted]
        ).select_related('user').first()
        
        # Fallback: normalização
        if not profile:
            for p in UserProfile.objects.select_related('user').all():
                p_digits = re.sub(r'\D', '', p.cpf or '')
                if p_digits == digits:
                    profile = p
                    break
        
        if not profile:
            return JsonResponse({
                'found': False, 
                'message': 'Não existe conta cadastrada neste CPF'
            })
        
        user = profile.user
        nome = user.first_name or user.username
        email = user.email or ''
        telefone = getattr(profile, 'telefone', '') or ''
        
        # Mascaramento para privacidade
        def mask_email(e):
            if not e or '@' not in e:
                return ''
            u, d = e.split('@', 1)
            return (u[0] + '*' * (len(u) - 1)) + '@' + d if len(u) > 1 else '*@' + d
        
        def mask_phone(p):
            if not p:
                return ''
            digs = re.sub(r'\D', '', p)
            if len(digs) <= 7:
                return digs
            return digs[:2] + '*' * (len(digs) - 5) + digs[-3:]
        
        return JsonResponse({
            'found': True,
            'nome': nome,
            'email': mask_email(email),
            'telefone': mask_phone(telefone)
        })
        
    except Exception:
        return JsonResponse({
            'found': False, 
            'message': 'Erro ao buscar CPF'
        })

@csrf_exempt
def verificar_cpf(request):
    """Verifica se existe usuário com o CPF (POST) - VERSÃO CORRIGIDA"""
    try:
        data = request.POST or json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        return JsonResponse({'found': False, 'message': 'Dados inválidos'})

    cpf_raw = data.get('cpf', '').strip()
    if not cpf_raw:
        return JsonResponse({'found': False, 'message': 'CPF obrigatório'})

    import re
    cpf_digits = re.sub(r'\D', '', cpf_raw)
    if len(cpf_digits) != 11:
        return JsonResponse({'found': False, 'message': 'CPF deve ter 11 dígitos'})

    # Formatos para busca
    cpf_formatted = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"
    
    try:
        from .models_profile import UserProfile
        
        # Busca direta por ambos os formatos
        profile = UserProfile.objects.filter(
            cpf__in=[cpf_digits, cpf_formatted]
        ).select_related('user').first()
        
        # Fallback: normalização completa
        if not profile:
            for p in UserProfile.objects.select_related('user').all():
                p_digits = re.sub(r'\D', '', p.cpf or '')
                if p_digits == cpf_digits:
                    profile = p
                    break
        
        if not profile:
            return JsonResponse({
                'found': False, 
                'message': 'Não existe conta cadastrada com este CPF'
            })
        
        user = profile.user
        return JsonResponse({
            'found': True, 
            'user': {
                'nome': getattr(profile, 'nome_social', '') or user.get_full_name() or user.username,
                'email': user.email,
                'telefone': getattr(profile, 'telefone', '')
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'found': False, 
            'message': f'Erro interno: {str(e)}'
        })

# ===== BUSCA DE PEDIDOS =====
@csrf_exempt
def buscar_pedidos(request):
    if request.method == 'POST':
        telefone = request.POST.get('telefone', '').strip()
        cpf = request.POST.get('cpf', '').strip().replace('.', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
        
        numeros = []
        
        if telefone:
            telefone_limpo = telefone.replace('(', '').replace(')', '').replace(' ', '').replace('-', '')
            numeros = Numero.objects.filter(comprador_telefone__icontains=telefone_limpo).select_related('rifa')
        elif cpf and len(cpf) == 11 and cpf.isdigit():
            numeros = Numero.objects.filter(comprador_cpf=cpf).select_related('rifa')
        
        if numeros:
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
            return JsonResponse({'status': 'not_found', 'message': 'Nenhum número encontrado.'})

    return JsonResponse({'status': 'error', 'message': 'Método inválido.'})

@csrf_exempt
def buscar_numeros_por_telefone(request):
    if request.method == 'POST':
        telefone = request.POST.get('telefone', '').strip()
        cpf = request.POST.get('cpf', '').strip().replace('.', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
        
        numeros = []
        
        if telefone:
            telefone_limpo = telefone.replace('(', '').replace(')', '').replace(' ', '').replace('-', '')
            numeros = Numero.objects.filter(comprador_telefone__icontains=telefone_limpo).select_related('rifa')
        elif cpf and len(cpf) == 11 and cpf.isdigit():
            numeros = Numero.objects.filter(comprador_cpf=cpf).select_related('rifa')
        
        if numeros:
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
            return JsonResponse({'status': 'not_found', 'message': 'Nenhum número encontrado.'})

    return JsonResponse({'status': 'error', 'message': 'Método inválido.'})


@csrf_exempt
def buscar_pedidos_cpf(request):
    """View para buscar pedidos pelo CPF do comprador - VERSÃO FINAL CORRIGIDA"""
    if request.method == 'POST':
        cpf = request.POST.get('cpf', '').strip()
        
        if not cpf:
            return JsonResponse({
                'status': 'error',
                'message': 'CPF é obrigatório.'
            })
        
        cpf_limpo = re.sub(r'\D', '', cpf)
        
        if len(cpf_limpo) != 11:
            return JsonResponse({
                'status': 'error',
                'message': 'CPF deve ter 11 dígitos.'
            })
        
        try:
            cpf_formatado = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
            
            # Buscar números diretamente - não pedidos
            numeros = Numero.objects.filter(
                comprador_cpf__in=[cpf_limpo, cpf_formatado],
                status__in=['reservado', 'pago']
            ).select_related('rifa').order_by('-reservado_em')
            
            if not numeros.exists():
                return JsonResponse({
                    'status': 'not_found',
                    'message': 'Nenhum número encontrado para o CPF informado.'
                })
            
            numeros_data = []
            pedidos_processados = set()  # Para evitar duplicatas
            
            for numero in numeros:
                # Buscar pedido relacionado (se existir)
                pedido = Pedido.objects.filter(
                    rifa=numero.rifa,
                    cpf__in=[cpf_limpo, cpf_formatado],
                    numeros_reservados__contains=str(numero.numero)
                ).first()
                
                # Calcular tempo restante
                tempo_restante = 0
                if numero.status == 'reservado' and numero.reservado_em:
                    tempo_decorrido = (timezone.now() - numero.reservado_em).total_seconds()
                    tempo_limite = 86400
                    tempo_restante = max(0, tempo_limite - tempo_decorrido)
                
                # Status do NÚMERO (não do pedido)
                status_display = numero.status.title()  # 'Reservado' ou 'Pago'
                
                # Identificador único para agrupar por pedido
                pedido_key = f"{numero.rifa.id}_{pedido.id if pedido else 'sem_pedido'}"
                
                # Dados do número
                numero_dict = {
                    'numero': str(numero.numero).zfill(6),
                    'rifa_titulo': numero.rifa.titulo,
                    'rifa_id': numero.rifa.id,
                    'pedido_id': pedido.id if pedido else None,
                    'status': status_display,
                    'comprador_nome': numero.comprador_nome or 'Não informado',
                    'quantidade': pedido.quantidade if pedido else 1,
                    'valor_total': float(pedido.valor_total) if pedido else float(numero.rifa.preco),
                    'tempo_restante': int(tempo_restante)
                }
                
                numeros_data.append(numero_dict)
            
            return JsonResponse({
                'status': 'success',
                'numeros': numeros_data
            })
                
        except Exception as e:
            logger.error(f'Erro ao buscar pedidos por CPF {cpf}: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
            
            return JsonResponse({
                'status': 'error',
                'message': 'Erro ao processar a busca. Tente novamente.'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Método não permitido.'
    })
    
# ===== PAGAMENTOS E PEDIDOS =====
@csrf_exempt
def criar_pedido(request):
    if request.method != 'POST':
        return JsonResponse({'error':'Método inválido'}, status=405)
    
    try:
        rifa_id = request.POST.get('rifa_id')
        cpf_raw = (request.POST.get('cpf') or '').strip()
        qtd = int(request.POST.get('quantidade','0'))
        
        if qtd <= 0:
            return JsonResponse({'error':'Quantidade inválida'}, status=400)
        
        rifa = get_object_or_404(Rifa, id=rifa_id)
        
        # Sanitizar CPF
        digits = re.sub(r'\D','', cpf_raw)
        if len(digits) != 11:
            return JsonResponse({'error':'CPF inválido'}, status=400)
        
        cpf_fmt = f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
        
        # Localizar usuário pelo CPF
        profile = Perfil.objects.select_related('user').filter(cpf__in=[cpf_fmt, digits]).first()
        if not profile:
            for p in Perfil.objects.select_related('user').all():
                if re.sub(r'\D','', p.cpf or '') == digits:
                    profile = p
                    break
        
        if not profile:
            return JsonResponse({'error':'CPF não cadastrado'}, status=400)
        
        user = profile.user
        preco = decimal.Decimal(rifa.preco)
        total_max = rifa.quantidade_numeros
        
        if total_max <= 0:
            return JsonResponse({'error':'Rifa sem limite de números configurado.'}, status=400)
        
        with transaction.atomic():
            # Números ocupados
            ocupados = set(Numero.objects.select_for_update(skip_locked=True)
                           .filter(rifa=rifa)
                           .exclude(status='livre')
                           .values_list('numero', flat=True))
            
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
        
        # Criar pedido
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
            pix_codigo=f"TXID:{txid}|RIFA:{rifa.id}|TOTAL:{valor_total:.2f}",
            pix_txid=txid,
            expires_at=timezone.now()+timezone.timedelta(hours=1)
        )
        
        # Tentar criar pagamento PIX via Mercado Pago
        try:
            from .mercadopago_service import MercadoPagoService
            mp_service = MercadoPagoService()
            
            description = f'Rifa {rifa.titulo} - Pedido #{pedido.id}'
            
            mp_resp = mp_service.criar_pagamento_pix(
                amount=float(valor_total),
                description=description,
                payer_email=user.email if user.email else None,
                external_reference=str(pedido.id),
                payer_cpf=cpf_fmt
            )
            
            if mp_resp.get('success'):
                if mp_resp.get('payment_id'):
                    pedido.mercado_pago_payment_id = str(mp_resp['payment_id'])
                    pedido.pix_txid = str(mp_resp['payment_id'])
                
                if mp_resp.get('qr_code_base64'):
                    pedido.pix_qr_base64 = mp_resp['qr_code_base64']
                
                if mp_resp.get('qr_code'):
                    pedido.pix_codigo = mp_resp['qr_code']
                
                pedido.save(update_fields=['mercado_pago_payment_id','pix_qr_base64','pix_codigo','pix_txid'])
                
        except Exception as e:
            logger.exception('Erro ao criar pagamento PIX: %s', e)
        
        # Verificar prêmios ganhos
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
        
        return JsonResponse({
            'success': True,
            'pedido_id': pedido.id,
            'redirect': f"/pedido/{pedido.id}/pix/",
            'premios_ganhos': premios_ganhos
        })
        
    except Exception as e:
        logger.exception('Erro ao criar pedido: %s', e)
        return JsonResponse({'error': str(e)}, status=500)

def pedido_pix(request, pedido_id):
    try:
        pedido = get_object_or_404(Pedido, id=pedido_id)
        if pedido.expirado():
            pedido.status = 'expirado'
            pedido.save(update_fields=['status'])
        
        return render(request, 'rifa/pedido_pix.html', {
            'pedido': pedido,
            'pix_qr_base64': getattr(pedido, 'pix_qr_base64', None),
            'pix_codigo': getattr(pedido, 'pix_codigo', None),
            'mercado_pago_payment_id': getattr(pedido, 'mercado_pago_payment_id', None),
        })
    except Exception as e:
        logger.exception('Erro ao renderizar pedido_pix: %s', e)
        if getattr(settings, 'DEBUG', False):
            return HttpResponse(f'<h1>Erro ao abrir pedido #{pedido_id}</h1><pre>{str(e)}</pre>', status=500)
        return HttpResponse('<h1>Erro ao abrir pedido</h1>', status=500)

@csrf_exempt
def gerar_qr_code(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido.'}, status=405)

    try:
        try:
            data = json.loads(request.body.decode('utf-8') or '{}')
        except Exception:
            data = request.POST.dict()

        pedido_id = data.get('pedido_id') or data.get('order_id')
        
        if not pedido_id:
            return JsonResponse({'error': 'pedido_id é obrigatório'}, status=400)

        try:
            pedido = get_object_or_404(Pedido, id=pedido_id)
        except Exception as e:
            logger.error(f"Erro ao buscar pedido {pedido_id}: {e}")
            return JsonResponse({'error': f'Pedido {pedido_id} não encontrado'}, status=404)
        
        # Se já existe QR salvo, retorna imediatamente
        if pedido.pix_qr_base64 and pedido.pix_codigo:
            return JsonResponse({
                "success": True,
                "payment_id": pedido.mercado_pago_payment_id,
                "qr_code": pedido.pix_codigo,
                "qr_code_base64": pedido.pix_qr_base64,
                "status": pedido.status,
                "cached": True,
                "pedido_id": pedido_id
            })

        # Criar pagamento PIX no Mercado Pago
        try:
            from .mercadopago_service import MercadoPagoService
            mp_service = MercadoPagoService()
            
            payer_email = None
            payer_cpf = None
            
            if pedido.user and pedido.user.email:
                payer_email = pedido.user.email
            
            if pedido.cpf:
                payer_cpf = pedido.cpf
            elif pedido.user and hasattr(pedido.user, 'userprofile') and pedido.user.userprofile.cpf:
                payer_cpf = pedido.user.userprofile.cpf
            
            description = f'Rifa {pedido.rifa.titulo} - Pedido #{pedido.id}'
            
            payment_result = mp_service.criar_pagamento_pix(
                amount=float(pedido.valor_total),
                description=description,
                payer_email=payer_email,
                external_reference=str(pedido_id),
                payer_cpf=payer_cpf
            )
            
            if not payment_result.get("success"):
                # Fallback: código PIX simples
                fallback_code = f"PEDIDO:{pedido.id}|VALOR:{pedido.valor_total:.2f}|RIFA:{pedido.rifa.id}|TX:{uuid.uuid4().hex[:8]}"
                
                pedido.pix_codigo = fallback_code
                pedido.save(update_fields=['pix_codigo'])
                
                return JsonResponse({
                    'success': True,
                    'payment_id': None,
                    'qr_code': fallback_code,
                    'qr_code_base64': None,
                    'status': 'pending',
                    'fallback': True,
                    'message': 'QR Code gerado localmente',
                    'pedido_id': pedido_id
                })

            # Salvar dados do Mercado Pago
            try:
                if payment_result.get("payment_id"):
                    pedido.mercado_pago_payment_id = str(payment_result["payment_id"])
                    pedido.pix_txid = str(payment_result["payment_id"])
                
                if payment_result.get("qr_code_base64"):
                    pedido.pix_qr_base64 = payment_result["qr_code_base64"]
                
                if payment_result.get("qr_code"):
                    pedido.pix_codigo = payment_result["qr_code"]
                elif payment_result.get("pix_code"):
                    pedido.pix_codigo = payment_result["pix_code"]
                
                pedido.save(update_fields=[
                    'mercado_pago_payment_id', 
                    'pix_qr_base64', 
                    'pix_codigo', 
                    'pix_txid'
                ])
                
            except Exception as e:
                logger.error(f"Erro ao salvar dados no pedido {pedido_id}: {e}")

            return JsonResponse({
                "success": True,
                "payment_id": payment_result.get("payment_id"),
                "qr_code": payment_result.get("qr_code") or payment_result.get("pix_code"),
                "qr_code_base64": payment_result.get("qr_code_base64"),
                "status": payment_result.get("status", "pending"),
                "pedido_id": pedido_id,
                "message": "QR Code gerado com sucesso"
            })

        except Exception as e:
            logger.exception(f'Erro ao criar pagamento PIX: {e}')
            
            # Fallback
            try:
                fallback_code = f"PEDIDO:{pedido.id}|VALOR:{pedido.valor_total:.2f}|RIFA:{pedido.rifa.id}|TX:{uuid.uuid4().hex[:8]}"
                pedido.pix_codigo = fallback_code
                pedido.save(update_fields=['pix_codigo'])
                
                return JsonResponse({
                    'success': True,
                    'payment_id': None,
                    'qr_code': fallback_code,
                    'qr_code_base64': None,
                    'status': 'pending',
                    'fallback': True,
                    'message': 'QR Code gerado localmente',
                    'pedido_id': pedido_id
                })
            except Exception as fallback_error:
                logger.error(f"Erro no fallback: {fallback_error}")
                return JsonResponse({
                    'error': 'Erro ao gerar pagamento PIX',
                    'details': str(e)
                }, status=500)

    except Exception as e:
        logger.exception(f'Erro inesperado ao gerar QR: {e}')
        return JsonResponse({
            'error': 'Erro interno do servidor',
            'details': str(e)
        }, status=500)

def mostrar_qr(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    qr_code_base64 = getattr(pedido, 'pix_qr_base64', None)
    
    if not qr_code_base64:
        qr_code_base64 = request.GET.get('qr_code_base64')

    return render(request, 'rifa/mostrar_qr.html', {'pedido': pedido, 'qr_code_base64': qr_code_base64})

# ===== WEBHOOK MERCADO PAGO =====
@csrf_exempt
def pagamento_webhook(request):
    try:
        raw = request.body.decode('utf-8') or ''
        
        # Validar assinatura
        signature = request.headers.get('x-signature', '')
        webhook_secret = getattr(settings, 'MERCADOPAGO_WEBHOOK_SECRET', '')
        
        if webhook_secret and signature:
            expected_signature = hmac.new(
                webhook_secret.encode(),
                raw.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning('Assinatura do webhook inválida')
                return JsonResponse({'status': 'invalid_signature'}, status=400)
        
        logger.info('Webhook recebido: %s', raw)
        
        # Parse do payload
        payload = {}
        try:
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {}

        # Extrair payment_id
        payment_id = None
        if isinstance(payload, dict):
            data = payload.get('data') or payload.get('resource') or {}
            if isinstance(data, dict):
                payment_id = data.get('id') or data.get('payment', {}).get('id')
            if not payment_id:
                payment_id = payload.get('id')

        if not payment_id:
            return JsonResponse({'status': 'ok', 'message': 'no_payment_id'})

        if not getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None):
            logger.error('MERCADOPAGO_ACCESS_TOKEN ausente')
            return JsonResponse({'status': 'error'}, status=500)

        # Buscar dados do pagamento no Mercado Pago
        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        mp_resp = sdk.payment().get(payment_id)
        result = mp_resp.get('response') if isinstance(mp_resp, dict) else mp_resp

        external_ref = None
        status = None
        transaction_amount = 0
        
        if isinstance(result, dict):
            external_ref = result.get('external_reference')
            status = result.get('status')
            transaction_amount = result.get('transaction_amount', 0)

        # Processar pedido
        if external_ref:
            try:
                pedido = Pedido.objects.filter(id=int(external_ref)).first()
                
                if pedido and status and status.lower() in ['approved', 'paid']:
                    logger.info(f'Processando pagamento aprovado - Pedido: {pedido.id}')
                    
                    pedido.status = 'pago'
                    
                    # Atualizar números para "pago"
                    numeros_ids = [int(x) for x in pedido.numeros_reservados.split(',') if x.strip().isdigit()]
                    Numero.objects.filter(
                        rifa=pedido.rifa,
                        numero__in=numeros_ids,
                        status='reservado'
                    ).update(status='pago')
                    
                    pedido.save()
                    
                    # Transferir para Lenon
                    try:
                        taxa_plataforma = getattr(settings, 'TAXA_PLATAFORMA', 0)
                        valor_para_lenon = float(transaction_amount) * (1 - taxa_plataforma)
                        
                        if valor_para_lenon > 0:
                            sucesso = transferir_para_lenon(payment_id, valor_para_lenon, pedido.id)
                            if sucesso:
                                logger.info(f'Transferência realizada para pedido {pedido.id}')
                            else:
                                logger.error(f'Falha na transferência para pedido {pedido.id}')
                        
                    except Exception as e:
                        logger.exception(f'Erro na transferência para pedido {pedido.id}: {e}')
                        
            except Exception as e:
                logger.exception(f'Erro ao processar pedido {external_ref}: {e}')

        return JsonResponse({'status': 'ok'})

    except Exception as e:
        logger.exception(f'Erro crítico no webhook: {e}')
        return JsonResponse({'status': 'error'}, status=500)

def transferir_para_lenon(payment_id, valor, pedido_id):
    try:
        from .mercadopago_service import MercadoPagoService
        mp_service = MercadoPagoService()
        
        result = mp_service.criar_transferencia(
            amount=valor,
            receiver_id=settings.LENON_USER_ID,
            description=f"Rifa - Pedido #{pedido_id}"
        )
        
        if result.get("success"):
            logger.info(f'Transferência criada: {result.get("transfer_id")}')
            return True
        else:
            logger.error(f'Erro na transferência: {result.get("error")}')
            return False
            
    except Exception as e:
        logger.exception(f'Erro ao transferir para Lenon: {e}')
        return False

# ===== PRÊMIOS =====
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
        
        valor_raw = (request.POST.get('valor_premio') or '').strip().replace(',','.')
        if not valor_raw:
            return JsonResponse({'error':'Valor obrigatório'}, status=400)
        
        valor = decimal.Decimal(valor_raw)
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

# ===== VERIFICAÇÃO DE STATUS =====
@csrf_exempt 
def verificar_status_pagamento(request, pedido_id):
    try:
        pedido = get_object_or_404(Pedido, id=pedido_id)
        
        if pedido.mercado_pago_payment_id:
            try:
                from .mercadopago_service import MercadoPagoService
                mp_service = MercadoPagoService()
                
                status_result = mp_service.verificar_pagamento(pedido.mercado_pago_payment_id)
                
                if status_result.get("success"):
                    mp_status = status_result.get("status")
                    
                    if mp_status == "approved" and pedido.status != "pago":
                        pedido.status = "pago"
                        
                        numeros_ids = [int(x) for x in pedido.numeros_reservados.split(',') if x.strip().isdigit()]
                        Numero.objects.filter(
                            rifa=pedido.rifa,
                            numero__in=numeros_ids,
                            status='reservado'
                        ).update(status='pago')
                        
                        pedido.save()
                    
                    return JsonResponse({
                        "success": True,
                        "status": pedido.status,
                        "mercado_pago_status": mp_status,
                        "payment_id": pedido.mercado_pago_payment_id,
                        "updated": True
                    })
                else:
                    return JsonResponse({
                        "success": True,
                        "status": pedido.status,
                        "error": "Erro ao consultar Mercado Pago",
                        "updated": False
                    })
                    
            except Exception as e:
                logger.error(f"Erro ao verificar pagamento no MP: {e}")
                return JsonResponse({
                    "success": True,
                    "status": pedido.status,
                    "error": "Erro na consulta externa",
                    "updated": False
                })
        else:
            return JsonResponse({
                "success": True,
                "status": pedido.status,
                "message": "Sem integração ativa",
                "updated": False
            })
            
    except Exception as e:
        logger.error(f"Erro ao verificar status do pedido {pedido_id}: {e}")
        return JsonResponse({
            "error": "Erro ao verificar status",
            "details": str(e)
        }, status=500)

# ===== TESTES MERCADO PAGO =====
@csrf_exempt
def testar_mercadopago(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Acesso negado'}, status=403)
    
    try:
        from .mercadopago_service import MercadoPagoService
        mp_service = MercadoPagoService()
        result = mp_service.testar_conexao()
        return JsonResponse(result)
        
    except Exception as e:
        logger.exception(f'Erro ao testar Mercado Pago: {e}')
        return JsonResponse({
            'success': False,
            'error': 'Erro no teste',
            'details': str(e)
        }, status=500)

def teste_pagamento(request):
    try:
        from .mercadopago_service import criar_preferencia
        preference = criar_preferencia("Rifa Teste", 10.00)
    except Exception as e:
        return HttpResponse(f"Erro ao criar preferência: {str(e)}", status=500)

    init_point = None
    if isinstance(preference, dict):
        init_point = preference.get("init_point") or preference.get('sandbox_init_point')
    
    try:
        if not init_point:
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

# ===== UTILIDADES ADMIN =====
@staff_member_required
def testar_email(request):
    try:
        resultado = send_mail(
            subject='🧪 Teste de Email - Pantanal da Sorte',
            message='Configuração SMTP funcionando! ✅',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email if request.user.email else 'pantanaldasortems@gmail.com'],
            fail_silently=False,
            html_message='''
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                    <h2 style="color: #ffd700; text-align: center;">🧪 Teste de Email</h2>
                    <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <p style="font-size: 16px; line-height: 1.6;">
                            <strong>Parabéns!</strong> 🎉
                        </p>
                        <p style="font-size: 16px; line-height: 1.6;">
                            A configuração de email do <strong>Pantanal da Sorte</strong> está funcionando.
                        </p>
                        <div style="background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <p style="margin: 0; color: #2e7d2e;">
                                ✅ <strong>SMTP configurado!</strong><br>
                                ✅ <strong>Reset de senha funcionando!</strong>
                            </p>
                        </div>
                    </div>
                </div>
            '''
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Email teste enviado! ({resultado} email(s))',
            'destinatario': request.user.email if request.user.email else 'pantanaldasortems@gmail.com',
            'configuracao': {
                'EMAIL_BACKEND': settings.EMAIL_BACKEND,
                'EMAIL_HOST': getattr(settings, 'EMAIL_HOST', 'Não configurado'),
                'EMAIL_PORT': getattr(settings, 'EMAIL_PORT', 'Não configurado'),
                'EMAIL_USE_TLS': getattr(settings, 'EMAIL_USE_TLS', False),
                'DEFAULT_FROM_EMAIL': getattr(settings, 'DEFAULT_FROM_EMAIL', 'Não configurado')
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': 'Erro ao enviar email de teste',
            'dica': 'Verifique se a App Password do Gmail está correta'
        }, status=500)

@csrf_exempt
def export_data_api(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        users = []
        for user in User.objects.all():
            profile = getattr(user, 'userprofile', None)
            users.append({
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'cpf': profile.cpf if profile else '',
                'telefone': profile.telefone if profile else '',
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser
            })
        
        rifas = []
        for rifa in Rifa.objects.all():
            rifas.append({
                'id': rifa.id,
                'titulo': rifa.titulo,
                'descricao': rifa.descricao,
                'preco': float(rifa.preco),
                'quantidade_numeros': rifa.quantidade_numeros,
                'encerrada': rifa.encerrada
            })
        
        numeros = []
        for numero in Numero.objects.exclude(status='livre'):
            numeros.append({
                'rifa_id': numero.rifa.id,
                'numero': numero.numero,
                'status': numero.status,
                'comprador_nome': numero.comprador_nome,
                'comprador_email': numero.comprador_email,
                'comprador_cpf': numero.comprador_cpf,
                'comprador_telefone': numero.comprador_telefone
            })
        
        pedidos = []
        for pedido in Pedido.objects.all():
            pedidos.append({
                'id': pedido.id,
                'user_email': pedido.user.email if pedido.user else '',
                'rifa_id': pedido.rifa.id,
                'quantidade': pedido.quantidade,
                'valor_total': float(pedido.valor_total),
                'numeros_reservados': pedido.numeros_reservados,
                'cpf': pedido.cpf,
                'nome': pedido.nome,
                'status': pedido.status,
                'created_at': pedido.created_at.isoformat()
            })
        
        return JsonResponse({
            'users': users,
            'rifas': rifas,
            'numeros': numeros,
            'pedidos': pedidos
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
def exportar_dados_para_migracao(request):
    try:
        data = {
            'users': [],
            'rifas': [],
            'numeros': [],
            'timestamp': timezone.now().isoformat()
        }
        
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
            
            try:
                if hasattr(user, 'profile'):
                    profile = user.profile
                    user_data['profile'] = {
                        'cpf': profile.cpf or '',
                        'telefone': profile.telefone or '',
                        'nome_social': profile.nome_social or '',
                        'data_nascimento': str(profile.data_nascimento) if profile.data_nascimento else '',
                        'cep': profile.cep or '',
                        'logradouro': profile.logradouro or '',
                        'numero': profile.numero or '',
                        'bairro': profile.bairro or '',
                        'uf': profile.uf or '',
                        'cidade': profile.cidade or ''
                    }
            except Exception as e:
                logger.error(f"Erro ao exportar perfil do usuário {user.username}: {e}")
            
            data['users'].append(user_data)
        
        for rifa in Rifa.objects.all():
            data['rifas'].append({
                'id': rifa.id,
                'titulo': rifa.titulo,
                'descricao': rifa.descricao,
                'preco': float(rifa.preco),
                'encerrada': rifa.encerrada,
                'ganhador_nome': rifa.ganhador_nome or '',
                'ganhador_numero': rifa.ganhador_numero,
                'data_encerramento': rifa.data_encerramento.isoformat() if hasattr(rifa, 'data_encerramento') and rifa.data_encerramento else None
            })
        
        for numero in Numero.objects.all():
            data['numeros'].append({
                'id': numero.id,
                'numero': numero.numero,
                'rifa_id': numero.rifa.id,
                'status': numero.status,
                'comprador_nome': numero.comprador_nome or '',
                'comprador_email': numero.comprador_email or '',
                'comprador_telefone': numero.comprador_telefone or '',
                'comprador_cpf': getattr(numero, 'comprador_cpf', '') or ''
            })
        
        stats = {
            'total_users': len(data['users']),
            'total_rifas': len(data['rifas']),
            'total_numeros': len(data['numeros']),
            'numeros_pagos': len([n for n in data['numeros'] if n['status'] == 'pago']),
            'numeros_reservados': len([n for n in data['numeros'] if n['status'] == 'reservado']),
            'rifas_ativas': len([r for r in data['rifas'] if not r['encerrada']]),
            'rifas_encerradas': len([r for r in data['rifas'] if r['encerrada']])
        }
        
        data['stats'] = stats
        
        return JsonResponse({
            'success': True,
            'data': data,
            'message': f'Dados exportados: {stats["total_users"]} usuários, {stats["total_rifas"]} rifas, {stats["total_numeros"]} bilhetes'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': 'Erro ao exportar dados'
        }, status=500)

@staff_member_required
def gerar_bilhetes_web(request):
    rifa_id = request.GET.get('rifa_id')
    dry_run = request.GET.get('dry_run', 'false').lower() == 'true'
    
    if not rifa_id:
        return HttpResponse("""
        <h2>Gerar Bilhetes - Produção</h2>
        <p>Especifique o ID da rifa:</p>
        <a href="?rifa_id=10&dry_run=true">🧪 Teste Rifa ID 10</a><br>
        <a href="?rifa_id=11&dry_run=true">🧪 Teste Rifa ID 11</a><br><br>
        <a href="?rifa_id=10">⚡ EXECUTAR Rifa ID 10</a><br>
        <a href="?rifa_id=11">⚡ EXECUTAR Rifa ID 11</a><br>
        """)
    
    try:
        rifa = get_object_or_404(Rifa, id=rifa_id)
        
        output = []
        output.append(f"<h2>Processando: {rifa.titulo} (ID: {rifa.id})</h2>")
        output.append(f"<p>Limite: {rifa.quantidade_numeros:,} bilhetes</p>")
        
        numeros_existentes = set(Numero.objects.filter(rifa=rifa).values_list('numero', flat=True))
        total_existentes = len(numeros_existentes)
        
        output.append(f"<p>Existentes: {total_existentes:,}</p>")
        
        faltantes = rifa.quantidade_numeros - total_existentes
        
        if faltantes <= 0:
            output.append(f"<p style='color: green;'>✅ Completo: {total_existentes:,} bilhetes</p>")
            return HttpResponse('<br>'.join(output))
        
        output.append(f"<p>Faltantes: {faltantes:,}</p>")
        
        numeros_para_criar = []
        for numero in range(1, rifa.quantidade_numeros + 1):
            if numero not in numeros_existentes:
                numeros_para_criar.append(numero)
        
        if dry_run:
            output.append(f"<p style='color: orange;'>[TESTE] Seriam criados {len(numeros_para_criar):,} bilhetes</p>")
            output.append(f"<p><a href='?rifa_id={rifa_id}'>▶️ EXECUTAR</a></p>")
            return HttpResponse('<br>'.join(output))
        
        output.append("<h3>Criando bilhetes...</h3>")
        batch_size = 1000
        total_criados = 0
        
        for i in range(0, len(numeros_para_criar), batch_size):
            lote = numeros_para_criar[i:i + batch_size]
            
            try:
                with transaction.atomic():
                    bilhetes_para_criar = [
                        Numero(rifa=rifa, numero=numero, status='livre')
                        for numero in lote
                    ]
                    
                    Numero.objects.bulk_create(bilhetes_para_criar, ignore_conflicts=True)
                    total_criados += len(lote)
                    
                    lote_num = i//batch_size + 1
                    output.append(f"<p>✓ Lote {lote_num}: {len(lote):,} (Total: {total_criados:,})</p>")
                    
            except Exception as e:
                output.append(f"<p style='color: red;'>❌ Erro lote {i//batch_size + 1}: {e}</p>")
                continue
        
        total_final = Numero.objects.filter(rifa=rifa).count()
        output.append(f"<h3 style='color: green;'>✅ CONCLUÍDO</h3>")
        output.append(f"<p>Total final: {total_final:,} bilhetes</p>")
        
        stats = Numero.objects.filter(rifa=rifa).values('status').annotate(total=Count('id'))
        output.append("<h4>📊 ESTATÍSTICAS:</h4>")
        for stat in stats:
            output.append(f"<p>- {stat['status'].title()}: {stat['total']:,}</p>")
        
        return HttpResponse('<br>'.join(output))
        
    except Exception as e:
        return HttpResponse(f"<h2>Erro:</h2><p>{str(e)}</p>")

@csrf_exempt
def export_manual(request):
    try:
        users = list(User.objects.values('username', 'email', 'first_name', 'is_staff', 'is_superuser'))
        rifas = list(Rifa.objects.values('id', 'titulo', 'descricao', 'preco', 'encerrada'))
        numeros = list(Numero.objects.exclude(status='livre').values(
            'numero', 'rifa_id', 'status', 'comprador_nome', 
            'comprador_email', 'comprador_cpf', 'comprador_telefone'
        ))
        
        return JsonResponse({
            'users': users,
            'rifas': rifas, 
            'numeros': numeros,
            'count': f"{len(users)} usuários, {len(rifas)} rifas, {len(numeros)} números"
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)})

# ===== PERFIL =====
@login_required
def perfil(request):
    """Exibe e permite editar o perfil do usuário logado"""
    try:
        profile = request.user.profile
    except AttributeError:
        # Cria perfil se não existir
        from .models_profile import UserProfile
        profile = UserProfile.objects.create(
            user=request.user,
            cpf='',
            nome_social='',
            data_nascimento='',
            telefone='',
            cep='',
            logradouro='',
            numero='',
            bairro='',
            uf='',
            cidade='',
            complemento='',
            referencia=''
        )
    
    if request.method == 'POST':
        try:
            # Dados do User
            new_username = request.POST.get('username', '').strip()
            new_email = request.POST.get('email', '').strip()
            new_first_name = request.POST.get('first_name', '').strip()
            
            # Dados do Profile
            new_nome_social = request.POST.get('nome_social', '').strip()
            new_telefone = request.POST.get('telefone', '').strip()
            
            # Validações de unicidade (excluindo o próprio usuário)
            if new_username != request.user.username:
                if User.objects.filter(username=new_username).exclude(id=request.user.id).exists():
                    messages.error(request, "Nome de usuário já está em uso.")
                    return render(request, 'rifa/perfil.html', {'profile': profile})
            
            if new_email != request.user.email:
                if User.objects.filter(email=new_email).exclude(id=request.user.id).exists():
                    messages.error(request, "Email já está em uso.")
                    return render(request, 'rifa/perfil.html', {'profile': profile})
            
            # Atualizar User
            request.user.username = new_username
            request.user.email = new_email
            request.user.first_name = new_first_name
            request.user.save()
            
            # Atualizar Profile
            profile.nome_social = new_nome_social
            profile.telefone = new_telefone
            profile.save()
            
            messages.success(request, "Perfil atualizado com sucesso!")
            
        except Exception as e:
            messages.error(request, f"Erro ao atualizar perfil: {str(e)}")
    
    return render(request, 'rifa/perfil.html', {
        'profile': profile
    })      

@csrf_exempt 
def verificar_status_pagamento(request, pedido_id):
    try:
        pedido = get_object_or_404(Pedido, id=pedido_id)
        return JsonResponse({
            "success": True,
            "status": pedido.status,
            "payment_id": getattr(pedido, 'mercado_pago_payment_id', None),
            "updated": False
        })
    except Exception as e:
        return JsonResponse({
            "error": "Erro ao verificar status",
            "details": str(e)
        }, status=500)
        

def api_rifa_data(request, rifa_id):
    """API para retornar dados básicos de uma rifa"""
    try:
        rifa = get_object_or_404(Rifa, id=rifa_id)
        
        return JsonResponse({
            'id': rifa.id,
            'titulo': rifa.titulo,
            'preco': float(rifa.preco),
            'encerrada': rifa.encerrada,
            'quantidade_numeros': rifa.quantidade_numeros
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)