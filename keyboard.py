import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.filters.command import Command
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery  
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from os import getenv

# Replace with your bot API token
TOKEN = getenv("BOT_TOKEN")

# Create bot and dispatcher
dp = Dispatcher()

notRowOptions = ["addme", "rmme"]

# Function to generate the menu
def generate_menu(menu_options : dict[str,str]):
    builder = InlineKeyboardBuilder()
    for option_text, callback_data in menu_options.items():
        if callback_data in notRowOptions:
            builder.add(InlineKeyboardButton(
            text=option_text, callback_data=callback_data )
            )
        else:
            builder.row(InlineKeyboardButton(
            text=option_text, callback_data=callback_data )
            )
    return builder.as_markup()

# Handler for the /menu command
@dp.message(Command("menu"))
async def show_menu(message: Message):
    """Handle the /menu command and display the menu."""
    await message.answer("Please select an option:", reply_markup=generate_menu())

# Handler for button clicks
async def handle_button_click(query: CallbackQuery):
    """Handle button clicks from the menu."""
    await query.answer()  # Acknowledge the button click
    selected_option = query.data
    await query.message.answer(f"You selected: {selected_option}")

async def main():
    bot = Bot(token=TOKEN,default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    # Start the bot
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
