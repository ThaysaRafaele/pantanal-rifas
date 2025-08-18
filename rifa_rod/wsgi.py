"""
WSGI config for rifa_rod project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rifa_rod.settings')

application = get_wsgi_application()
