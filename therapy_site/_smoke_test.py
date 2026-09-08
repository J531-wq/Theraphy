import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'therapy_site.settings')
django.setup()
from django.conf import settings
settings.ALLOWED_HOSTS.append('testserver')

from django.test import Client
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.models import update_last_login
user_logged_in.disconnect(update_last_login)

from core.models import User