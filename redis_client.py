import redis.asyncio as aioredis


class RedisClient:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, **kwargs):
        if not hasattr(self, 'client'):
            self.client = aioredis.from_url(
                kwargs['redis_url'],
                decode_responses=True
            )
