import asyncio
import logging
import sys
import DBLoad

from random import randint
from datetime import datetime, timedelta, timezone
from os import getenv
from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery, Chat
from aiogram.exceptions import TelegramBadRequest

from keyboard import generate_menu

#Bot setup
TOKEN = getenv("BOT_TOKEN")
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

dp = Dispatcher()
bot_started = False

#Test class function for multiple chats
class MultipleChatBot:
    def __init__(self):
        self.running = False
        self.timeDiff = 4 #time to wait before sending a message in hours
        self.sleepTime = 10 * 60 
        self.lastReminder = dict() #dict to keep track of the last hour of a sent reminder
        self.functionality = dict()
        self.oldMenu = dict() #keep the keyboard menu to delete later
        self.running_chats = dict() #dict to keep track of chat timers


        self.keyboard = {"Добавь меня":"addme",
                         "Убери меня":"rmme",
                         "Отправить напоминание":"sendreminder",
                         "Начать таймер":"starttimer",
                         "Остановить таймер":"stoptimer",
                        }

        dp.message.register(self.greet,Command(commands=["menu","Menu"]))
        dp.message.register(self.get_all_members, Command("checkall"))

        #link commands with buttons
        dp.callback_query.register(self.send_single_reminder_callback,F.data == "sendreminder")
        dp.callback_query.register(self.send_weekday_message_callback,F.data == "starttimer")
        dp.callback_query.register(self.addme_callback,F.data == "addme")
        dp.callback_query.register(self.stop_callback,F.data == "stoptimer")
        dp.callback_query.register(self.rmme_callback,F.data == "rmme")
  
    #delete sent messages after a sleep time 
    async def timed_delete_message(self, chat_id: int, message_id: int,  awaitTilDelete: int = 5):
        await asyncio.sleep(awaitTilDelete)
        await bot.delete_message(chat_id=chat_id, message_id=message_id)

    #send a menu for a user and delete and old one if exists
    async def greet(self, message: Message):
        if message.chat.id in self.oldMenu:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=self.oldMenu[message.chat.id])
            except(TelegramBadRequest) as e:
                logging.info(e)

        oldMenu = await bot.send_message(chat_id=message.chat.id, text = "Помощник ЗС готов помогать", reply_markup=generate_menu(self.keyboard))
        self.oldMenu[message.chat.id] = oldMenu.message_id
        await self.timed_delete_message(message.chat.id, message.message_id, 0)

    #escape the special characters in usernames and first and second name's
    def escape_markdown_v2(self, text:str):
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!' ]
        escaped_text = ""
        for char in text:
            if char in escape_chars:
                escaped_text += "\\" + char
            else:
                escaped_text += char
        return escaped_text
    
    #Send the reminder message taken from the Database
    async def send_reminder(self, chat:Chat):
        call = "\nЗаходим на ЗС"
        text = " "
        chat_name = chat.title if chat.title else chat.username
        membersDict = DBLoad.get_members_by_chat(chat_id=chat.id)

        for member in membersDict:
            if member["username"]:
                text += f"@{self.escape_markdown_v2(member['username'])} "
            else:
                first_name = self.escape_markdown_v2(member['first_name'])
                text += f"[{first_name}](tg://user?id={member['telegram_id']}) "

        if randint(1, 100) in list(range(1, 15)):
            await bot.send_message(chat_id=chat.id, text=text, parse_mode="MarkdownV2")
            sticker = "CAACAgIAAxkBAAEF1bJmWtS_n1brWEZ2QBFzuxThLLHSFgACKQADaAyqFpujaoKf4jVgNQQ"
            await bot.send_sticker(chat_id=chat.id,sticker=sticker)
        else:
            text += call  
            await bot.send_message(chat_id=chat.id, text=text, parse_mode="MarkdownV2")
       
        logging.info(f"Message | {text} | sent at chat {(chat_name, chat.id)}")

    async def send_single_reminder_callback(self, query: CallbackQuery):
        chat = query.message.chat
        user = query.from_user.username if query.from_user.username else query.from_user.first_name

        logging.info(f"Single reminder sent by {user}")
        await self.send_reminder(chat=chat)

        await query.answer()

    #send a reminder by GMT+3 time every cycle(sleepTime)
    async def send_weekday_message_callback(self, query: CallbackQuery):
        chat = query.message.chat
        user = query.from_user.username if query.from_user.username else query.from_user.first_name
        chat_name = chat.title if chat.title else chat.username

        #Check if the timer is already running in the chat
        if chat.id in self.running_chats and self.running_chats[chat.id]:
            message =  await bot.send_message(chat_id=chat.id, text="Таймер уже запущен")
            await query.answer()
            logging.info(f"{user} tried to activate timer in chat {(chat_name,chat.id)} while timer is already active")
        else:
            #timezone change to GMT+3 because the server runs UTC
            utc_now = datetime.now(timezone.utc)
            gmt_plus_3 = timezone(timedelta(hours=3))
            gmt_plus_3_time = utc_now.astimezone(gmt_plus_3)

            self.running_chats[chat.id] = True
            self.lastReminder[chat.id] = gmt_plus_3_time.hour

            logging.info(f"Timer activated by {user} in chat {(chat_name,chat.id)}")
            await query.answer()
            message = await bot.send_message(chat_id=chat.id, text="Таймер запущен")
            await self.send_reminder(chat)
            await self.timed_delete_message(chat.id, message.message_id,  awaitTilDelete = 3)

            while self.running_chats[chat.id]:
                utc_now = datetime.now(timezone.utc)
                gmt_plus_3 = timezone(timedelta(hours=3))
                gmt_plus_3_time = utc_now.astimezone(gmt_plus_3)
                #Check if it's a weekday and the time's between 6 - 23 hours 
                if gmt_plus_3_time.weekday() < 5 and 6 <= gmt_plus_3_time.hour <= 23:  # Monday=0, Tuesday=1, ... , Sunday=6
                    #check the difference in hours between last reminder and current time
                    if (gmt_plus_3_time.hour - self.lastReminder[chat.id]) >= self.timeDiff:
                        logging.info(f"Reminder sent at: {gmt_plus_3_time.strftime('%H:%M:%S')} in chat {chat_name} next reminder at: {(gmt_plus_3_time + timedelta(hours=self.timeDiff)).strftime('%H:%M:%S')}")
                        await self.send_reminder(chat)
                        self.lastReminder[chat.id] = gmt_plus_3_time.hour
                    else:
                        logging.info(f"Not enough time has passed since last reminder for chat {chat_name}. Last reminder sent at {self.lastReminder[chat.id]} now {gmt_plus_3_time.strftime('%H:%M')} diff: {gmt_plus_3_time.hour - self.lastReminder[chat.id]}")
                    
                else:
                    logging.info(f"Inappropriate time for a reminder: {gmt_plus_3_time.strftime('%H:%M:%S')} in chat {chat_name} next attempt at: {(gmt_plus_3_time + timedelta(hours=self.timeDiff)).strftime('%H:%M:%S')}")
                    self.lastReminder[chat.id] = gmt_plus_3_time.hour
                # Wait for sleepTime seconds before checking again
                await asyncio.sleep(self.sleepTime)

    #stop the timer in a chat
    async def stop_callback(self,query: CallbackQuery):
        chat = query.message.chat
        user = query.from_user.username if query.from_user.username else query.from_user.first_name
        chat_name = chat.title if chat.title else chat.username

        utc_now = datetime.now(timezone.utc)
        gmt_plus_3 = timezone(timedelta(hours=3))
        gmt_plus_3_time = utc_now.astimezone(gmt_plus_3)
        
        #check if the timer is on in a chat
        if chat.id in self.running_chats:
            self.running_chats[chat.id] = False
            logging.info(f"Timer was stopped at {gmt_plus_3_time.strftime('%d %H:%M:%S')} by {user} at chat {(chat_name,chat.id)}")
            message = await query.message.answer(text="Таймер остановлен")
        
        else:
            message = await query.message.answer(text="Таймер не запущен")
            logging.info(f"{user} tried to stop the timer in chat {(chat_name,chat.id)} while timer is not active")
        await query.answer()
        await self.timed_delete_message(chat.id, message.message_id, 3)

    #secret command to get all of the database entries
    async def get_all_members(self, message: Message):
        allMembers = DBLoad.get_all_members()
        for member in allMembers:
            await bot.send_message(chat_id=message.chat.id, text=str(member))

    #removes a users id, username and firstname from the Database and notifies a user
    async def rmme_callback(self,query: CallbackQuery):
        #check if the user is in the database
        if DBLoad.remove_member_from_list(query):
            message =  await bot.send_message(query.message.chat.id, text=f"Пользователь {query.from_user.first_name} был удален из списка") 
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
        #check if the person is not in the database
        if DBLoad.add_member_to_list(query):
            message = await bot.send_message(query.message.chat.id, text=f"Пользователь {query.from_user.first_name} был успешно добавлен в список")
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

        #handler for all messagess, so you won't get "Update not handled"
        @dp.message()
        async def chat_member_handler(message: Message):
            #id Ника 1423976911
            if message.from_user.id == 1423976911 and message.text == "иди в жопу":
                text = "Сам иди"
                await message.answer(text = text)
                
            if message.left_chat_member:
                DBLoad.remove_member_from_list(message.left_chat_member)
            elif message.new_chat_members:
                for member in message.new_chat_members:
                    DBLoad.new_chat_member_db_handler(member, message.chat.id)
            else:
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
        await bot.send_message(chat_id = chat.id ,text="Бот уже запущен \nНапиши /menu для визова меню")
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