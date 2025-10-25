from django.core.management.base import BaseCommand

from ...services.tasks import *
from ...services.tasks.commands import *


class Command(BaseCommand):
    @add_cron_arguments
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        schedule = validate_cron(options)
        task_name = f'VETURILO_UPDATING'
        task_path = 'Tasker.tasks.update_veturilo_data',
        status, text = create_periodic_task(schedule, task_name, task_path)
        print_task_status(self, status, text)