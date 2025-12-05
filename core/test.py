import requests
from bs4 import BeautifulSoup
import re
import itertools
from common.models import Route

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Referer": "https://google.com",
    "Upgrade-Insecure-Requests": "1",
}

def get_soups_for_route(date, route):
    for directions in {'A', 'B'}:
        url = 'https://www.wtp.waw.pl/rozklady-jazdy'
        params = {'wtp_dt':date, 'wtp_md':'3', 'wtp_ln':route, 'wtp_dr':directions}

        response = requests.get(url,headers=HEADERS, params=params)
        
        soup = BeautifulSoup(response.text, 'lxml')
        url:str = soup.find('a', class_='timetable-link timetable-route-point name active follow').attrs['href']
        
        response = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(response.text, 'lxml')
        yield soup


def parse_tt_annotations_from_soup(soup):
    timetable = soup.find('ul', class_='timetable-time')
    timetable_minutes = timetable.find_all('a', class_=re.compile(r'timetable-minute'))
    tt_labels = [tt.attrs['aria-label'] for tt in timetable_minutes]
    tt_labels = [tt_label.split(' ', maxsplit=1)[1] for tt_label in tt_labels]

    annotations = soup.find_all('div', class_='timetable-annotations-symbol')
    
    for i, an in enumerate(annotations):
        symbol = an.find('div', class_='timetable-annotations-symbol-key')

        if icon:=symbol.find('i'):
            symbol = icon.attrs['class']
        else:
            symbol = symbol.text

        desc = an.find('div', class_='timetable-annotations-symbol-val').text
        annotations[i] = f'{symbol} - {desc}'

    return annotations

routes = Route.objects.filter(carrier_id='5').values_list('route_id', flat=True)
routes = [route.split(':')[1] for route in routes]
dates = ['2025-12-05', '2025-12-06', '2025-12-07']

print('Start!!')
print(f'Count of routes to take info from: {len(routes)}')

annotations = list()
for route, date in itertools.product(routes, dates):
    print(f'Getting for route "{route}" and date "{date}"')
    try:
        for soup in get_soups_for_route(date, route):
            annotations += parse_tt_annotations_from_soup(soup)
    except Exception as e:
        print(f'Помилка під час парсингу анотації для рейсу {route} в {date}: {e}')
        continue


annotations = set(annotations)

with open('ans.txt', 'w') as f:
    f.write('\n'.join(annotations))

