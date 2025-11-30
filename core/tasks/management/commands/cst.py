
from django.core.management.base import BaseCommand

from ...services import *
from ...services.commands import *


class Command(BaseCommand):
    @add_crontab_arguments
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        schedule = validate_cron(options)
        task_name = f'SCOOTERS_UPDATING'
        task_path = 'tasks.tasks.update_scooter_data'
        status, text = create_periodic_task(schedule, task_name, task_path)
        print_task_creation_status(self, status, text)