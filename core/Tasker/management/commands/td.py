from django.core.management.base import BaseCommand
from ...models.staging import *


class Command(BaseCommand):
    help = "Completely cleans all tables related to schedule data and carriers"

    def add_arguments(self, parser):
        parser.add_argument('-s', type=bool,
                            help='Boolean argument indicating whether to clean up staging tables or regular tables')

    def handle(self, *args, **options):
        model = CarrierStaging if options['s'] else Carrier
        staging_str = 'Staging ' if options['s'] else ''

        self.stdout.write('The database cleanup process is ongoing....')
        try:
            model.objects.all().delete()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Unable to clear table {model}:\n{e}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Tables {staging_str} successfully cleared!'))

    
        
        
        
        
        
        