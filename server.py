import redis.asyncio as aioredis
import trio
import trio_asyncio
from pydantic import ValidationError
from quart import render_template, websocket, request
from quart_trio import QuartTrio

from classes import Settings, Message, SendingResult, DbWrapper, SmsMailing
from hypercorn.trio import serve
from hypercorn.config import Config as HyperConfig
from smsc_api import SMSSender

app = QuartTrio(__name__)
PHONES = [
    '79371752458',
    '112',
    '911',
    '900'
]


@app.get("/")
async def index():
    return await render_template("index.html")


@app.post("/send/")
async def send():
    db = app.db_pool

    form = await request.form
    try:
        msg = Message.model_validate(form)
    except ValidationError:
        return {
            "errorMessage": "Wrong data format"
        }

    sending_result = await app.sms_sender.send_sms(PHONES, msg.text[0])
    try:
        sending_result = SendingResult.model_validate(sending_result)
    except ValidationError:
        return {
            "errorMessage": "Service error"
        }

    await db.add_sms_mailing(str(sending_result.id), PHONES, msg.text[0])
    sms_mailings = await db.get_sms_mailings(str(sending_result.id))

    return sms_mailings


@app.websocket("/ws")
async def ws() -> None:
    db = app.db_pool
    while True:
        sms_ids = await db.list_sms_mailings()
        sms_mailings = [
            SmsMailing.model_validate(sms_mailing)
            for sms_mailing in await db.get_sms_mailings(*sms_ids)
        ]
        await websocket.send_json({
            "msgType": "SMSMailingStatus",
            "SMSMailings": [
                {
                    "timestamp": sms_mailing.created_at,
                    "SMSText": sms_mailing.text,
                    "mailingId": sms_mailing.sms_id,
                    "totalSMSAmount": len(sms_mailing.phones),
                    "deliveredSMSAmount": sms_mailing.count_phones_by_status('delivered'),
                    "failedSMSAmount": sms_mailing.count_phones_by_status('failed')
                }
                for sms_mailing in sms_mailings
            ]
        })
        await trio.sleep(1)


@app.before_serving
async def create_db_pool():
    settings = Settings()
    redis = aioredis.from_url(
        settings.redis_url,
        decode_responses=True
    )
    app.db_pool = DbWrapper(redis)
    app.sms_sender = SMSSender(
        login=settings.smsc_login,
        psw=settings.smsc_psw
    )


@app.after_serving
async def close_db_pool():
    await app.db_pool.redis.close()


async def run_server():
    async with trio_asyncio.open_loop():
        config = HyperConfig()
        config.bind = ['127.0.0.1:5000']
        config.use_reloader = True
        await serve(app, config)


if __name__ == '__main__':
    trio.run(run_server)
