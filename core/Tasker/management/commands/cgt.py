import json

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule

from ...services.tasks.gtfs import *

def create_periodic_task(schedule: CrontabSchedule, name: str, realtime: bool = False):
    task_name = f'GTFS_UPDATING_{name}'
    task_name += '_RT' if realtime else ''

    task = 'Tasker.tasks.update_gtfs'
    task += '_realtime' if realtime else ''

    task, created = PeriodicTask.objects.get_or_create(
        crontab=schedule,
        name=task_name,
        task=task,
        args=json.dumps([name])
    )

    return created

class Command(BaseCommand):
    help = "Tworzy zadania periodyczne GTFS dla wszystkich agencji"

    def add_arguments(self, parser):
        parser.add_argument('carrier', type=str, nargs=1,
                            help='Перевізник, для котрого створиться завдання.')
        parser.add_argument('-r', action='store_true',
                            help='Булевий аргумент, вказуючий чи створити realtime таску для даного перевізника')
        parser.add_argument('--minute', '-m', type=str, nargs=1, default='*/5')
        parser.add_argument('--hour', '-H', type=str, nargs=1, default='*')
        parser.add_argument('--day_of_month', '-D', type=str, nargs=1, default='*')
        parser.add_argument('--month_of_year', '-M', type=str, nargs=1, default='*')
        parser.add_argument('--day_of_week', '-W', type=str, nargs=1, default='*')

    def handle(self, *args, **options):
        name, cron = validate_command_args(options)
        schedule, _ = CrontabSchedule.objects.get_or_create(**cron)

        is_realtime = options['r']
        created = create_periodic_task(schedule, name, is_realtime)
        
        realtime_str = 'realtime ' if is_realtime else ''
        if created:
            self.stdout.write(self.style.SUCCESS(f'Таск {realtime_str}для перевізника {name} створено!'))
        else:
            self.stdout.write(self.style.WARNING(f'Таск {realtime_str}для перевізника {name} уже існує!'))
