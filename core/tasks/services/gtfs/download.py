import requests
import io
import zipfile

from django.conf import settings
from common.services.redis import get_hash_from_redis

def get_from_feed(feed, key):
    return feed.get('feeds')[0].get('feed_versions')[0].get(key)

def get_recent_feed(carrier: str):  
    onestop_id = settings.ONESTOP_IDS[carrier]
    api_key = settings.TRANSITLAND_API_KEY
    url = f'https://transit.land/api/v2/rest/feeds?onestop_id={onestop_id}&api_key={api_key}'

    feed = requests.get(url)
    feed.raise_for_status()

    return feed.json()

def is_feed_new(feed, carrier:str):
    redis_sha = get_hash_from_redis(carrier)
    feed_sha = get_from_feed(feed, 'sha1')

    return feed_sha != redis_sha

def get_gtfs(feed):
    url = get_from_feed(feed, 'url')
    return requests.get(url).content

def fetch_gtfs_zip(gtfs_zip) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(gtfs_zip))

