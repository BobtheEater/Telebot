import asyncio

from aiogram import Bot, F, Router
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from dotenv import load_dotenv
from os import getenv

load_dotenv()
TOKEN = getenv("BOT_TOKEN")
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

commonRouter = Router()
#delete sent messages after a sleep time 
async def timed_delete_message(chat_id: int, message_id: int,  awaitTilDelete: int = 5):
    await asyncio.sleep(awaitTilDelete)
    await bot.delete_message(chat_id=chat_id, message_id=message_id)

@commonRouter.message((F.text.lower().contains("иди в жопу"))&(F.from_user.id == int(getenv("NIK_ID")) ))
async def nik_handler(message: Message):
    text = "Сам иди"
    await message.reply(text = text)