from django.core.management.base import BaseCommand
from ...models.common import *


class Command(BaseCommand):
    help = "Повністю очищує усі таблиці пов'язані з даними розкладу та перевізників"

    def handle(self, *args, **options):
        primary_models = (CalendarDate, Route, Shape, Stop)

        self.stdout.write('Триває процес очищення бази даних...')
        try:
            for model in primary_models:
                model.objects.all().delete()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Неможливо очистити таблицю {model}:\n{e}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'База даних успішно очищена!'))

    
        
        
        
        
        
        