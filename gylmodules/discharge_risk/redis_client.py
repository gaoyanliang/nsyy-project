import redis

from .config import REDIS_URL

redis_client = redis.from_url(REDIS_URL, decode_responses=True, protocol=2)


def acquire_lock(key: str, expire: int = 600) -> bool:
    return bool(redis_client.set(key, "1", nx=True, ex=expire))


def release_lock(key: str):
    redis_client.delete(key)


def clear_stat_cache():
    for k in redis_client.scan_iter("stat:daily:*"):
        redis_client.delete(k)