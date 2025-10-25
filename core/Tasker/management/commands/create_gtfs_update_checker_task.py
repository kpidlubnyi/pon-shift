from django.core.management.base import BaseCommand

from ...services.tasks.commands import *
from ...services.tasks.gtfs import validate_cron


class Command(BaseCommand):
    help = 'Creates GTFS checker for all carriers immediately after launching the Docker'

    @add_cron_arguments
    def add_arguments(self, parser):
        parser.add_argument('-r', action='store_true',
                    help='Boolean argument indicating whether to create a realtime updater')

    def handle(self, *args, **options):
        schedule = validate_cron(options)
        task_name = "GTFS_UPDATE_CHECKER"
        task_path = 'Tasker.tasks.check_gtfs_updates'
        
        status, text = create_periodic_task(schedule, task_name, task_path)
        print_task_status(self, status, text)
