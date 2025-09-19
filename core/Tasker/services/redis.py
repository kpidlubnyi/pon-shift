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
    """Декоратор для операцій в Редісі"""
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
def set_sha_in_redis(sha, carrier):
    key = f'{carrier}_sha1'
    return redis_client.set(key, sha)

@redis_operation
def get_redis_sha(carrier):
    key = f'{carrier}_sha1'
    sha = redis_client.get(key)

    if not sha:
        set_sha_in_redis('initial value', carrier)
        return get_redis_sha(carrier)
    else:
        return sha
        

