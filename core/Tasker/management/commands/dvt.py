from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask


class Command(BaseCommand):
    help = "Видаляє завдання оновлення Veturilo"

    def handle(self, *args, **options):
        try:
            periodic_task = PeriodicTask.objects.get(name__istartswith='VETURILO')
        except PeriodicTask.DoesNotExist:
            self.stdout.write(self.style.WARNING('Таску на оновлення даних Veturilo не існує!'))
            return

        periodic_task.delete()
        self.stdout.write(self.style.SUCCESS(f'Таску на оновлення даних Veturilo видалено!'))
