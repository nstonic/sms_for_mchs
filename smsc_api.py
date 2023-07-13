from json import JSONDecodeError

import asyncclick as click
import trio
from asks.sessions import Session


class SmscApiError(Exception):

    def __init__(self, errors: dict = None):
        self.error = errors.get('error', 'Unknown error')
        self.error_code = errors.get('error_code', 'Unknown error code')

    def __str__(self):
        return f'Error code: {self.error_code}. {self.error.capitalize()}'


def check_response(response):
    response.raise_for_status()
    try:
        errors = response.json()
    except JSONDecodeError:
        raise SmscApiError
    if 'error' in errors:
        raise SmscApiError(errors)


class SMSSender:

    def __init__(self, login, psw, connections=3):
        self.params = {
            'login': login,
            'psw': psw,
        }
        self.session = Session(
            connections=connections
        )

    async def send_sms(self, phones, msg, valid=1):
        params = self.params | {
            'valid': valid,
            'phones': ','.join(phones),
            'mes': msg,
            'fmt': 3
        }
        response = await self.session.get('https://smsc.ru/sys/send.php', params=params)
        check_response(response)
        return response.json()

    async def check_status(self, phone, msg_id, all_=1):
        params = self.params | {
            'phone': phone,
            'id': msg_id,
            'all': all_
        }
        response = await self.session.get('https://smsc.ru/sys/status.php', params=params)
        check_response(response)

    async def run(self, phones, msg, valid):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.send_sms, phones, msg, valid)


@click.command()
@click.argument('msg')
@click.argument('phones', nargs=-1)
@click.option('--login', help='Сообщение для отправки')
@click.option('--psw', help='Сообщение для отправки')
@click.option('--valid', default=1, help='Время жизни сообщения в часах', type=int)
def main(phones, msg, login, psw, valid):
    sender = SMSSender(login=login, psw=psw)
    trio.run(sender.run, phones, msg, valid)


if __name__ == '__main__':
    main(auto_envvar_prefix='SMSC')
