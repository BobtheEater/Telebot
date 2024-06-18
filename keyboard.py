import asyncio
import logging

from aiogram import Bot, Router
from aiogram.filters import CommandStart
from aiogram.filters.command import Command
from aiogram.types import Message, InlineKeyboardButton 
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

from .common import timed_delete_message 

# Create bot and dispatcher
keyboardRouter = Router()
oldMenu = dict() #keep the keyboard menu to delete later

keyboard = {"Добавь меня":"addme",
            "Убери меня":"rmme",
            "Отправить напоминание":"sendreminder",
            "Начать таймер":"starttimer",
            "Остановить таймер":"stoptimer",
            "Назначить расписание":"setschedule",
            "Посмотреть расписание":"getschedule",
            }
notRowOptions = ["addme", "rmme"]

# Function to generate the menu
def generate_menu(menu_options : dict[str,str]):
    builder = InlineKeyboardBuilder()
    for option_text, callback_data in menu_options.items():
        if callback_data in notRowOptions:
            builder.add(InlineKeyboardButton(
            text=option_text, callback_data=callback_data)
            )
        else:
            builder.row(InlineKeyboardButton(
            text=option_text, callback_data=callback_data)
            )
    return builder.as_markup()

#send a menu for a user and delete and old one if exists
@keyboardRouter.message(CommandStart())
@keyboardRouter.message(Command(commands=["menu","Menu"]))
async def greet(message: Message, bot: Bot):
    if message.chat.id in oldMenu:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=oldMenu[message.chat.id])
        except(TelegramBadRequest) as e:
            logging.info(e)

    oldMessage = await bot.send_message(chat_id=message.chat.id, text = "Помощник ЗС готов помогать", reply_markup=generate_menu(keyboard))
    oldMenu[message.chat.id] = oldMessage.message_id
    await timed_delete_message(message.chat.id, message.message_id, 0)

