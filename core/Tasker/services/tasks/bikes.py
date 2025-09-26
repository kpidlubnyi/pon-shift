import requests

from django.conf import settings
from django.db import transaction

from Bikes.models import *


def fetch_veturilo_api():
    url = settings.NEXTBIKE_API_URL
    response = requests.get(url)
    response.raise_for_status()

    data = response.json().get('countries')[0].get('cities')[0]
    places = data.get('places')

    return places

def get_necessary_data(place: dict, mode: str) -> dict:
    if mode not in {'station', 'bike'}:
        raise ValueError()
    
    fields = ['uid', 'lat', 'lng', 'name', 'number', 'bike']

    if mode == 'station':    
        fields += ['bikes_available_to_rent']
        return {field: place[field] for field in fields}
    else:
        result = {field: place[field] for field in fields}
        bike = place.get('bike_list')[0]

        bike_fields = ['bike_type', 'active', 'state']
        result.update({field: bike[field] for field in bike_fields})

        is_electric = result['bike_type'] == VeturiloAloneBike.BikeTypeChoice.ELECTRIC
        result['percentage'] = bike['battery_pack']['percentage'] if is_electric else None
        return result


def process_veturilo_data(places: list[dict]):
    processed_places = []

    for place in places:
        mode = 'bike' if place['bike'] else 'station'
        processed_places.append(get_necessary_data(place, mode))

    return processed_places

@transaction.atomic
def delete_old_veturilo_data():
    VeturiloAloneBike.objects.all().delete()
    VeturiloStation.objects.all().delete()

def split_veturilo_data(data):
    stations = []
    bikes = []

    for place in data:
        lst = bikes if place['bike'] else stations
        del place['bike']
        lst.append(place)

    return stations, bikes

def import_veturilo_data(data) -> None:
    stations, bikes = split_veturilo_data(data)

    stations = [VeturiloStation(**data) for data in stations]
    bikes = [VeturiloAloneBike(**data) for data in bikes]

    with transaction.atomic():    
        VeturiloStation.objects.bulk_create(stations)
        VeturiloAloneBike.objects.bulk_create(bikes)

    return