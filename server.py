import asyncio
from datetime import datetime

import redis.asyncio as aioredis
from pydantic import ValidationError
from quart import Quart, render_template, websocket, request

from classes import Settings, Message, SendingResult, DbWrapper
from redis_client import RedisClient
from smsc_api import SMSSender

app = Quart(__name__)
PHONES = [
    '79371752458',
    '911',
    '112',
]


@app.get("/")
async def index():
    return await render_template("index.html")


@app.post("/send/")
async def send():
    redis = RedisClient()
    db = DbWrapper(redis)

    form = await request.form
    # with patch('__main__.SMSSender') as mock:
    #     instance = mock.return_value
    #     instance.send_sms.return_value = {
    #         "id": 366,
    #         "cnt": 1
    #     }
    #     sms_sender = SMSSender(
    #         login=env('SMSC_LOGIN'),
    #         psw=env('SMSC_PSW')
    #     )
    #     result = sms_sender.send_sms(PHONES, form['text'])
    try:
        msg = Message.model_validate(form)
    except ValidationError:
        return {
            "errorMessage": "Wrong data format"
        }

    sending_result = await SMSSender().send_sms(PHONES, msg.text[0])
    try:
        sending_result = SendingResult.model_validate(sending_result)
    except ValidationError:
        return {
            "errorMessage": "Service error"
        }

    try:
        await db.add_sms_mailing(str(sending_result.id), PHONES, msg.text[0])
    finally:
        await redis.client.close()

    await websocket.send_json({
        "msgType": "SendingReport",
        "SMSMailings": [
            {
                "timestamp": datetime.now().timestamp(),
                "SMSText": msg.text,
                "mailingId": sending_result.id,
                "totalSMSAmount": sending_result.cnt,
                "deliveredSMSAmount": 0,
                "failedSMSAmount": 0,
            }
        ]
    })


@app.websocket("/ws")
async def ws() -> None:
    for i in range(100):
        await websocket.send_json({
            "msgType": "SMSMailingStatus",
            "SMSMailings": [
                {
                    "timestamp": 1123131392.734,
                    "SMSText": "Сегодня гроза! Будьте осторожны!",
                    "mailingId": "1",
                    "totalSMSAmount": 100,
                    "deliveredSMSAmount": i,
                    "failedSMSAmount": 0,
                },
                {
                    "timestamp": 1323141112.924422,
                    "SMSText": "Новогодняя акция!!! Приходи в магазин и получи скидку!!!",
                    "mailingId": "new-year",
                    "totalSMSAmount": 100,
                    "deliveredSMSAmount": i,
                    "failedSMSAmount": 0,
                },
            ]
        })
        await asyncio.sleep(1)


def main():
    settings = Settings()
    SMSSender(
        login=settings.smsc_login,
        psw=settings.smsc_psw
    )
    RedisClient(
        redis_url=settings.redis_url
    )
    app.run(debug=True)


if __name__ == '__main__':
    main()
