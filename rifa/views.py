from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from .models import Rifa, Numero, NumeroRifa
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
import mercadopago
import json
import logging
import hmac
import hashlib

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
    qtde_list = ['5', '10', '20', '50', '100', '200']  # Sugestão de quantidades para compra
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

        # Primeiro tentativa com os dados normalizados
        form = AuthenticationForm(request, data=post)
        if form.is_valid():
            user = form.get_user()
            logger.debug('login success: raw=%s -> candidate=%s user=%s', raw_user, post.get('username'), user.username)
            login(request, user)
            return redirect('home')
        else:
            logger.debug('login attempt failed: raw=%s -> candidate=%s form_errors=%s', raw_user, post.get('username'), form.non_field_errors() or form.errors)

        # Se falhou, tentar localizar por username exato (case-insensitive) ou pelo nome_social do perfil
        try:
            # tenta username case-insensitive
            u = User.objects.filter(username__iexact=raw_user).first()
            if u:
                post['username'] = u.username
                logger.debug('fallback matched username__iexact: raw=%s -> %s', raw_user, post['username'])
                form = AuthenticationForm(request, data=post)
                if form.is_valid():
                    login(request, form.get_user())
                    return redirect('home')
            # tenta por nome_social no perfil (case-insensitive)
            from rifa.models_profile import UserProfile
            profile = UserProfile.objects.filter(nome_social__iexact=raw_user).select_related('user').first()
            if profile and profile.user:
                post['username'] = profile.user.username
                logger.debug('fallback matched nome_social: raw=%s -> %s', raw_user, post['username'])
                form = AuthenticationForm(request, data=post)
                if form.is_valid():
                    login(request, form.get_user())
                    return redirect('home')
        except Exception:
            pass
    else:
        form = AuthenticationForm()
    return render(request, 'rifa/login.html', {'form': form})

def cadastro(request):
    if request.method == 'POST':
        nome = request.POST['nomeCompleto']
        username = request.POST.get('username', '')
        social = request.POST.get('nomeSocial', '')
        cpf = request.POST['cpf']
        data = request.POST['dataNascimento']
        email = request.POST['email']
        telefone = request.POST['telefone']
        confirma_telefone = request.POST['confirmaTelefone']
        # CORRIGIDO: usar password1 e password2 em vez de senha e senha2
        senha = request.POST['password1']
        senha2 = request.POST['password2']
        
        # Campos de endereço
        cep = request.POST['cep']
        logradouro = request.POST['logradouro']
        numero = request.POST['numero']
        bairro = request.POST['bairro']
        complemento = request.POST.get('complemento', '')
        uf = request.POST['uf']
        cidade = request.POST['cidade']
        referencia = request.POST.get('referencia', '')

        # Validações
        if senha != senha2:
            messages.error(request, "As senhas não coincidem.")
            return redirect('cadastro')
            
        if telefone != confirma_telefone:
            messages.error(request, "Os telefones não coincidem.")
            return redirect('cadastro')

        # Normaliza CPF para salvar no perfil
        import re
        cpf_digits = re.sub(r'\D','', cpf)
        cpf_formatted = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}" if len(cpf_digits)==11 else cpf

        # Verifica se o CPF já existe em UserProfile
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

        # Verifica se username já existe
        if User.objects.filter(username=username).exists():
            messages.error(request, "Nome de usuário já existe.")
            return redirect('cadastro')
            
        # Verifica se email já existe
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email já cadastrado.")
            return redirect('cadastro')

        try:
            # Cria usuário
            user = User.objects.create_user(
                username=username, 
                email=email, 
                password=senha, 
                first_name=nome
            )
            
            # Cria perfil com todos os campos
            Perfil.objects.create(
                user=user, 
                cpf=cpf_formatted, 
                nome_social=social, 
                data_nascimento=data,
                telefone=telefone,
                cep=cep,
                logradouro=logradouro,
                numero=numero,
                bairro=bairro,
                complemento=complemento,
                uf=uf,
                cidade=cidade,
                referencia=referencia
            )

            login(request, user)  # loga automaticamente
            messages.success(request, "Cadastro realizado com sucesso!")
            return redirect('home')
            
        except Exception as e:
            messages.error(request, f"Erro ao criar cadastro: {str(e)}")
            return redirect('cadastro')

    return render(request, 'rifa/cadastro.html')

