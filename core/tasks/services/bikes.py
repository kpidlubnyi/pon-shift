import requests
import base64
from datetime import datetime

from django.conf import settings
from django.db import transaction
from django.utils import timezone as tz

from Bikes.models import *


   ############################
   ###       VETURILO       ###
   ############################

def fetch_veturilo_api():
    url = settings.NEXTBIKE_API_URL
    response = requests.get(url)
    response.raise_for_status()

    data = response.json().get('countries')[0].get('cities')[0]
    places = data.get('places')

    return places

def process_veturilo_data(places: list[dict]):
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
        
    processed_places = []

    for place in places:
        mode = 'bike' if place['bike'] else 'station'
        processed_places.append(get_necessary_data(place, mode))

    return processed_places

def delete_old_bike_data(*models):
    for model in models:
        model.objects.all().delete()

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
        delete_old_bike_data(VeturiloAloneBike, VeturiloStation)    
        VeturiloStation.objects.bulk_create(stations)
        VeturiloAloneBike.objects.bulk_create(bikes)

    return

   ############################
   ###      SCOOTERS        ###
   ############################

def fetch_dott_api() -> dict:
    resp = requests.get(settings.DOTT_SCOOTERS_API_URL)
    resp.raise_for_status()

    return resp.json()['data']['bikes']

def fetch_bolt_api() -> dict:
    url = settings.BOLT_SCOOTERS_API_URL
    device_id = settings.BOLT_DEVICE_ID
    phone = settings.BOLT_PHONE_NUMBER

    params = {
        'lat': '52.2297700',
        'lng': '21.0117800',
        'version': 'CI.203.0',
        'deviceId': device_id,
        'deviceType': 'iphone',
        'device_name':'IPhone12,1',
        'device_os_version':'IOS18.1.1',
        'language':'pl',
    }

    text = f'{phone}:{device_id}' 
    auth_value = base64.b64encode(text.encode('utf-8'))
    headers = {
        'Authorization':  auth_value
    }

    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    return data['data']['categories'][0]['vehicles']

def standardize_scooter_data(data: list[dict], mode: str = None) -> list[dict]:    
    def process_last_reported(timestamp: int):
        dt = datetime.fromtimestamp(timestamp)
        return tz.make_aware(dt)
    
    if not mode:
        mode = 'dott' if 'bike_id' in data[0].keys() else 'bolt'
    
    result = []
    company, _ = ScooterCompany.objects.get_or_create(company_name=mode)
    
    fields = [field.attname for field in Scooter._meta.fields if field.attname != 'company_id']
    field_mapping = {
        'dott': [
            'bike_id', 'lat', 'lon',
            'current_fuel_percent',
            'current_range_meters', 
            'is_disabled','last_reported'
        ],
        'bolt': [
            'id', 'lat','lng', 
            'charge',
            'distance_on_charge',
            None, None
        ]
    }
    
    mapping = {k: v for k,v in zip(fields, field_mapping[mode])}
    
    for vehicle in data:
        std_vehicle = dict()
        for model_field, api_field in mapping.items():
            if api_field and api_field in vehicle:
                std_vehicle[model_field] = vehicle[api_field]
            else:
                std_vehicle[model_field] = None
        
        if std_vehicle.get('last_reported'):
            std_vehicle['last_reported'] = process_last_reported(std_vehicle['last_reported'])
        
        std_vehicle['company'] = company
        result.append(std_vehicle)

    return result

@transaction.atomic
def import_scooter_data(data):
    delete_old_bike_data(Scooter)
    data = [Scooter(**scooter) for scooter in data]
    Scooter.objects.bulk_create(data)
