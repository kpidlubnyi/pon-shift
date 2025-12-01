import redis
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
            return None
    return wrapper


@redis_operation
def set_hash_in_redis(hash_to_redis:str, carrier:str, suffix:str = 'sha1'):
    key = f'{carrier}_{suffix}'
    return redis_client.set(key, hash_to_redis)


@redis_operation
def get_hash_from_redis(carrier:str, suffix:str = 'sha1'):
    key = f'{carrier}_{suffix}'
    hash_from_redis = redis_client.get(key)

    if not hash_from_redis:
        set_hash_in_redis('initial value', carrier, suffix)
        return get_hash_from_redis(carrier, suffix)
    else:
        return hash_from_redis


@redis_operation     
def remove_from_redis(key):
    if redis_client.get(key):
        redis_client.delete(key)
