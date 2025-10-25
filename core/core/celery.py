from celery import Celery
from kombu import Queue
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

app = Celery('core')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.task_queues = (
    Queue('default'),
    Queue('gtfs_updates'),
)

app.conf.task_default_queue = 'default'
