from django.core.management.base import BaseCommand
from ...models.staging import *


class Command(BaseCommand):
    help = "Повністю очищує усі таблиці пов'язані з даними розкладу та перевізників"

    def add_arguments(self, parser):
        parser.add_argument('-s', type=bool,
                            help='Булевий аргумент, вказуючий чистити Staging таблиці чи звичайні')

    def handle(self, *args, **options):
        model = CarrierStaging if options['s'] else Carrier
        staging_str = 'Staging ' if options['s'] else ''

        self.stdout.write('Триває процес очищення бази даних...')
        try:
            model.objects.all().delete()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Неможливо очистити таблицю {model}:\n{e}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Таблиці {staging_str}успішно очищено!'))

    
        
        
        
        
        
        