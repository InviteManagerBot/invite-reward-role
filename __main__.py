import logging
import asyncio
import asyncpg
import configs
import click

from bot import SteveBot

_log = logging.getLogger(__name__)


def setup_logging():
    logging.getLogger("discord").setLevel(logging.INFO)
    logging.getLogger("discord.http").setLevel(logging.WARNING)

    logging.basicConfig(
        format="[{asctime}] [{levelname:<7}] {name}: {message}",
        style="{",
        level=logging.INFO,
    )


async def create_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        configs.postgresql_url,
        command_timeout=60,
        max_size=20,
        min_size=20,
    )


async def run_bot():
    bot = SteveBot()
    try:
        pool = await create_pool()
    except Exception:
        _log.error("Could not connect to PostgreSQL")
        return

    async with bot:
        bot.pool = pool
        await bot.start()


async def run_db_init():
    con = await asyncpg.connect(configs.postgresql_url)
    with open("setup.sql", "r", encoding="utf-8") as fp:
        await con.execute(fp.read())
    await con.close()


@click.group(
    invoke_without_command=True,
)
@click.pass_context
def main(ctx: click.Context):
    if ctx.invoked_subcommand is None:
        setup_logging()
        asyncio.run(run_bot())


@main.group()
def db():
    pass


@db.command()
def setup():
    asyncio.run(run_db_init())
    click.secho("Setup was run in the database", fg="green")


if __name__ == "__main__":
    asyncio.run(main())
