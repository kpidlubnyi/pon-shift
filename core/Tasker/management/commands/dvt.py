from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask


class Command(BaseCommand):
    help = "Removes Veturilo update tasks"

    def handle(self, *args, **options):
        try:
            periodic_task = PeriodicTask.objects.get(name__istartswith='VETURILO')
        except PeriodicTask.DoesNotExist:
            self.stdout.write(self.style.WARNING('There is no task to update Veturilo data.!'))
            return

        periodic_task.delete()
        self.stdout.write(self.style.SUCCESS(f'The task to update Veturilo data has been deleted.!'))
