import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "websentinel.settings")

app = Celery("websentinel")
# All Celery config lives in Django settings under the CELERY_ namespace.
app.config_from_object("django.conf:settings", namespace="CELERY")
# Discover tasks.py modules in every installed app.
app.autodiscover_tasks()
