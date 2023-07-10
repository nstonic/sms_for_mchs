import asyncclick as click
import trio
from asks.sessions import Session


class SMSSender:

    def __init__(self, login: str, psw: str, valid: int, connections: int = 3):
        self.login = login
        self.psw = psw
        self.valid = valid
        self.session = Session(
            connections=connections
        )
        self.statuses = {}

    async def send_sms(self, phones, msg):
        params = {
            'login': self.login,
            'psw': self.psw,
            'valid': self.valid,
            'phones': ','.join(phones),
            'mes': msg,
            'fmt': 3
        }
        response = await self.session.get('https://smsc.ru/sys/send.php', params=params)
        response.raise_for_status()
        msg_id = response.json()['id']
        self.statuses[msg_id] = None

    async def get_status(self, phone, msg_id, all_=1):
        params = {
            'login': self.login,
            'psw': self.psw,
            'phone': phone,
            'id': msg_id,
            'all': all_
        }
        response = await self.session.get('https://smsc.ru/sys/status.php', params=params)
        response.raise_for_status()
        self.statuses[msg_id] = response.json()

    async def run(self, phones, msg):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.send_sms, phones, msg)


@click.command()
@click.argument('msg')
@click.argument('phones', nargs=-1)
@click.option('--login', help='Сообщение для отправки')
@click.option('--psw', help='Сообщение для отправки')
@click.option('--valid', default=1, help='Время жизни сообщения в часах', type=int)
def main(phones, msg, login, psw, valid):
    sender = SMSSender(login, psw, valid)
    trio.run(sender.run, phones, msg)


if __name__ == '__main__':
    main(auto_envvar_prefix='SMSC')
