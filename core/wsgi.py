import os
import sys

# Asegura que el directorio raíz del proyecto esté en el path
sys.path.append('/opt/bitnami/Repositories/WEB-AteneaGruneco')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()