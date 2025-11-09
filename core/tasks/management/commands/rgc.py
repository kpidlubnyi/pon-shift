from django.core.management.base import BaseCommand

from ...services.commands import *
from ...tasks import check_gtfs_updates


class Command(BaseCommand):
    def handle(self, *args, **options):
        check_gtfs_updates.delay()
        self.stdout.write(
            self.style.SUCCESS(f'Runned GTFS update checker!')
        )
