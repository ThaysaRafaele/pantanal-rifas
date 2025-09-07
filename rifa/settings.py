from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-your-secret-key-here'
DEBUG = True
ALLOWED_HOSTS = ['pantanal.onrender.com', 'localhost', '127.0.0.1', 'www.pantanaldasortems.com', 'pantanaldasortems.com']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rifa',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'rifa.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'rifa.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Cuiaba'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# =======================
# 🔑 Mercado Pago Config - PRODUÇÃO ( Transferindo para conta do Lenon)
# =======================
MERCADOPAGO_PUBLIC_KEY = os.getenv(
    "MERCADOPAGO_PUBLIC_KEY",
    "APP_USR-2b928fc8-0a66-461b-b9b4-daac8737c198"
)

MERCADOPAGO_ACCESS_TOKEN = os.getenv(
    "MERCADOPAGO_ACCESS_TOKEN",
    "APP_USR-5791646844116557-090620-60f7b4822bce105687cb6339f9a99e64-190769772"
)

MERCADOPAGO_CLIENT_ID = os.getenv(
    "MERCADOPAGO_CLIENT_ID",
    "5791646844116557"
)

MERCADOPAGO_CLIENT_SECRET = os.getenv(
    "MERCADOPAGO_CLIENT_SECRET",
    "Kz1LwAcsCZT67FaLhYshFzQuE49CnZPj"
)

# Dados do Lenon para transfers
LENON_EMAIL = "lenonms543@gmail.com"  # Email da conta MP do Lenon
LENON_CPF = "01800818106"  # CPF
LENON_USER_ID = "217387767"  # User ID da conta do Lenon
TAXA_PLATAFORMA = 0.00 

# Assinatura do webhook para validação
MERCADOPAGO_WEBHOOK_SECRET = "edbd5177af11d0917d78100f19e5f819694608d6c12d82355fb05037b6b536b5"

# Exemplo de chamada curl (apenas referência / comentário):
# curl -H 'Authorization: Bearer APP_USR-7966421377263587-090120-14ab8d825b8e13df9dc6ae4511d54e3d-2665708908' \
#   https://api.mercadolibre.com/users/me
