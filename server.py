import asyncio
from datetime import datetime
from typing import NoReturn
from unittest.mock import patch

from environs import Env
from pydantic import BaseModel, ValidationError
from quart import Quart, render_template, websocket, request

from broker import Broker
from smsc_api import SMSSender

app = Quart(__name__)
broker = Broker()
env = Env()
env.read_env()
sms_sender = SMSSender(
    login=env('SMSC_LOGIN'),
    psw=env('SMSC_PSW')
)
PHONES = ['79371752458']


class Message(BaseModel):
    text: list[str]


class SendingResult(BaseModel):
    id: int
    cnt: int


class SendingStatus(BaseModel):
    Status: int
    check_time: str
    send_date: str
    phone: str
    cost: float
    sender_id: str
    status_name: str
    message: int
    type: int


@app.get("/")
async def index():
    return await render_template("index.html")


@app.post("/send/")
async def send():
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

    result = await sms_sender.send_sms(PHONES, msg.text[0])
    try:
        result = SendingResult.model_validate(result)
    except ValidationError:
        return {
            "errorMessage": "Service error"
        }
    else:
        return {
            "msgType": "SMSMailingStatus",
            "SMSMailings": [
                {
                    "timestamp": datetime.now().timestamp(),
                    "SMSText": msg.text,
                    "mailingId": result.id,
                    "totalSMSAmount": result.cnt,
                    "deliveredSMSAmount": 0,
                    "failedSMSAmount": 0,
                }
            ]
        }


async def _receive() -> NoReturn:
    while True:
        message = await websocket.receive()
        await broker.publish(message)


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


if __name__ == '__main__':
    app.run(debug=True)
