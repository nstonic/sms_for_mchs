import asyncio

import redis.asyncio as aioredis
import trio
import trio_asyncio

from trio_asyncio import aio_as_trio

from classes import DbWrapper


async def main(redis_url: str, phones: list, sms_id: str, sms_text: str):
    redis = aioredis.from_url(
        redis_url,
        decode_responses=True)

    try:
        db = DbWrapper(redis)

        await db.add_sms_mailing(sms_id, phones, sms_text)

        sms_ids = await db.list_sms_mailings()
        print('Registered mailings ids', sms_ids)

        pending_sms_list = await db.get_pending_sms_list()
        print('pending:')
        print(pending_sms_list)

        await db.update_sms_status_in_bulk([
            # [sms_id, phone_number, status]
            [sms_id, '112', 'failed'],
            [sms_id, '911', 'pending'],
            [sms_id, '+7 999 519 05 57', 'delivered'],
            # following statuses are available: failed, pending, delivered
        ])

        pending_sms_list = await db.get_pending_sms_list()
        print('pending:')
        print(pending_sms_list)

        sms_mailings = await db.get_sms_mailings('1')
        print('sms_mailings')
        print(sms_mailings)

        @aio_as_trio
        async def send():
            while True:
                await asyncio.sleep(1)
                await redis.publish('updates', sms_id)

        @aio_as_trio
        async def listen():
            channel = redis.pubsub()
            await channel.subscribe('updates')

            while True:
                message = await channel.get_message(ignore_subscribe_messages=True, timeout=1.0)

                if not message:
                    continue

                print('Got message:', repr(message['data']))

        async with trio.open_nursery() as nursery:
            nursery.start_soon(send)
            nursery.start_soon(listen)

    finally:
        await redis.close()


if __name__ == '__main__':
    trio_asyncio.run(
        main,
        'redis://default:JLsi7hFmAZthHXkHc3lVEItq63yQltwG@redis-12377.c73.us-east-1-2.ec2.cloud.redislabs.com:12377'
    )
