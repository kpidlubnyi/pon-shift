from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask
from django.db.models import Q

class Command(BaseCommand):
    help = "Shows all existing update tasks"

    def handle(self, *args, **options):
        task_filter = (
            Q(name__istartswith='GTFS') | 
            Q(name__istartswith='VETURILO')
        )
        tasks = PeriodicTask.objects.filter(task_filter)
        for num, task in enumerate(tasks, 1):
            print(f'{num}) {task.name} ({task.crontab})')
        
            
