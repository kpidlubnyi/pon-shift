from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask

from ...services.tasks.gtfs import validate_carrier


class Command(BaseCommand):
    help = "Deletes GTFS update tasks for the selected carrier"
    
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
            self.stdout.write(self.style.WARNING(f'There is no task for {carrier}: {realtime_str}'))
            return


        crontab = periodic_task.crontab
        periodic_task.delete()
        self.stdout.write(self.style.SUCCESS(f'Task {realtime_str} for carrier {carrier} successfully deleted!'))

        if crontab.periodictask_set.exists():
            return
        
        crontab.delete()
        self.stdout.write(self.style.SUCCESS(f'Schedule {crontab} removed!'))

        
            
