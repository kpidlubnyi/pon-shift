import json
import logging
from functools import wraps
from enum import StrEnum

from django_celery_beat.models import PeriodicTask, CrontabSchedule, IntervalSchedule
from django.core.management.base import BaseCommand


logger = logging.getLogger(__name__)


def add_crontab_arguments(func):
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

def add_interval_arguments(func):
    @wraps(func)
    def wrapper(self, parser):
        result = func(self, parser)
        
        parser.add_argument('--every', '-e', type=int, default=15,
                            help='Interval value (default: 15)')
        
        parser.add_argument('--period', '-p', type=str,
            choices=['seconds', 'minutes', 'hours', 'days', 'weeks'],
            default='seconds',
            help='Interval period (default: seconds)'
        )
        
        return result
    return wrapper

class TaskCreationStatus(StrEnum):
    CREATED = 'created'
    EXISTS = 'exists'
    FAILED = 'failed'

def create_periodic_task(
        schedule: CrontabSchedule | IntervalSchedule, 
        task_name: str, 
        task_path: str, 
        *args) -> tuple[TaskCreationStatus, str]:
    
    match schedule:
        case CrontabSchedule():
            sch_key = 'crontab'
        case IntervalSchedule():
            sch_key = 'interval'
   
    try:
        _, created = PeriodicTask.objects.get_or_create(
            **{sch_key: schedule},
            name=task_name,
            task=task_path,
            args=json.dumps(args)
        )

        if created:
            logger.info(text:=f'Periodic task {task_name} created successfully!')
            return TaskCreationStatus.CREATED, text 

        logger.warning(text:=f'Periodic task {task_name} already exists!')
        return TaskCreationStatus.EXISTS, text 
 
    except Exception as e:
        logger.exception(text:=f'Error while creating a {task_name} periodic task: {e}')
        return TaskCreationStatus.FAILED, text
    
def print_task_status(command: BaseCommand, status: TaskCreationStatus, text: str) -> None:
    style_map = {
        TaskCreationStatus.CREATED: command.style.SUCCESS,
        TaskCreationStatus.EXISTS: command.style.WARNING,
        TaskCreationStatus.FAILED: command.style.ERROR
    }
    
    styled_text = style_map.get(status, command.style.NOTICE)(text)
    command.stdout.write(styled_text)

def create_gtfs_periodic_task(carrier: str, schedule: CrontabSchedule):
    task_name = f'GTFS_UPDATING_{carrier}'
    task_path = 'tasks.tasks.update_gtfs'

    status, text = create_periodic_task(schedule, task_name, task_path)
    return status, text

def create_gtfs_rt_periodic_task(feed_name: str, interval:IntervalSchedule):
    task_name = f'GTFS_UPDATING_{feed_name}_RT'
    task_path = 'tasks.tasks.update_gtfs_realtime'

    status, text = create_periodic_task(interval, task_name, task_path, feed_name)
    return status, text
