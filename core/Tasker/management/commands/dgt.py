from django.core.management.base import BaseCommand, CommandError
from django_celery_beat.models import PeriodicTask, CrontabSchedule

from ...services.task import validate_carrier


class Command(BaseCommand):
    help = "Видаляє завдання оновлення GTFS для вибраного перевізника"
    
    def add_arguments(self, parser):
        parser.add_argument('carrier', type=str, nargs=1, default='ztm')

    def handle(self, *args, **options):
        carrier = validate_carrier(options)
        task_name = f'GTFS_UPDATING_{carrier}'

        try:
            periodic_task = PeriodicTask.objects.get(name=task_name)
        except PeriodicTask.DoesNotExist:
            self.stdout.write(self.style.WARNING(f'{carrier}: завдання для цього перевізника не існує'))
            return


        crontab = periodic_task.crontab
        periodic_task.delete()
        self.stdout.write(self.style.SUCCESS(f'Таск для перевізника {carrier} успішно видалено!'))

        if crontab.periodictask_set.exists():
            return
        
        crontab.delete()
        self.stdout.write(self.style.SUCCESS(f'Розклад {crontab} усунено!'))

        
            
