from django.core.management.base import BaseCommand
from django.conf import settings

from ...services.commands import *
from ...services.gtfs.tasks import validate_interval

class Command(BaseCommand):
    help = 'Creates GTFS-RT updater for all carriers immediately after launching the Docker'

    @add_interval_arguments
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        interval = validate_interval(options)

        if interval:
            for feed_name in settings.SERVED_FEEDS:
                if "_RT_" in feed_name:
                    status, text = create_gtfs_rt_periodic_task(feed_name, interval)
                    print_task_creation_status(self, status, text)