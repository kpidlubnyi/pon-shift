from django.utils import timezone as tz


def parse_gtfs_time(time:str) -> tz.timedelta:
    h, m, s = map(int, time.split(':'))
    extra_days, h = divmod(h, 24)
    return tz.timedelta(days=extra_days, hours=h, minutes=m, seconds=s)
