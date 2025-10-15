from django.core.management.base import BaseCommand
from django.conf import settings

from Tasker.tasks import update_gtfs


class Command(BaseCommand):
    help = 'Execute all GTFS tasks immediately after launching the Docker'

    def handle(self, *args, **kwargs):
        for carrier in settings.ALLOWED_CARRIERS:
            update_gtfs.apply(args=[carrier])
        self.stdout.write(self.style.SUCCESS('Tasks successfully executed!'))
