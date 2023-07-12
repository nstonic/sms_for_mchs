from typing import Optional

from pydantic import BaseModel
from pydantic_settings import BaseSettings
from trio_asyncio import aio_as_trio

from db import Database


class Settings(BaseSettings):
    smsc_login: str
    smsc_psw: str
    redis_url: str

    class Config:
        env_file = '.env'


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


class DbWrapper(Database):

    @aio_as_trio
    async def add_sms_mailing(self, sms_id: str, phones: list, text: str, created_at: Optional[float] = None):
        await super().add_sms_mailing(sms_id, phones, text, created_at)

    @aio_as_trio
    async def get_pending_sms_list(self):
        return await super().get_pending_sms_list()

    @aio_as_trio
    async def update_sms_status_in_bulk(self, sms_list):
        await super().update_sms_status_in_bulk(sms_list)

    @aio_as_trio
    async def get_sms_mailings(self, *sms_ids: str) -> list:
        return await super().get_sms_mailings(*sms_ids)

    @aio_as_trio
    async def list_sms_mailings(self):
        return await super().list_sms_mailings()
