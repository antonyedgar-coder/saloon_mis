import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "saloon_mis.settings")

application = get_wsgi_application()