@login_required
def premios(request):
    rifas = Rifa.objects.all()
    return render(request, 'rifa/premios.html', {'rifas': rifas})

def home(request):
    rifas = Rifa.objects.all()
    return render(request, 'rifa/home.html', {'rifas': rifas, 'user': request.user})


@csrf_exempt
@require_POST
def verificar_cpf(request):
    """API simples para verificar se existe usuário com o CPF fornecido.
    Recebe 'cpf' no body (form-encoded ou json). Retorna JSON:
    { found: true/false, user: { nome, email, telefone } }
    """
    try:
        data = request.POST or json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        return HttpResponseBadRequest('Invalid payload')

    cpf_raw = data.get('cpf')
    if not cpf_raw:
        return HttpResponseBadRequest('cpf required')

    import re
    cpf_digits = re.sub(r'\D', '', cpf_raw)
    if len(cpf_digits) != 11:
        return JsonResponse({'found': False})

    # Tenta por diferentes formatos
    cpf_formatted = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"
    from .models_profile import UserProfile
    profile = UserProfile.objects.filter(cpf__in=[cpf_formatted, cpf_digits]).select_related('user').first()
    if not profile:
        # tentar varredura normalizando outros perfis
        for p in UserProfile.objects.all():
            if re.sub(r'\D', '', p.cpf or '') == cpf_digits:
                profile = p
                break

    if not profile:
        return JsonResponse({'found': False})

    user = profile.user
    return JsonResponse({'found': True, 'user': {
        'nome': profile.nome_social or user.get_full_name() or user.username,
        'email': user.email,
        'telefone': getattr(profile, 'telefone', '')
    }})
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
    qtde_list = ['5', '10', '20', '50', '100', '200']  # Sugestão de quantidades para compra
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
    """
    API para gerar QR Code PIX usando Mercado Pago
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido. Use POST.'}, status=405)

    try:
        # Parse do body da requisição
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
        
        # Se já existe QR salvo no pedido, retorna imediatamente
        if pedido.pix_qr_base64:
            return JsonResponse({
                "success": True,
                "payment_id": pedido.mercado_pago_payment_id,
                "qr_code": pedido.pix_codigo,
                "qr_code_base64": pedido.pix_qr_base64,
                "status": pedido.status,
                "cached": True,
                "pedido_id": pedido_id
            })

        # Usar o novo serviço do Mercado Pago
        try:
            from .mercadopago_service import MercadoPagoService
            mp_service = MercadoPagoService()
            
            # Dados do pagador
            payer_email = None
            payer_cpf = None
            
            if pedido.user and pedido.user.email:
                payer_email = pedido.user.email
            
            # CPF do pedido ou do perfil do usuário
            if pedido.cpf:
                payer_cpf = pedido.cpf
            elif pedido.user and hasattr(pedido.user, 'profile') and pedido.user.profile.cpf:
                payer_cpf = pedido.user.profile.cpf
            
            # Descrição do pagamento
            description = f'Rifa {pedido.rifa.titulo} - Pedido #{pedido.id}'
            
            logger.info(f"Criando pagamento PIX para pedido {pedido_id}: "
                       f"valor={pedido.valor_total}, email={payer_email}, cpf={payer_cpf}")
            
            # Criar pagamento PIX
            payment_result = mp_service.criar_pagamento_pix(
                amount=float(pedido.valor_total),
                description=description,
                payer_email=payer_email,
                external_reference=str(pedido_id),
                payer_cpf=payer_cpf
            )
            
            logger.info(f"Resultado do pagamento MP: {payment_result}")
            
            if not payment_result.get("success"):
                logger.error(f"Falha no Mercado Pago: {payment_result}")
                # Fallback: retornar código PIX simples
                import uuid
                fallback_code = f"PEDIDO:{pedido.id}|VALOR:{pedido.valor_total:.2f}|RIFA:{pedido.rifa.id}|TX:{uuid.uuid4().hex[:8]}"
                
                # Salvar código fallback
                pedido.pix_codigo = fallback_code
                pedido.save(update_fields=['pix_codigo'])
                
                return JsonResponse({
                    'success': True,
                    'payment_id': None,
                    'qr_code': fallback_code,
                    'qr_code_base64': None,
                    'status': 'pending',
                    'fallback': True,
                    'message': 'QR Code gerado localmente (Mercado Pago indisponível)',
                    'error_details': payment_result.get('details'),
                    'pedido_id': pedido_id
                })

            # Salvar dados no pedido
            try:
                if payment_result.get("payment_id"):
                    pedido.mercado_pago_payment_id = str(payment_result["payment_id"])
                    pedido.pix_txid = str(payment_result["payment_id"])
                
                if payment_result.get("qr_code_base64"):
                    pedido.pix_qr_base64 = payment_result["qr_code_base64"]
                
                if payment_result.get("qr_code"):
                    pedido.pix_codigo = payment_result["qr_code"]
                
                pedido.save(update_fields=[
                    'mercado_pago_payment_id', 
                    'pix_qr_base64', 
                    'pix_codigo', 
                    'pix_txid'
                ])
                
                logger.info(f"Dados de pagamento salvos no pedido {pedido_id}")
                
            except Exception as e:
                logger.error(f"Erro ao salvar dados no pedido {pedido_id}: {e}")

            return JsonResponse({
                "success": True,
                "payment_id": payment_result.get("payment_id"),
                "qr_code": payment_result.get("qr_code"),
                "qr_code_base64": payment_result.get("qr_code_base64"),
                "status": payment_result.get("status", "pending"),
                "pedido_id": pedido_id,
                "message": "QR Code gerado com sucesso"
            })

        except Exception as e:
            logger.exception(f'Erro ao criar pagamento PIX via MP: {e}')
            
            # Fallback: retornar código PIX simples se Mercado Pago falhar
            try:
                import uuid
                fallback_code = f"PEDIDO:{pedido.id}|VALOR:{pedido.valor_total:.2f}|RIFA:{pedido.rifa.id}|TX:{uuid.uuid4().hex[:8]}"
                
                # Salvar código fallback
                pedido.pix_codigo = fallback_code
                pedido.save(update_fields=['pix_codigo'])
                
                return JsonResponse({
                    'success': True,
                    'payment_id': None,
                    'qr_code': fallback_code,
                    'qr_code_base64': None,
                    'status': 'pending',
                    'fallback': True,
                    'message': 'QR Code gerado localmente (Mercado Pago indisponível)',
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

@csrf_exempt
def pagamento_webhook(request):
    """Webhook que transfere automaticamente para o Lenon quando pagamento é aprovado."""
    try:
        raw = request.body.decode('utf-8') or ''
        
        # Validar assinatura do webhook para segurança
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
            logger.info('Webhook sem payment_id')
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
            
            logger.info(f'Payment {payment_id}: status={status}, amount={transaction_amount}, ref={external_ref}')

        # Processar pedido se encontrado
        if external_ref:
            try:
                pedido = Pedido.objects.filter(id=int(external_ref)).first()
                
                if pedido and status and status.lower() in ['approved', 'paid']:
                    logger.info(f'Processando pagamento aprovado - Pedido: {pedido.id}')
                    
                    # Marcar pedido como pago
                    pedido.status = 'pago'
                    
                    # Atualizar números para "pago"
                    numeros_ids = [int(x) for x in pedido.numeros_reservados.split(',') if x.strip().isdigit()]
                    Numero.objects.filter(
                        rifa=pedido.rifa,
                        numero__in=numeros_ids,
                        status='reservado'
                    ).update(status='pago')
                    
                    # Salvar pedido
                    pedido.save()
                    
                    # TRANSFERIR PARA O LENON AUTOMATICAMENTE
                    try:
                        taxa_plataforma = getattr(settings, 'TAXA_PLATAFORMA', 0)
                        valor_para_lenon = float(transaction_amount) * (1 - taxa_plataforma)
                        
                        if valor_para_lenon > 0:
                            logger.info(f'Iniciando transferência para Lenon: R$ {valor_para_lenon:.2f}')
                            
                            sucesso = transferir_para_lenon(payment_id, valor_para_lenon, pedido.id)
                            
                            if sucesso:
                                logger.info(f'Transferência realizada com sucesso para pedido {pedido.id}')
                            else:
                                logger.error(f'Falha na transferência para pedido {pedido.id}')
                        else:
                            logger.warning(f'Valor para transferência é zero ou negativo: {valor_para_lenon}')
                            
                    except Exception as e:
                        logger.exception(f'Erro na transferência automática para pedido {pedido.id}: {e}')
                        
                elif pedido:
                    logger.info(f'Pedido {pedido.id} encontrado mas status não é aprovado: {status}')
                else:
                    logger.warning(f'Pedido não encontrado para external_reference: {external_ref}')
                    
            except Exception as e:
                logger.exception(f'Erro ao processar pedido {external_ref}: {e}')
        else:
            logger.info('Webhook sem external_reference')

        return JsonResponse({'status': 'ok'})

    except Exception as e:
        logger.exception(f'Erro crítico no webhook: {e}')
        return JsonResponse({'status': 'error'}, status=500)

def transferir_para_lenon(payment_id, valor, pedido_id):
    """Transfere automaticamente para a conta do Lenon"""
    try:
        logger.info(f'INICIANDO transferência - Payment: {payment_id}, Valor: R$ {valor:.2f}, Pedido: {pedido_id}')
        
        from .mercadopago_service import MercadoPagoService
        mp_service = MercadoPagoService()
        
        result = mp_service.criar_transferencia(
            amount=valor,
            receiver_id=settings.LENON_USER_ID,
            description=f"Rifa - Pedido #{pedido_id}"
        )
        
        logger.info(f'RESULTADO transferência: {result}')
        
        if result.get("success"):
            logger.info(f'Transferência criada com sucesso: {result.get("transfer_id")}')
            return True
        else:
            logger.error(f'Erro na transferência: {result.get("error")} - {result.get("details")}')
            return False
            
    except Exception as e:
        logger.exception(f'ERRO CRÍTICO ao transferir para Lenon: {e}')
        return False

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

@csrf_exempt 
def verificar_status_pagamento(request, pedido_id):
    """
    API para verificar status de pagamento
    """
    try:
        pedido = get_object_or_404(Pedido, id=pedido_id)
        
        # Se tem payment_id do Mercado Pago, consulta a API
        if pedido.mercado_pago_payment_id:
            try:
                from .mercadopago_service import MercadoPagoService
                mp_service = MercadoPagoService()
                
                status_result = mp_service.verificar_pagamento(pedido.mercado_pago_payment_id)
                
                if status_result.get("success"):
                    mp_status = status_result.get("status")
                    
                    # Atualizar status do pedido se necessário
                    if mp_status == "approved" and pedido.status != "pago":
                        pedido.status = "pago"
                        
                        # Atualizar números para "pago"
                        numeros_ids = [int(x) for x in pedido.numeros_reservados.split(',') if x.strip().isdigit()]
                        Numero.objects.filter(
                            rifa=pedido.rifa,
                            numero__in=numeros_ids,
                            status='reservado'
                        ).update(status='pago')
                        
                        pedido.save()
                        logger.info(f"Pedido {pedido_id} marcado como pago")
                    
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
            # Sem payment_id, apenas retorna status atual
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


@csrf_exempt
def testar_mercadopago(request):
    """
    Endpoint para testar a conexão com Mercado Pago
    """
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