from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('', include('rifa.app_urls')),

     # MODO MANUTENÇÃO ATIVADO
    path('', TemplateView.as_view(template_name='rifa/manutencao.html'), name='manutencao'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ═══════════════════════════════════════════════════════════════
# INSTRUÇÕES PARA REATIVAR O SITE:
# ═══════════════════════════════════════════════════════════════
# 1. Comentar a linha: path('', TemplateView.as_view(...)...)
# 2. Descomentar a linha: path('', include('rifa.app_urls'))
# 3. Reiniciar o servidor
# ═══════════════════════════════════════════════════════════════