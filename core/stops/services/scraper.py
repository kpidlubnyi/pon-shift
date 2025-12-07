import requests
from bs4 import BeautifulSoup

from django.conf import settings


HEADERS = {
    "User-Agent": settings.SCRAPER_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Referer": "https://google.com",
    "Upgrade-Insecure-Requests": "1",
}

HIGH_FLEET_SYMBOL = '[]'
HIGH_FLEET_ANNOTATION = 'kurs pojazdem z wysoką podłogą'


def get_soup_for_route(stop_id:str, date:str, route:str):
    url = 'https://www.wtp.waw.pl/rozklady-jazdy'

    stop_params = {'wtp_st': stop_id[:4]}
    stop_params['wtp_pt'] = '80' if len(stop_id) == 4 else stop_id[4:6]  # WTP stops for trains have 4-digit stop_id
    route = route.split(':')[1]
    
    params = {
        'wtp_dt':date, 'wtp_md':'5', 
        'wtp_ln':route, 'wtp_lm': '1',
    }
    params.update(stop_params)

    response = requests.get(url,headers=HEADERS, params=params)
    soup = BeautifulSoup(response.text, 'lxml')
    return soup
