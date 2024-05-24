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
        self.sleepTime = 10 #5 * 60 * 60
        self.functionality = dict()
        self.oldMenu = dict() #keep the keyboard menu to delete later
        self.running_chats = dict() #dict to keep track of chat timers

        self.keyboard = {"Добавь меня":"addme",
                         "Убери меня":"rmme",
                         "Начать таймер":"starttimer",
                         "Остановить таймер":"stoptimer",
                         "Включить функционал":"functionality"}

        #link commands with functions
        dp.message.register(self.send_weekday_message,Command(commands=["startTimer","starttimer"]))
        dp.message.register(self.stop,Command(commands=["stopTimer","stoptimer"]))
        dp.message.register(self.rmme,Command(commands=["rmme","rmMe"]))
        dp.message.register(self.addme,Command(commands=["addme","addMe"]))
        dp.message.register(self.greet,Command(commands=["menu","Menu"]))

        #link commands with buttons
        dp.callback_query.register(self.send_weekday_message_callback,F.data == "starttimer")
        dp.callback_query.register(self.addme_callback,F.data == "addme")
        dp.callback_query.register(self.stop_callback,F.data == "stoptimer")
        dp.callback_query.register(self.rmme_callback,F.data == "rmme")
        dp.callback_query.register(self.func,F.data == "functionality")

    #send a menu for a user and delete and old one if exists
    async def greet(self, message: Message):
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        
        if message.chat.id in self.oldMenu:
           await bot.delete_message(chat_id=message.chat.id, message_id=self.oldMenu[message.chat.id])

        oldMenu = await bot.send_message(chat_id=message.chat.id, text = "Помощник ЗС готов помогать:", reply_markup=generate_menu(self.keyboard))
        self.oldMenu[message.chat.id] = oldMenu.message_id

    #Enables functionality (Useless)
    async def func(self, query:CallbackQuery):
        chat_id = query.message.chat.id
        if self.functionality[chat_id]:
            self.functionality[chat_id] = False
            text = "Функционал выключен"
        else:
            self.functionality[chat_id] = True
            text = "Функционал включен"
        await query.message.answer(text = text)
        await query.answer()

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

    #Check if the timer is on, check if it's a weekday, send a message if it is or wait another cycle if not
    async def send_weekday_message(self,message:Message):
        chat_id = message.chat.id
        if chat_id in self.running_chats and self.running_chats[chat_id]:
            await bot.send_message(chat_id=chat_id, text="Таймер уже запущен")
        else:
            chat_name = message.chat.title if  message.chat.title else  message.chat.username
            user = message.from_user.username if message.from_user.username else message.from_user.first_name
            self.running = True
            logging.info(f"Timer activated by {user} in chat {(chat_name,chat_id)}")
            while self.running:
                # Get the current datetime
                now = datetime.now()
                # Check if today is a weekday (Monday to Friday)
                if now.weekday() < 5:  # Monday=0, Tuesday=1, ... , Sunday=6
                    logging.info("Reminder sent at: " + str(now.strftime('%H:%M:%S')) + " in chat "+  chat_name +" next reminder at: " + (now + timedelta(seconds=self.sleepTime)).strftime('%H:%M:%S'))
                    #Send the message
                    await self.send_reminder(message.chat.id)
                else:
                    logging.info("Inapropriete time for a reminder: " + str(now.strftime('%H:%M:%S')) + " in chat "+  chat_name +" next attempt at: " + (now + timedelta(seconds=self.sleepTime)).strftime('%H:%M:%S'))
                
                # Wait before checking again
                
                await asyncio.sleep(self.sleepTime)

    async def send_weekday_message_callback(self, query: CallbackQuery):
        chat_id = query.message.chat.id

        if chat_id in self.running_chats and self.running_chats[chat_id]:
            await bot.send_message(chat_id=chat_id, text="Таймер уже запущен")
            await query.answer()
        else:
            chat_name = query.message.chat.title if  query.message.chat.title else  query.message.chat.username
            user = query.from_user.username if query.from_user.username else query.from_user.first_name
            self.running_chats[chat_id] = True
            logging.info(f"Timer activated by {user} in chat {(chat_name,chat_id)}")
            await query.answer()
            await bot.send_message(chat_id=chat_id, text="Таймер запущен")
            
            while self.running_chats[chat_id]:
                now = datetime.now()
                if now.weekday() < 5 and 6 <= now.hour <= 23:  # Monday=0, Tuesday=1, ... , Sunday=6
                    logging.info(f"Reminder sent at: {now.strftime('%H:%M:%S')} in chat {chat_name} next reminder at: {(now + timedelta(seconds=self.sleepTime)).strftime('%H:%M:%S')}")
                    await self.send_reminder(chat_id)
                else:
                    logging.info(f"Inappropriate time for a reminder: {now.strftime('%H:%M:%S')} in chat {chat_name} next attempt at: {(now + timedelta(seconds=self.sleepTime)).strftime('%H:%M:%S')}")
                
                # Wait for sleepTime seconds before checking again
                await asyncio.sleep(self.sleepTime)


    #Check if the timer is on and stop the timer if it is
    async def stop(self,message: Message) -> None:
        if self.running:
            logging.info(f"Timer was stopped at {datetime.now().strftime('%d %H:%M:%S')} by {message.from_user.username if message.from_user.username else message.from_user.first_name} at chat {message.chat.id}")
            self.running = False
            await bot.send_message(chat_id=message.chat.id, text="Таймер остановлен")
        else:
            await bot.send_message(chat_id=message.chat.id, text="Таймер не запущен")

    async def stop_callback(self,query: CallbackQuery) -> None:
        chat_id = query.message.chat.id
        if chat_id in self.running_chats:
            self.running_chats[chat_id] = False
            logging.info(f"Timer was stopped at {datetime.now().strftime('%d %H:%M:%S')} by {query.from_user.username if query.from_user.username else query.from_user.first_name} at chat {chat_id}")
            await query.message.answer(text="Таймер остановлен")
        else:
            await query.message.answer(text="Таймер не запущен")
        await query.answer()

    #removes a persons id, username and firstname from the set and notifies a user
    async def rmme(self,message:Message):
        if DBLoad.remove_member_from_list(message):
            await bot.send_message(message.chat.id, text=f"Пользователь {message.from_user.first_name} был удален из списка") 
            #Add the message details to the recorded set
            logging.info(f"""User {(message.from_user.username,
                                    message.from_user.first_name,
                                    message.from_user.id,
                                    message.chat.id)} removed from the set""")
        else:
            await bot.send_message(message.chat.id, text=f"Пользователь {message.from_user.first_name} не в списке")

    async def rmme_callback(self,query: CallbackQuery):
        if DBLoad.remove_member_from_list(query):
            await bot.send_message(query.message.chat.id, text=f"Пользователь {query.from_user.first_name} был удален из списка") 
            #Add the message details to the recorded set
            logging.info(f"""User {(query.from_user.username,
                                query.from_user.first_name,
                                query.from_user.id,
                                query.message.chat.id)} removed from the set""")
        else:
            await bot.send_message(query.message.chat.id, text=f"Пользователь {query.from_user.first_name} не в списке")
        
        await query.answer()

    #adds a persons id, username and firstname to the set and sends a confirmation message 
    async def addme(self,message: Message):
        if DBLoad.add_member_to_list(message):
            await bot.send_message(message.chat.id, text=f"Пользователь {message.from_user.first_name} был успешно добавлен в список")
            logging.info(f"""User {(message.from_user.username,
                                message.from_user.first_name,
                                message.from_user.id,
                                message.chat.id)} added to the set""")
        else:
            await bot.send_message(message.chat.id, text=f"Пользователь {message.from_user.first_name} уже в есть в списке") 
        
    async def addme_callback(self,query: CallbackQuery):
        if DBLoad.add_member_to_list(query):
            await bot.send_message(query.message.chat.id, text=f"Пользователь {query.from_user.first_name} был успешно добавлен в список")
            #Add the message details to the recorded set
            logging.info(f"""User {(query.from_user.username,
                        query.from_user.first_name,
                        query.from_user.id,
                        query.message.chat.id,)} added to the set""")            
        else:
            await bot.send_message(query.message.chat.id, text=f"Пользователь {query.from_user.first_name} уже в есть в списке") 
    
        await query.answer()

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
    
        