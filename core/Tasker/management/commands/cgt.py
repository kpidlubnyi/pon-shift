from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule

from ...services.tasks.gtfs import *
from ...services.tasks.commands import *


class Command(BaseCommand):
    help = "Tworzy zadania periodyczne GTFS dla wszystkich agencji"

    @add_cron_arguments
    def add_arguments(self, parser):
        parser.add_argument('carrier', type=str, nargs=1,
                            help='Перевізник, для котрого створиться завдання.')
        parser.add_argument('-r', action='store_true',
                            help='Булевий аргумент, вказуючий чи створити realtime таску для даного перевізника')

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
