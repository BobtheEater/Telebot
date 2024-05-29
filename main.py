import asyncio
import logging
import sys
import DBLoad

from datetime import datetime, timedelta, timezone
from os import getenv
from aiohttp import web

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
bot_started = False

#Test class function for multiple chats
class MultipleChatBot:
    def __init__(self,):
        self.running = False
        self.sleepTime = 4 * 60 * 60 
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

        await self.timed_delete_message(message.chat.id, message.message_id)
        oldMenu = await bot.send_message(chat_id=message.chat.id, text = "Помощник ЗС готов помогать", reply_markup=generate_menu(self.keyboard))
        self.oldMenu[message.chat.id] = oldMenu.message_id

    #Enables functionality (Useless)
    async def func(self, query:CallbackQuery):
        chat = query.message.chat
        user = query.from_user.username if query.from_user.username else query.from_user.first_name
        if self.functionality.get(chat.id):
            self.functionality[chat.id] = False
            text = "Функционал выключен"
            logging.info(f"Functionality off in {(chat.id, chat.title if chat.title else chat.username)} by {user}")
        else:
            self.functionality[chat.id] = True
            text = "Функционал включен"   
            logging.info(f"Functionality on in {(chat.id, chat.title if chat.title else chat.username)} by {user}")

        message = await query.message.answer(text = text)
        await query.answer()
        await self.timed_delete_message(chat.id, message.message_id)

    #Send the reminder message taken from the Database
    async def send_reminder(self,chat_id):
        call = "\nЗаходим на ЗС"
        text = " "
        membersDict =  DBLoad.get_members_by_chat(chat_id=chat_id)
        for member in  membersDict:
            if member["username"]:
                text += f"@{ member["username"] } "
            else:
                text += f"[{ member["first_name"] }](tg://user?id={ str(member["telegram_id"]) }) "

        text += call
        await bot.send_message(chat_id=chat_id,text=text,parse_mode="MarkdownV2")
        logging.info(f"Message | {text} | sent at chat {chat_id}")

    async def send_weekday_message_callback(self, query: CallbackQuery):
        chat = query.message.chat
        user = query.from_user.username if query.from_user.username else query.from_user.first_name
        chat_name = chat.title if chat.title else chat.username

        if chat.id in self.running_chats and self.running_chats[chat.id]:
            message =  await bot.send_message(chat_id=chat.id, text="Таймер уже запущен")
            await query.answer()
            logging.info(f"{user} tried to activate timer in chat {(chat_name,chat.id)} while timer is already active")
        else:
            self.running_chats[chat.id] = True
            logging.info(f"Timer activated by {user} in chat {(chat_name,chat.id)}")
            await query.answer()
            message = await bot.send_message(chat_id=chat.id, text="Таймер запущен")
            
            while self.running_chats[chat.id]:
                #timezone change to GMT+3 because the server runs UTC
                utc_now = datetime.now(timezone.utc)
                gmt_plus_3 = timezone(timedelta(hours=3))
                gmt_plus_3_time = utc_now.astimezone(gmt_plus_3)
                if gmt_plus_3_time.weekday() < 5 and 6 <= gmt_plus_3_time.hour <= 23:  # Monday=0, Tuesday=1, ... , Sunday=6
                    logging.info(f"Reminder sent at: {gmt_plus_3_time.strftime('%H:%M:%S')} in chat {chat_name} next reminder at: {(gmt_plus_3_time + timedelta(seconds=self.sleepTime)).strftime('%H:%M:%S')}")
                    await self.send_reminder(chat.id)
                
                else:
                    logging.info(f"Inappropriate time for a reminder: {gmt_plus_3_time.strftime('%H:%M:%S')} in chat {chat_name} next attempt at: {(gmt_plus_3_time + timedelta(seconds=self.sleepTime)).strftime('%H:%M:%S')}")

                # Wait for sleepTime seconds before checking again
                await asyncio.sleep(self.sleepTime)

        await self.timed_delete_message(chat.id, message.message_id,  awaitTilDelete = 0)

    #Check if the timer is on and stop the timer if it is
    async def stop_callback(self,query: CallbackQuery) -> None:
        chat = query.message.chat
        user = query.from_user.username if query.from_user.username else query.from_user.first_name
        chat_name = chat.title if chat.title else chat.username
        user = query.from_user.username if query.from_user.username else query.from_user.first_name
       
        if chat.id in self.running_chats:
            self.running_chats[chat.id] = False
            logging.info(f"Timer was stopped at {datetime.now().strftime('%d %H:%M:%S')} by {query.from_user.username if query.from_user.username else query.from_user.first_name} at chat {(chat_name,chat.id)}")
            message = await query.message.answer(text="Таймер остановлен")
        
        else:
            message = await query.message.answer(text="Таймер не запущен")
            logging.info(f"{user} tried to stop the timer in chat {(chat_name,chat.id)} while timer is not active")
        await query.answer()
        await self.timed_delete_message(chat.id, message.message_id, 3)

    #removes a persons id, username and firstname from the Database and notifies a user
    async def rmme_callback(self,query: CallbackQuery):
        if DBLoad.remove_member_from_list(query):
            message =  await bot.send_message(query.message.chat.id, text=f"Пользователь {query.from_user.first_name} был удален из списка") 
            #Add the message details to the recorded set
            logging.info(f"""User {(query.from_user.username,
                                query.from_user.first_name,
                                query.from_user.id,
                                query.message.chat.id)} removed from the database""")
        else:
            message = await bot.send_message(query.message.chat.id, text=f"Пользователь {query.from_user.first_name} не в списке")
            logging.info(f"""User {(query.from_user.username,
                                query.from_user.first_name,
                                query.from_user.id,
                                query.message.chat.id)} tried to be removed from the database and was not found""")
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
                        query.message.chat.id,)} added to the database""")            
        else:
            message = await bot.send_message(query.message.chat.id, text=f"Пользователь {query.from_user.first_name} уже в есть в списке") 
            logging.info(f"""User {(query.from_user.username,
                                query.from_user.first_name,
                                query.from_user.id,
                                query.message.chat.id)} tried to be added to the database and was found is the database""")
            
        await query.answer()
        await self.timed_delete_message(message.chat.id, message.message_id)

        @dp.message()
        async def message_handler(message: Message):
            pass

@dp.message(CommandStart())
async def start(message: Message) -> None:
    global bot_started
    chat = message.chat
    if not bot_started:
        newbot = MultipleChatBot()
        await newbot.greet(message)
        bot_started = True
        logging.info(f"Bot instance created at chat {(chat.id, chat.title if chat.title else chat.username)}")
    else:
        bot.send_message(text="Бот уже запущен \nНапиши /menu для визова меню")
        logging.info(f"Bot instance creation attempt at chat {(chat.id, chat.title if chat.title else chat.username)}")

async def main() -> None:
    await dp.start_polling(bot, allowed_updates=[], skip_updates=True)

async def webhook():
    async def handle(request):
        return web.Response(text="Bot is running")

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
        