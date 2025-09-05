
from django.contrib import admin
from .models import Rifa, Numero, NumeroRifa, PremioBilhete
from .admin_numero import NumeroAdmin
from django.utils.html import format_html
import csv
from django.http import HttpResponse
from .models_profile import UserProfile
from django.contrib.auth.models import User

# Inline para editar UserProfile diretamente dentro do User
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    fk_name = 'user'
    extra = 1  # mostra formulário para criar quando não existe
    max_num = 1
    fieldsets = (
        ('Dados Pessoais', {
            'fields': ('nome_social','cpf','data_nascimento','telefone')
        }),
        ('Endereço', {
            'fields': ('cep','logradouro','numero','bairro','complemento','uf','cidade','referencia')
        }),
    )

class UserAdmin(admin.ModelAdmin):
    inlines = [UserProfileInline]
    list_display = ('username','email','first_name','cpf','is_staff')
    search_fields = ('username','email','first_name','profile__cpf')
    list_filter = ('is_staff','is_superuser','is_active')
    fieldsets = (
        (None, {'fields': ('username','password')}),
        ('Informações Pessoais', {'fields': ('first_name','last_name','email')}),
        ('Permissões', {'fields': ('is_active','is_staff','is_superuser','groups','user_permissions')}),
        ('Datas Importantes', {'fields': ('last_login','date_joined')}),
    )
    readonly_fields = ('last_login','date_joined')

    def cpf(self, obj):
        return getattr(getattr(obj, 'profile', None), 'cpf', '')
    cpf.short_description = 'CPF'

    def get_inline_instances(self, request, obj=None):
        # Garante criação automática do perfil se não existir ao abrir a página
        if obj and not hasattr(obj, 'profile'):
            UserProfile.objects.create(user=obj, cpf='000.000.000-00', data_nascimento='', telefone='', cep='', logradouro='', numero='', bairro='', uf='', cidade='')
        return super().get_inline_instances(request, obj)

# Desregistrar User padrão e registrar novo
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, UserAdmin)

# Admin para UserProfile
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'cpf', 'telefone', 'cidade', 'uf')
    search_fields = ('user__username', 'cpf', 'telefone', 'cidade', 'uf')
    fieldsets = (
        (None, {'fields': ('user','nome_social','cpf','data_nascimento','telefone')}),
        ('Endereço', {'fields': ('cep','logradouro','numero','bairro','complemento','uf','cidade','referencia')}),
    )

 # (limpo) imports duplicados removidos

