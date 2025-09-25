from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask

from ...services.tasks.gtfs import validate_carrier


class Command(BaseCommand):
    help = "Видаляє завдання оновлення GTFS для вибраного перевізника"
    
    def add_arguments(self, parser):
        parser.add_argument('carrier', type=str, nargs=1)
        parser.add_argument('-r', '--realtime', action='store_true')

    def handle(self, *args, **options):
        carrier = validate_carrier(options)
        is_realtime = options['realtime']
        task_name = f'GTFS_UPDATING_{carrier}'
        task_name += '_RT' if is_realtime else ''
        realtime_str = 'realtime ' if is_realtime else ''

        try:
            periodic_task = PeriodicTask.objects.get(name=task_name)
        except PeriodicTask.DoesNotExist:
            self.stdout.write(self.style.WARNING(f'{carrier}: {realtime_str}таск для цього перевізника не існує'))
            return


        crontab = periodic_task.crontab
        periodic_task.delete()
        self.stdout.write(self.style.SUCCESS(f'Таск {realtime_str}для перевізника {carrier} успішно видалено!'))

        if crontab.periodictask_set.exists():
            return
        
        crontab.delete()
        self.stdout.write(self.style.SUCCESS(f'Розклад {crontab} усунено!'))

        
            
