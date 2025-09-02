from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask


class Command(BaseCommand):
    help = "Показує усі існуючі завдання на оновлення gtfs"

    def handle(self, *args, **options):
        tasks = PeriodicTask.objects.filter(name__istartswith='GTFS')
        for num, task in enumerate(tasks, 1):
            print(f'{num}) {task.name} ({task.crontab})')
        
            