@admin.register(Rifa)
class RifaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'preco', 'encerrada', 'imagem_tag', 'data_encerramento', 'ganhador_nome', 'ganhador_numero')
    actions = ['sortear_ganhador']

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Renomear ação para aparecer como 'Sortear' no painel
        if 'sortear_ganhador' in actions:
            actions['sortear_ganhador']['short_description'] = 'Sortear'
        return actions

    def sortear_ganhador(self, request, queryset):
        from django.contrib import messages
        from .models import Numero
        from django.core.mail import send_mail
        import random
        for rifa in queryset:
            if rifa.encerrada:
                messages.warning(request, f'Rifa "{rifa.titulo}" já está encerrada.')
                continue
            bilhetes = Numero.objects.filter(rifa=rifa, status='pago')
            if not bilhetes.exists():
                messages.warning(request, f'Nenhum bilhete pago para a rifa "{rifa.titulo}".')
                continue
            sorteado = random.choice(list(bilhetes))
            user = sorteado.reservado_por if hasattr(sorteado, 'reservado_por') else None
            rifa.ganhador_nome = user.get_full_name() or user.username if user else sorteado.comprador_nome
            rifa.ganhador_numero = sorteado.numero
            if hasattr(user, 'profile') and hasattr(user.profile, 'foto') and user.profile.foto:
                rifa.ganhador_foto = user.profile.foto
            rifa.encerrada = True
            rifa.save()
            # Enviar e-mail
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
                    '🎉 Parabéns! Você venceu a rifa',
                    '',
                    'Rifa Online <noreply@rifa.com>',
                    [email],
                    fail_silently=True,
                    html_message=html_message
                )
            messages.success(request, f'Ganhador sorteado para a rifa "{rifa.titulo}"!')
        self.message_user(request, 'Processo de sorteio finalizado.')
    sortear_ganhador.short_description = 'Sortear (encerra e escolhe ganhador)'
    list_filter = ('encerrada', 'data_encerramento')
    search_fields = ('titulo', 'descricao')
    fields = ('titulo', 'descricao', 'preco', 'imagem', 'encerrada', 'data_encerramento')

    def imagem_tag(self, obj):
        if obj.imagem:
            return format_html('<img src="{}" style="max-height:40px;max-width:60px;" />', obj.imagem.url)
        return "-"
    imagem_tag.short_description = 'Imagem'

    # Exportação CSV
    actions = ['exportar_csv']
    def exportar_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=rifas.csv'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Título', 'Descrição', 'Preço', 'Encerrada', 'Data Encerramento'])
        for rifa in queryset:
            writer.writerow([rifa.id, rifa.titulo, rifa.descricao, rifa.preco, rifa.encerrada, getattr(rifa, 'data_encerramento', '')])
        return response
    exportar_csv.short_description = "Exportar selecionadas para CSV"

    # Dashboard avançado
    change_list_template = "admin/rifa_dashboard.html"

    def changelist_view(self, request, extra_context=None):
        from .models import Numero
        queryset = self.get_queryset(request)
        total_bilhetes = Numero.objects.count()
        valor_total_vendido = sum([n.rifa.preco for n in Numero.objects.filter(status='pago')])
        rifas = queryset
        nomes_rifas = [r.titulo for r in rifas]
        bilhetes_por_rifa = [Numero.objects.filter(rifa=r).count() for r in rifas]
        extra_context = extra_context or {}
        rifas_ativas = queryset.filter(encerrada=False).count()
        rifas_encerradas = queryset.filter(encerrada=True).count()
        extra_context.update({
            'rifas_ativas': rifas_ativas,
            'rifas_encerradas': rifas_encerradas,
            'total_bilhetes': total_bilhetes,
            'valor_total_vendido': f'{valor_total_vendido:,.2f}'.replace('.',','),
            'nomes_rifas': nomes_rifas,
            'bilhetes_por_rifa': bilhetes_por_rifa,
        })
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(Numero)
class NumeroAdmin(admin.ModelAdmin):
    list_display = ('numero', 'rifa', 'status', 'comprador_nome', 'comprador_email', 'comprador_telefone')
    list_filter = ('status', 'rifa')
    search_fields = ('comprador_nome', 'comprador_email', 'comprador_telefone', 'numero')
    actions = ['exportar_csv', 'liberar_reservados', 'acao_atribuir_para_usuario']

    def exportar_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=numeros.csv'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Número', 'Rifa', 'Status', 'Nome', 'Email', 'Telefone'])
        for n in queryset:
            writer.writerow([n.id, n.numero, n.rifa.titulo, n.status, n.comprador_nome, n.comprador_email, n.comprador_telefone])
        return response
    exportar_csv.short_description = "Exportar selecionados para CSV"

    def liberar_reservados(self, request, queryset):
        """Action: libera bilhetes que estão em status 'reservado' (define como 'livre' e limpa comprador)."""
        from django.contrib import messages
        liberados = 0
        for n in queryset.filter(status='reservado'):
            n.status = 'livre'
            n.comprador_nome = ''
            n.comprador_email = ''
            n.comprador_telefone = ''
            # caso possua campo comprador_cpf
            if hasattr(n, 'comprador_cpf'):
                try: n.comprador_cpf = ''
                except Exception: pass
            n.save()
            liberados += 1
        messages.info(request, f'{liberados} bilhetes reservados foram liberados e ficaram como livres.')
    liberar_reservados.short_description = 'Liberar bilhetes reservados (marcar como livre)'

    def acao_atribuir_para_usuario(self, request, queryset):
        """Action que redireciona para a view interna de atribuição, passando os ids selecionados."""
        ids = ','.join([str(x) for x in queryset.values_list('pk', flat=True)])
        # Redireciona para a view customizada no admin para escolher o usuário
        from django.shortcuts import redirect
        return redirect(f'./atribuir/?ids={ids}')
    acao_atribuir_para_usuario.short_description = 'Atribuir números selecionados a um usuário...'

    # Adiciona uma view customizada no admin para atribuir números a um usuário
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('atribuir/', self.admin_site.admin_view(self.atribuir_view), name='rifa_numero_atribuir'),
        ]
        return custom_urls + urls

    def atribuir_view(self, request):
        """View simples dentro do admin para atribuir os números selecionados a um usuário."""
        from django.shortcuts import render, redirect
        from django.contrib import messages
        from django.contrib.auth.models import User
        ids = request.GET.get('ids', '') or request.POST.get('ids', '')
        id_list = [int(x) for x in ids.split(',') if x.strip().isdigit()]

        if request.method == 'POST':
            user_id = request.POST.get('user_id')
            status = request.POST.get('status') or 'reservado'
            try:
                user = User.objects.get(id=int(user_id))
            except Exception:
                messages.error(request, 'Usuário inválido escolhido.')
                return redirect(request.path + f'?ids={ids}')

            # Atribui cada número
            numeros_qs = Numero.objects.filter(id__in=id_list).select_related('rifa')
            count = 0

            # Se o admin escolheu marcar como 'pago', criamos Pedidos por Rifa e marcamos os números como pagos
            if status == 'pago':
                from .models import Pedido
                from django.utils import timezone
                # Agrupa números por rifa
                by_rifa = {}
                for n in numeros_qs:
                    by_rifa.setdefault(n.rifa.id, []).append(n)

                pedidos_criados = 0
                for rifa_id, numeros in by_rifa.items():
                    rifa_obj = numeros[0].rifa
                    nums = [str(n.numero) for n in numeros]
                    quantidade = len(numeros)
                    valor_unitario = rifa_obj.preco
                    valor_total = valor_unitario * quantidade
                    cpf_val = ''
                    telefone_val = ''
                    try:
                        cpf_val = getattr(user.profile, 'cpf', '') or ''
                        telefone_val = getattr(user.profile, 'telefone', '') or ''
                    except Exception:
                        cpf_val = ''
                        telefone_val = ''

                    pedido = Pedido.objects.create(
                        user=user,
                        rifa=rifa_obj,
                        quantidade=quantidade,
                        valor_unitario=valor_unitario,
                        valor_total=valor_total,
                        numeros_reservados=','.join(nums),
                        cpf=cpf_val,
                        nome=(user.first_name or user.username),
                        telefone=telefone_val,
                        pix_codigo='',
                        pix_txid='',
                        mercado_pago_payment_id='admin-assigned',
                        pix_qr_base64='',
                        status='pago',
                        expires_at=timezone.now()
                    )
                    pedidos_criados += 1

                    # Atualiza cada número como pago e vincula dados do comprador
                    for n in numeros:
                        n.status = 'pago'
                        n.comprador_nome = user.first_name or user.username
                        n.comprador_email = user.email or ''
                        n.comprador_telefone = telefone_val
                        try:
                            if cpf_val:
                                n.comprador_cpf = cpf_val
                        except Exception:
                            pass
                        n.save()
                        count += 1

                messages.success(request, f'{count} números marcados como pago e {pedidos_criados} pedidos criados.')
                return redirect('../../')

            else:
                numeros = numeros_qs
                for n in numeros:
                    n.status = status
                    n.comprador_nome = user.first_name or user.username
                    n.comprador_email = user.email or ''
                    # tenta buscar telefone do perfil
                    try:
                        n.comprador_telefone = getattr(user.profile, 'telefone', '') or ''
                    except Exception:
                        n.comprador_telefone = ''
                    # se existir campo comprador_cpf e o perfil tiver cpf, salva
                    try:
                        cpf = getattr(user.profile, 'cpf', '') or ''
                        if cpf:
                            n.comprador_cpf = cpf
                    except Exception:
                        pass
                    n.save()
                    count += 1

                messages.success(request, f'{count} números atribuídos ao usuário {user.username}.')
                return redirect('../../')

        # GET: renderiza formulário simples
        users = User.objects.all().order_by('username')[:200]
        context = {
            'title': 'Atribuir números a um usuário',
            'ids': ids,
            'id_list': id_list,
            'users': users,
            'opts': self.model._meta,
        }
        # HTML inline simples para evitar criar template novo
        html = """
        <div style="padding:20px;background:#111;color:#fff;">
          <h2>Atribuir números selecionados a um usuário</h2>
          <form method="post">
            {% csrf_token %}
            <input type="hidden" name="ids" value="%s" />
            <div style="margin:8px 0;">
              <label>Usuário:</label>
              <select name="user_id" style="min-width:300px;padding:8px;margin-left:8px;">
                %s
              </select>
            </div>
            <div style="margin:8px 0;">
              <label>Estado do bilhete:</label>
              <select name="status" style="padding:8px;margin-left:8px;">
                <option value="reservado">Reservado</option>
                <option value="pago">Pago</option>
                <option value="livre">Livre</option>
              </select>
            </div>
            <div style="margin-top:12px;">
              <button type="submit" class="default">Confirmar</button>
              <a href="../../" style="margin-left:12px;color:#ddd;">Cancelar</a>
            </div>
          </form>
        </div>
        """ % (
            ids,
            '\n'.join([f'<option value="{u.id}">{u.username} - {u.email}</option>' for u in users])
        )
        from django.http import HttpResponse
        return HttpResponse(html)

@admin.register(NumeroRifa)
class NumeroRifaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'rifa', 'reservado_por', 'reservado_em')
    list_filter = ('rifa',)
    search_fields = ('numero', 'rifa__titulo', 'reservado_por__username')

@admin.register(PremioBilhete)
class PremioBilheteAdmin(admin.ModelAdmin):
    list_display = ('rifa','numero_premiado','valor_premio','ativo','ganho_por','ganho_em')
    list_filter = ('rifa','ativo')
    search_fields = ('rifa__titulo','numero_premiado','ganho_por__username')
    readonly_fields = ('ganho_por','ganho_em','pedido','criado_em','atualizado_em')
    actions = ['ativar','desativar']
    def ativar(self,request,queryset): queryset.update(ativo=True)
    def desativar(self,request,queryset): queryset.update(ativo=False)
