import json
from functools import wraps

from django_celery_beat.models import PeriodicTask, CrontabSchedule


def add_cron_arguments(func):
    @wraps(func)
    def wrapper(self, parser):
        result = func(self, parser)
        
        parser.add_argument('--minute', '-m', type=str, default='*/5', 
                            help='Minute (default: */5)')
        parser.add_argument('--hour', '-H', type=str, default='*',
                            help='Hour (default: *)')
        parser.add_argument('--day_of_month', '-D', type=str, default='*',
                            help='Day of the month (default: *)')
        parser.add_argument('--month_of_year', '-M', type=str, default='*',
                            help='Month of the year (default: *)')
        parser.add_argument('--day_of_week', '-W', type=str, default='*',
                            help='Day of the week (default: *)')
        return result
    return wrapper

def create_gtfs_periodic_task(schedule: CrontabSchedule, name: str, realtime: bool = False):
    task_name = f'GTFS_UPDATING_{name}'
    task_name += '_RT' if realtime else ''

    task = 'Tasker.tasks.update_gtfs'
    task += '_realtime' if realtime else ''

    task, created = PeriodicTask.objects.get_or_create(
        crontab=schedule,
        name=task_name,
        task=task,
        args=json.dumps([name])
    )

    return created