import requests

from django.conf import settings

from ..redis import *

def fetch_recent_osm_hash():
    url = settings.OSM_META_URL
    md5 = requests.get(url).content.decode().split()[0]
    return md5 

def osm_is_new():
    osm_md5 = fetch_recent_osm_hash()
    redis_md5 = get_hash_from_redis('osm', 'md5')
    return osm_md5 != redis_md5
