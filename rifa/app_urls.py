from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('rifa/<int:raffle_id>/', views.raffle_detail, name='raffle-detail'),
    path('rifa/<int:rifa_id>/sortear/', views.sortear_rifa, name='sortear_rifa'),
    path('rifa/<int:raffle_id>/reservar/<int:number_id>/', views.reservar_numero, name='raffle-reserve'),
    path('premios/', views.premios, name='premios'),
    path('sorteios/', views.sorteios, name='sorteios'),
    path('sorteio/<int:id>/', views.sorteio_detail, name='sorteio_detail'),
    path('criar-rifa/', views.criar_rifa, name='criar_rifa'),
    path('editar-rifa/<int:rifa_id>/', views.editar_rifa, name='editar_rifa'),
    path('excluir-rifa/<int:rifa_id>/', views.excluir_rifa, name='excluir_rifa'),
    path('sortear-rifa/<int:rifa_id>/', views.sortear_rifa_ajax, name='sortear_rifa_ajax'),
    path('api/rifa/<int:rifa_id>/', views.api_rifa_detail, name='api_rifa_detail'),    
    path('api/rifa/<int:rifa_id>/data/', views.api_rifa_data, name='api_rifa_data'),
    path('api/pedido/<int:pedido_id>/status/', views.verificar_status_pagamento, name='verificar_status_pagamento'),
    
    # Autenticação
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout_view'),
    path('cadastro/', views.cadastro, name='cadastro'),
    path('perfil/', views.perfil, name='perfil'),
    
    # Reset de senha
    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    path('buscar-numeros/', views.buscar_numeros_por_telefone, name='buscar_numeros'),
    path('ganhadores/', views.ganhadores, name='ganhadores'),
    path('meus-numeros/', views.meus_numeros, name='meus_numeros'),
    path('buscar-pedidos/', views.buscar_pedidos, name='buscar_pedidos'),
    path('api/usuario-por-cpf/', views.api_usuario_por_cpf, name='api_usuario_por_cpf'),
    path('api/criar-pedido/', views.criar_pedido, name='criar_pedido'),
    path('api/verificar-cpf/', views.verificar_cpf, name='verificar_cpf'),
    path('api/gerar-qr/', views.gerar_qr_code, name='gerar_qr'),
    
    # URLs de pedido/pagamento
    path('pedido/<int:pedido_id>/pix/', views.pedido_pix, name='pedido_pix'),
    path('pedido/<int:pedido_id>/pagar/', views.pedido_pix, name='pedido_pagar'), 
    path('pedido/<int:pedido_id>/mostrar-qr/', views.mostrar_qr, name='mostrar_qr'),
    
    path('webhook/pagamento/', views.pagamento_webhook, name='pagamento_webhook'),
    path('api/rifa/<int:rifa_id>/definir-premio/', views.definir_premio, name='definir_premio'),
    path('api/rifa/<int:rifa_id>/premios/', views.api_premios_rifa, name='api_premios_rifa'),
    path('api/rifa/<int:rifa_id>/premio/<int:premio_id>/excluir/', views.excluir_premio, name='excluir_premio'),

    path('buscar-pedidos-cpf/', views.buscar_pedidos_cpf, name='buscar_pedidos_cpf'),
    path('pagamento/teste/', views.teste_pagamento, name='teste_pagamento'),
    path('pagamento/sucesso/', views.pagamento_sucesso, name='pagamento_sucesso'),
    path('pagamento/falha/', views.pagamento_falha, name='pagamento_falha'),
    path('pagamento/pendente/', views.pagamento_pendente, name='pagamento_pendente'),
    path('admin/test-email/', views.testar_email, name='testar_email'),
]