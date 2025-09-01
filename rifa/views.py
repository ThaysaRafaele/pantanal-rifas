from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from .models import Rifa, Numero, NumeroRifa
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

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
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'rifa/login.html', {'form': form})

def cadastro_view(request):
    from .forms_user import CustomUserCreationForm
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Save extra fields to user model (first_name, email, etc.)
            user.first_name = form.cleaned_data.get('nomeCompleto')
            user.email = form.cleaned_data.get('email')
            user.save()
            # Optionally, save extra info to a profile model or another table
            login(request, user)
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'rifa/cadastro.html', {'form': form})

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
    pedido = get_object_or_404(Pedido, id=pedido_id)
    if pedido.expirado():
        pedido.status='expirado'
        pedido.save(update_fields=['status'])
    return render(request, 'rifa/pedido_pix.html', {'pedido':pedido})

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
