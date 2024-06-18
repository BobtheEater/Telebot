import asyncio
import logging
import sys
import SetSchedule
import keyboard
import MainMenu
import common

from os import getenv
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.strategy import FSMStrategy

#Bot setup
TOKEN = getenv("BOT_TOKEN")
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

dp = Dispatcher(fsm_strategy=FSMStrategy.CHAT,storage=SetSchedule.storage)

async def main() -> None:
    dp.include_routers(keyboard.keyboardRouter,
                       MainMenu.menurouter,
                       SetSchedule.router,
                       common.commonRouter)
    await dp.start_polling(bot, skip_updates=True)

async def webhook():
    async def handle(request):
        return web.Response(text="<b>Bot is running</b>")

    # Create an instance of the aiohttp web application
    app = web.Application()
    app.router.add_get('/', handle)
    
    # Run the web application on port 8000
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=8000)
    await site.start()

# Define the function to run both coroutines concurrently
async def create_coroutines():
    await asyncio.gather(
        main(),
        webhook()
    )
    print("webhook setup")

if __name__ == "__main__":
    #Basic logging conf to with the utf-8 support
    logging.basicConfig(level=logging.INFO,
                        stream=sys.stdout,
                        #filename="BotLogs.log",
                        encoding='utf-8',
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%d %H:%M:%S',)
    
    asyncio.run(create_coroutines()) 