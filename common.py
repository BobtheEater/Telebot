import asyncio

from aiogram import Bot, F, Router
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from os import getenv

load_dotenv()
TOKEN = getenv("BOT_TOKEN")
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

commonRouter = Router()
#delete sent messages after a sleep time 
async def timed_delete_message(message: Message,  awaitTilDelete: int = 5):
    await asyncio.sleep(awaitTilDelete)
    await message.delete()

@commonRouter.message((F.text.lower().contains("иди"))&(F.from_user.id == int(getenv("NIK_ID")) ))
async def nik_handler(message: Message):
    text = "Сам иди"
    await message.reply(text = text)

#timezone change to GMT+3 because the server runs UTC
def get_time_gmt3():
    utc_now = datetime.now(timezone.utc)
    gmt_plus_3 = timezone(timedelta(hours=3))
    gmt_plus_3_time = utc_now.astimezone(gmt_plus_3)
    
    return gmt_plus_3_time