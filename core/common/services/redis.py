import redis
import json
from typing import Generator

from django.conf import settings


try:
    redis_pool = redis.ConnectionPool.from_url(
        settings.REDIS,
        decode_responses=True,
        max_connections=64,
        retry_on_timeout=True,
        socket_keepalive=True,
        socket_keepalive_options={},
        socket_connect_timeout=5,    
        socket_timeout=5,          
        health_check_interval=30    
    )
    
    redis_client = redis.Redis(connection_pool=redis_pool)
    redis_client.ping()    
except Exception as e:
    redis_client = None
    redis_pool = None


def redis_operation(func):
    """Decorator for operations in Redis"""
    def wrapper(*args, **kwargs):
        if redis_client is None:
            return None
            
        try:
            return func(*args, **kwargs)
        except redis.ConnectionError as e:
            return None
        except redis.TimeoutError as e:
            return None
        except Exception as e:
            raise Exception(e)
    return wrapper


@redis_operation
def get_from_redis(key:str) -> str:
    return redis_client.get(key)


@redis_operation
def get_redis_keys_by_regexp(pattern: str) -> Generator[str, None, None]:
    return (key.decode() for key in redis_client.scan_iter(match=pattern))


@redis_operation
def get_json_data_from_redis(key:str) -> dict | None:
    data = get_from_redis(key)
    return json.loads(data) if data else None


@redis_operation
def get_stop_route_schedule_from_redis(stop_id:str, date:str, route:str) -> dict | None:
    from tasks.services.gtfs.models import split_value_with_carrier_prefix
    carrier, route_id = split_value_with_carrier_prefix(route)
    key = f'{carrier}_ROUTE_SCHEDULE_{stop_id}_{route_id}_{date}'

    if schedule := get_json_data_from_redis(key):
        return schedule
    return None


@redis_operation
def get_stop_list_from_redis() -> list[dict]:
    key = 'STOP_LIST'
    data = get_json_data_from_redis(key)
    return data


@redis_operation
def set_in_redis(key:str, value:str) -> None:
    try:
        assert redis_client.set(key, value)
    except Exception as e:
        raise Exception(f'Error while setting in Redis: {e}')
    

@redis_operation
def set_json_data_in_redis(key:str, data:dict) -> None:
    set_in_redis(key, json.dumps(data))
    

@redis_operation
def set_stop_route_schedule_in_redis(data: dict, stop_id:str, date:str, route:str) -> None:
    from tasks.services.gtfs.models import split_value_with_carrier_prefix
    carrier, route_id = split_value_with_carrier_prefix(route)
    key = f'{carrier}_ROUTE_SCHEDULE_{stop_id}_{route_id}_{date}'
    set_json_data_in_redis(key, data)


@redis_operation
def save_stops_in_redis(stops:list[dict]) -> None:
    key = 'STOP_LIST'
    set_json_data_in_redis(key, stops)


@redis_operation     
def remove_from_redis(*keys:str) -> None:
    redis_client.delete(*keys)


@redis_operation
def set_hash_in_redis(hash_to_redis:str, carrier:str, suffix:str = 'sha1') -> None:
    key = f'{carrier}_{suffix}'
    set_in_redis(key, hash_to_redis)


@redis_operation
def get_hash_from_redis(carrier:str, suffix:str = 'sha1') -> str:
    key = f'{carrier}_{suffix}'
    hash_from_redis = get_from_redis(key)

    if not hash_from_redis:
        set_hash_in_redis('initial value', carrier, suffix)
        return get_hash_from_redis(carrier, suffix)
    else:
        return hash_from_redis


@redis_operation
def recreate_redis_set(key: str, *values) -> bool:
    remove_from_redis(key)
    return bool(redis_client.sadd(key, *values))


@redis_operation
def is_in_redis_set(key: str, value: str) -> bool:
    return bool(redis_client.sismember(key, value))
