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
    path('login/', views.login_view, name='login'),
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('buscar-numeros/', views.buscar_numeros_por_telefone, name='buscar_numeros'),
    path('ganhadores/', views.ganhadores, name='ganhadores'),
    path('meus-numeros/', views.meus_numeros, name='meus_numeros'),
    path('buscar-pedidos/', views.buscar_pedidos, name='buscar_pedidos'),
]
