from collections import defaultdict


def get_wtp_weekday(day_of_week:int) -> str:
    if day_of_week not in range(1, 8):
        raise ValueError('Weekday cannot be out of range from 1 to 7!')
    
    d = defaultdict(lambda: 'PcS')
    d.update({5:'PtS', 6:'SbS', 7:'NdS'})
    return d[day_of_week]
