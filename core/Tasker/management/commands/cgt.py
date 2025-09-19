import json

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule

from ...services.tasks.gtfs import *


class Command(BaseCommand):
    help = "Tworzy zadania periodyczne GTFS dla wszystkich agencji"

    def add_arguments(self, parser):
        parser.add_argument('carrier', type=str, nargs=1,
                            help='Перевізник, для котрого створиться завдання.')
        parser.add_argument('--minute', '-m', type=str, nargs=1, default='*/5')
        parser.add_argument('--hour', '-H', type=str, nargs=1, default='*')
        parser.add_argument('--day_of_month', '-D', type=str, nargs=1, default='*')
        parser.add_argument('--month_of_year', '-M', type=str, nargs=1, default='*')
        parser.add_argument('--day_of_week', '-W', type=str, nargs=1, default='*')

    def handle(self, *args, **options):
        name, cron = validate_command_args(options)
        schedule, _ = CrontabSchedule.objects.get_or_create(**cron)

        task_name = f'GTFS_UPDATING_{name}'
        task, created = PeriodicTask.objects.get_or_create(
            crontab=schedule,
            name=task_name,
            task='Tasker.tasks.update_gtfs',
            args=json.dumps([name])
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Таск для перевізника {name} створено!'))
        else:
            self.stdout.write(self.style.WARNING(f'Таск для перевізника {name} уже існує!'))
