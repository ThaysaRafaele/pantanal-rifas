from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-your-secret-key-here')
DEBUG = os.getenv('DEBUG', 'False') == 'True'

CSRF_TRUSTED_ORIGINS = [
    'https://pantanaldasortems.com',
    'https://www.pantanaldasortems.com',
]

ALLOWED_HOSTS = [
    'localhost', 
    '127.0.0.1',
    '.onrender.com', 
    'pantanal.onrender.com',
    'pantanal-rifas.onrender.com',
    'www.pantanaldasortems.com', 
    'pantanaldasortems.com',
    '82.29.58.76',
]

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
    'whitenoise.middleware.WhiteNoiseMiddleware', 
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
        'DIRS': [
            BASE_DIR / 'rifa' / 'templates',
        ],
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

# Database
if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.parse(
            os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
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

# Static files
STATIC_URL = '/static/'
if 'RENDER' in os.environ or not DEBUG:
    STATIC_ROOT = BASE_DIR / 'staticfiles'
else:
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

static_dir = BASE_DIR / 'static'
if static_dir.exists():
    STATICFILES_DIRS = [static_dir]
else:
    STATICFILES_DIRS = []

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
if 'RENDER' in os.environ or not DEBUG:
    MEDIA_ROOT = BASE_DIR / 'media'
else:
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Email configuration
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'pantanaldasortems@gmail.com')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', 'wvds ohna hkoc aosx')
    DEFAULT_FROM_EMAIL = 'Pantanal da Sorte <pantanaldasortems@gmail.com>'
    EMAIL_SUBJECT_PREFIX = '[Pantanal da Sorte] '
    EMAIL_USE_SSL = False
    EMAIL_TIMEOUT = 30

SITE_ID = 1
ADMINS = [('Admin', 'pantanaldasortems@gmail.com')]
MANAGERS = ADMINS

# Security settings para produção
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_REDIRECT_EXEMPT = []
    SECURE_SSL_REDIRECT = False  
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Mercado Pago Config
MERCADOPAGO_PUBLIC_KEY = os.getenv(
    "MERCADOPAGO_PUBLIC_KEY",
    "APP_USR-047e3cad-def8-4095-90eb-0c7f17c41f66"
)
MERCADOPAGO_ACCESS_TOKEN = os.getenv(
    "MERCADOPAGO_ACCESS_TOKEN",
    "APP_USR-8930969594811512-090621-dae49d97322647d22509cb48b959867c-217387767"
)
MERCADOPAGO_CLIENT_ID = os.getenv("MERCADOPAGO_CLIENT_ID", "8930969594811512")
MERCADOPAGO_CLIENT_SECRET = os.getenv("MERCADOPAGO_CLIENT_SECRET", "vpxjHw2HXIJKKeFtcZSrGY4iMEOUDr8I")

# Dados do Lenon para transfers
LENON_EMAIL = os.getenv("LENON_EMAIL", "lenonms543@gmail.com")
LENON_CPF = os.getenv("LENON_CPF", "01800818106")
LENON_USER_ID = os.getenv("LENON_USER_ID", "217387767")
TAXA_PLATAFORMA = float(os.getenv("TAXA_PLATAFORMA", "0.00"))

MERCADOPAGO_WEBHOOK_SECRET = os.getenv(
    "MERCADOPAGO_WEBHOOK_SECRET",
    "edbd5177af11d0917d78100f19e5f819694608d6c12d82355fb05037b6b536b5"
)

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'rifa': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}
