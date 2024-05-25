import asyncio
import logging
import sys
import DBLoad

from datetime import datetime, timedelta
from os import getenv

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery

from keyboard import generate_menu

#Bot setup
TOKEN = getenv("BOT_TOKEN")
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()

#Test class function for multiple chats
class MultipleChatBot:
    def __init__(self,):
        self.running = False
        self.sleepTime = 5 * 60 
        self.functionality = dict()
        self.oldMenu = dict() #keep the keyboard menu to delete later
        self.running_chats = dict() #dict to keep track of chat timers

        self.keyboard = {"Добавь меня":"addme",
                         "Убери меня":"rmme",
                         "Начать таймер":"starttimer",
                         "Остановить таймер":"stoptimer",
                         "Включить функционал":"functionality"}

        dp.message.register(self.greet,Command(commands=["menu","Menu"]))

        #link commands with buttons
        dp.callback_query.register(self.send_weekday_message_callback,F.data == "starttimer")
        dp.callback_query.register(self.addme_callback,F.data == "addme")
        dp.callback_query.register(self.stop_callback,F.data == "stoptimer")
        dp.callback_query.register(self.rmme_callback,F.data == "rmme")
        dp.callback_query.register(self.func,F.data == "functionality")
    
    #delete sent messages after a sleep time 
    async def timed_delete_message(self, chat_id: int, message_id: int,  awaitTilDelete: int = 5):
        await asyncio.sleep(awaitTilDelete)
        await bot.delete_message(chat_id=chat_id, message_id=message_id)

    #send a menu for a user and delete and old one if exists
    async def greet(self, message: Message):
        if message.chat.id in self.oldMenu:
           await bot.delete_message(chat_id=message.chat.id, message_id=self.oldMenu[message.chat.id])

        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        oldMenu = await bot.send_message(chat_id=message.chat.id, text = "Помощник ЗС готов помогать:", reply_markup=generate_menu(self.keyboard))
        self.oldMenu[message.chat.id] = oldMenu.message_id

    #Enables functionality (Useless)
    async def func(self, query:CallbackQuery):
        chat_id = query.message.chat.id
        if self.functionality.get(chat_id):
            self.functionality[chat_id] = False
            text = "Функционал выключен"

        else:
            self.functionality[chat_id] = True
            text = "Функционал включен"   

        message = await query.message.answer(text = text)
        await query.answer()
        await self.timed_delete_message(chat_id, message.message_id)

    #Send the reminder message taken from the Database
    async def send_reminder(self,chat_id):
        call = "\nЗаходим на ЗС"
        text = " "
        membersDict =  DBLoad.get_members_by_chat(chat_id=chat_id)
        for member in  membersDict:
            if member["username"]:
                text += f"@{ member["username"] } "
            else:
                text += f"[{ member["first_name"] }(tg://user?id={ str(member["telegram_id"]) }) "

        text += call
        await bot.send_message(chat_id=chat_id,text=text,parse_mode="MarkdownV2")
        logging.info(f"Message | {text} | sent at chat {chat_id}")

    async def send_weekday_message_callback(self, query: CallbackQuery):
        chat_id = query.message.chat.id

        if chat_id in self.running_chats and self.running_chats[chat_id]:
            message =  await bot.send_message(chat_id=chat_id, text="Таймер уже запущен")
            await query.answer()
        else:
            chat_name = query.message.chat.title if  query.message.chat.title else  query.message.chat.username
            user = query.from_user.username if query.from_user.username else query.from_user.first_name
            self.running_chats[chat_id] = True
            logging.info(f"Timer activated by {user} in chat {(chat_name,chat_id)}")
            await query.answer()
            message = await bot.send_message(chat_id=chat_id, text="Таймер запущен")
            
            while self.running_chats[chat_id]:
                now = datetime.now()
                if now.weekday() < 5 and 6 <= now.hour <= 23:  # Monday=0, Tuesday=1, ... , Sunday=6
                    logging.info(f"Reminder sent at: {now.strftime('%H:%M:%S')} in chat {chat_name} next reminder at: {(now + timedelta(seconds=self.sleepTime)).strftime('%H:%M:%S')}")
                    await self.send_reminder(chat_id)
                else:
                    logging.info(f"Inappropriate time for a reminder: {now.strftime('%H:%M:%S')} in chat {chat_name} next attempt at: {(now + timedelta(seconds=self.sleepTime)).strftime('%H:%M:%S')}")

                # Wait for sleepTime seconds before checking again
                await asyncio.sleep(self.sleepTime)

        await self.timed_delete_message(chat_id, message.message_id, 0)

    #Check if the timer is on and stop the timer if it is
    async def stop_callback(self,query: CallbackQuery) -> None:
        chat_id = query.message.chat.id
        if chat_id in self.running_chats:
            self.running_chats[chat_id] = False
            logging.info(f"Timer was stopped at {datetime.now().strftime('%d %H:%M:%S')} by {query.from_user.username if query.from_user.username else query.from_user.first_name} at chat {chat_id}")
            message = await query.message.answer(text="Таймер остановлен")
        else:
            message = await query.message.answer(text="Таймер не запущен")
        await query.answer()
        await self.timed_delete_message(chat_id, message.message_id, 3)

    #removes a persons id, username and firstname from the Database and notifies a user
    async def rmme_callback(self,query: CallbackQuery):
        if DBLoad.remove_member_from_list(query):
            message =  await bot.send_message(query.message.chat.id, text=f"Пользователь {query.from_user.first_name} был удален из списка") 
            #Add the message details to the recorded set
            logging.info(f"""User {(query.from_user.username,
                                query.from_user.first_name,
                                query.from_user.id,
                                query.message.chat.id)} removed from the set""")
        else:
            message = await bot.send_message(query.message.chat.id, text=f"Пользователь {query.from_user.first_name} не в списке")
        
        await query.answer()
        await self.timed_delete_message(message.chat.id, message.message_id)

    #adds a persons id, username and firstname to the set and sends a confirmation message 
    async def addme_callback(self,query: CallbackQuery):
        if DBLoad.add_member_to_list(query):
            message = await bot.send_message(query.message.chat.id, text=f"Пользователь {query.from_user.first_name} был успешно добавлен в список")
            #Add the message details to the recorded set
            logging.info(f"""User {(query.from_user.username,
                        query.from_user.first_name,
                        query.from_user.id,
                        query.message.chat.id,)} added to the set""")            
        else:
            message = await bot.send_message(query.message.chat.id, text=f"Пользователь {query.from_user.first_name} уже в есть в списке") 
    
        await query.answer()
        await self.timed_delete_message(message.chat.id, message.message_id)

@dp.message(CommandStart())
async def start(message: Message) -> None:
    chat = message.chat
    await bot.delete_message(chat_id=chat.id, message_id=message.message_id)
    newbot = MultipleChatBot()
    await newbot.greet(message)
    logging.info(f"Bot instance created at chat {(chat.id, chat.title if chat.title else chat.username)}")


async def main() -> None:
    #Initialize Bot instance with default bot properties which will be passed to all API calls
    #And the run events dispatching
    await dp.start_polling(bot,allowed_updates=[])
        
if __name__ == "__main__":
    #Basic logging conf to with the utf-8 support
    logging.basicConfig(level=logging.INFO,
                        #stream=sys.stdout,
                        filename="BotLogs.log",
                        encoding='utf-8',
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%d %H:%M:%S',)
    asyncio.run(main())
    
        