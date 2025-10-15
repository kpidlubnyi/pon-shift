from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule

from ...services.tasks.gtfs import *
from ...services.tasks.commands import *


class Command(BaseCommand):
    help = "Creates a periodic task to update the data of the specified carrier"

    @add_cron_arguments
    def add_arguments(self, parser):
        parser.add_argument('carrier', type=str, nargs=1,
                            help='The carrier for whom the task will be created.')
        parser.add_argument('-r', action='store_true',
                            help='Boolean argument indicating whether to create a realtime task for this carrier')

    def handle(self, *args, **options):
        name, cron = validate_command_args(options)
        schedule, _ = CrontabSchedule.objects.get_or_create(**cron)

        is_realtime = options['r']
        created = create_gtfs_periodic_task(schedule, name, is_realtime)
        
        realtime_str = 'realtime ' if is_realtime else ''
        if created:
            self.stdout.write(self.style.SUCCESS(f'Task {realtime_str}for {name} carrier created!'))
        else:
            self.stdout.write(self.style.WARNING(f'Task {realtime_str}for {name} carrier already exists!'))
