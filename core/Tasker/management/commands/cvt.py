
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule

from ...services.tasks import *
from ...services.tasks.commands import *


class Command(BaseCommand):
    @add_cron_arguments
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        cron = process_cron(options)
        schedule, _ = CrontabSchedule.objects.get_or_create(**cron)
        task_name = f'VETURILO_UPDATING'

        task, created = PeriodicTask.objects.get_or_create(
            crontab=schedule,
            name=task_name,
            task='Tasker.tasks.update_veturilo_data',
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Task for updating Veturilo data created!'))
        else:
            self.stdout.write(self.style.WARNING(f'The task to update Veturilo data already exists.!'))
