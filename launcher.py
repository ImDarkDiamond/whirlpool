import sys
import click
import logging
import asyncio
import asyncpg
import discord
import importlib
import contextlib
from logging.handlers import RotatingFileHandler
from bot import TeddyBear

class RemoveNoise(logging.Filter):
    def __init__(self):
        super().__init__(name='discord.state')

    def filter(self, record):
        if record.levelname == 'WARNING' and 'referencing an unknown' in record.msg:
            return False
        return True

@contextlib.contextmanager
def setup_logging():
    try:
        # __enter__
        max_bytes = 32 * 1024 * 1024 # 32 MiB
        logging.getLogger('discord').setLevel(logging.INFO)
        logging.getLogger('discord.http').setLevel(logging.WARNING)
        logging.getLogger('discord.state').addFilter(RemoveNoise())

        log = logging.getLogger()
        log.setLevel(logging.INFO)
        handler = RotatingFileHandler(filename='teddyBear.log', encoding='utf-8', mode='w', maxBytes=max_bytes, backupCount=5)
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        fmt = logging.Formatter('[{asctime}] [{levelname:<7}] {name}: {message}', dt_fmt, style='{')
        handler.setFormatter(fmt)
        log.addHandler(handler)

        yield
    finally:
        # __exit__
        handlers = log.handlers[:]
        for hdlr in handlers:
            hdlr.close()
            log.removeHandler(hdlr)

def run_bot():
    loop = asyncio.get_event_loop()
    log = logging.getLogger()
    # kwargs = {
    #     'command_timeout': 60,
    #     'max_size': 20,
    #     'min_size': 20,
    # }
    # try:
    #     pool = loop.run_until_complete(Table.create_pool(config.postgresql, **kwargs))
    # except Exception as e:
    #     click.echo('Could not set up PostgreSQL. Exiting.', file=sys.stderr)
    #     log.exception('Could not set up PostgreSQL. Exiting.')
    #     return

    bot = TeddyBear()
    # bot.pool = pool
    bot.run()

if __name__ == '__main__':
    run_bot()