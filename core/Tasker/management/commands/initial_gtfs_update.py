from django.core.management.base import BaseCommand

from ...tasks import check_gtfs_updates


class Command(BaseCommand):
    help = "Task that updates GTFS data and runs only at the start of the container"
    def handle(self, *args, **options):
        check_gtfs_updates.apply_async()