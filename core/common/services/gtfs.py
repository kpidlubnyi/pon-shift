from django.utils import timezone as tz


def parse_gtfs_time(time:str) -> tz.timedelta:
    h, m, s = map(int, time.split(':'))
    extra_days, h = divmod(h, 24)
    return tz.timedelta(days=extra_days, hours=h, minutes=m, seconds=s)

def timedelta_to_str(td: tz.timedelta) -> str:
    total_seconds = int(td.total_seconds())
    total_seconds %= (24 * 3600)

    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60

    return f"{h:02d}:{m:02d}:{s:02d}"