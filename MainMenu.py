import asyncio
import logging
import DBLoad

from .common import timed_delete_message
from random import randint
from datetime import datetime, timedelta, timezone
from os import getenv

from aiogram import Bot, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import JOIN_TRANSITION, LEAVE_TRANSITION
from aiogram.filters.command import Command
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, Chat, ChatMemberUpdated

#Bot setup
TOKEN = getenv("BOT_TOKEN")
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

menurouter = Router()
bot_started = False

#Test class function for multiple chats
running = False
sleepTime = 10 * 60 
lastReminder = dict() #dict to keep track of the last hour of a sent reminder
functionality = dict()
running_chats = dict() #dict to keep track of chat timers

#escape the special characters in usernames and first and second name's
def escape_markdown_v2(text:str):
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!' ]
    escaped_text = ""
    for char in text:
        if char in escape_chars:
            escaped_text += "\\" + char
        else:
            escaped_text += char
    return escaped_text

#Send the reminder message taken from the Database
async def send_reminder(chat:Chat):
    call = "\nЗаходим на ЗС"
    text = " "
    chat_name = chat.title if chat.title else chat.username
    membersDict = DBLoad.get_members_by_chat(chat_id=chat.id)

    for member in membersDict:
        if member["username"]:
            text += f"@{escape_markdown_v2(member['username'])} "
        else:
            first_name = escape_markdown_v2(member['first_name'])
            text += f"[{first_name}](tg://user?id={member['telegram_id']}) "

    if randint(1, 100) in list(range(1, 15)):
        await bot.send_message(chat_id=chat.id, text=text, parse_mode="MarkdownV2")
        sticker = "CAACAgIAAxkBAAEF1bJmWtS_n1brWEZ2QBFzuxThLLHSFgACKQADaAyqFpujaoKf4jVgNQQ"
        await bot.send_sticker(chat_id=chat.id,sticker=sticker)
    else:
        text += call  
        await bot.send_message(chat_id=chat.id, text=text, parse_mode="MarkdownV2")
    
    logging.info(f"Message | {text} | sent at chat {(chat_name, chat.id)}")

@menurouter.callback_query(F.data == "sendreminder")
async def send_single_reminder_callback(query: CallbackQuery):
    chat = query.message.chat
    user = query.from_user.username if query.from_user.username else query.from_user.first_name

    logging.info(f"Single reminder sent by {user}")
    await send_reminder(chat=chat)

    await query.answer()

#send a reminder by GMT+3 time every cycle(sleepTime)
@menurouter.callback_query(F.data == "starttimer")
async def send_weekday_message_callback(query: CallbackQuery, state: FSMContext):
    last_time_message_sent = dict() #Dict to check the last time reminder was sent  
    message_sent = dict() #Dict to check if the reminder was sent this hour

    chat = query.message.chat
    user = query.from_user.username if query.from_user.username else query.from_user.first_name
    chat_name = chat.title if chat.title else chat.username
    chat_schedule =  await state.get_data()

    #Check if the timer is already running in the chat
    if chat.id in running_chats and running_chats[chat.id]:
        message =  await bot.send_message(chat_id=chat.id, text="Таймер уже запущен")
        await query.answer()
        logging.info(f"{user} tried to activate timer in chat {(chat_name,chat.id)} while timer is already active")
    elif not chat_schedule:
        message =  await bot.send_message(chat_id=chat.id, text="Розписание не назначено")
    else:
        #timezone change to GMT+3 because the server runs UTC
        utc_now = datetime.now(timezone.utc)
        gmt_plus_3 = timezone(timedelta(hours=3))
        gmt_plus_3_time = utc_now.astimezone(gmt_plus_3)

        running_chats[chat.id] = True
        message_sent[chat.id] = True
        last_time_message_sent[chat.id] = gmt_plus_3_time.hour #hour of a sent message of 

        logging.info(f"Timer activated by {user} in chat {(chat_name,chat.id)}")
        await query.answer()
        message = await bot.send_message(chat_id=chat.id, text="Таймер запущен")
        await send_reminder(chat)
        await timed_delete_message(chat.id, message.message_id,  awaitTilDelete = 3)
        
        while running_chats[chat.id]:
            utc_now = datetime.now(timezone.utc)
            gmt_plus_3 = timezone(timedelta(hours=3))
            gmt_plus_3_time = utc_now.astimezone(gmt_plus_3)
            #Check if time is in a schedule 
            if gmt_plus_3_time.hour in chat_schedule['chosen_schedule']:
                if not message_sent.get(chat.id, False):
                    logging.info(f"Reminder sent at: {gmt_plus_3_time.strftime('%H:%M:%S')} in chat {chat_name} chat's schedule: {chat_schedule['chosen_schedule']}")
                    await send_reminder(chat)
                    message_sent[chat.id] = True
                    last_time_message_sent[chat.id] = gmt_plus_3_time.hour
                    #if reminder needs to be sent on consecutive hours reset the message sent
                elif gmt_plus_3_time.hour != last_time_message_sent[chat.id]:
                    message_sent[chat.id] = False
                else:
                    logging.info(f"Inappropriate time for a reminder: {gmt_plus_3_time.strftime('%H:%M:%S')} in chat {chat_name} chat's schedule: {chat_schedule['chosen_schedule']}")
            else:
                message_sent[chat.id] = False
                logging.info(f"Inappropriate time for a reminder: {gmt_plus_3_time.strftime('%H:%M:%S')} in chat {chat_name} chat's schedule: {chat_schedule['chosen_schedule']}")
            # Wait for sleepTime seconds before checking again
            await asyncio.sleep(sleepTime)

#stop the timer in a chat
@menurouter.callback_query(F.data == "stoptimer")
async def stop_callback(query: CallbackQuery):
    chat = query.message.chat
    user = query.from_user.username if query.from_user.username else query.from_user.first_name
    chat_name = chat.title if chat.title else chat.username

    utc_now = datetime.now(timezone.utc)
    gmt_plus_3 = timezone(timedelta(hours=3))
    gmt_plus_3_time = utc_now.astimezone(gmt_plus_3)
    
    #check if the timer is on in a chat
    if running_chats[chat.id]:
        running_chats[chat.id] = False
        logging.info(f"Timer was stopped at {gmt_plus_3_time.strftime('%d %H:%M:%S')} by {user} at chat {(chat_name,chat.id)}")
        message = await query.message.answer(text="Таймер остановлен")
    
    else:
        message = await query.message.answer(text="Таймер не запущен")
        logging.info(f"{user} tried to stop the timer in chat {(chat_name,chat.id)} while timer is not active")
    await query.answer()
    await timed_delete_message(chat.id, message.message_id, 3)

#secret command to get all of the database entries
@menurouter.message(Command("checkall"))
async def get_all_members( message: Message):
    allMembers = DBLoad.get_all_members()
    for member in allMembers:
        await bot.send_message(chat_id=message.chat.id, text=str(member))

#removes a users id, username and firstname from the Database and notifies a user
@menurouter.callback_query(F.data == "rmme")
async def rmme_callback(query: CallbackQuery):
    #check if the user is in the database
    if DBLoad.remove_member_from_db(query.from_user, query.message.chat.id):
        message =  await bot.send_message(query.message.chat.id, text=f"Пользователь {query.from_user.first_name} был удален из списка") 
        logging.info(f"""User {(query.from_user.username, query.from_user.first_name,
                            query.from_user.id, query.message.chat.id)} removed from the database""")
    else:
        message = await bot.send_message(query.message.chat.id, text=f"Пользователь {query.from_user.first_name} не в списке")
        logging.info(f"""User {(query.from_user.username, query.from_user.first_name,
                                query.from_user.id, query.message.chat.id)} tried to be removed from the database and was not found""")
    await query.answer()
    await timed_delete_message(message.chat.id, message.message_id)

#adds a persons id, username and firstname to the set and sends a confirmation message 
@menurouter.callback_query(F.data == "addme")
async def addme_callback(query: CallbackQuery):
    #check if the person is not in the database
    if DBLoad.add_member_to_db(query.from_user, query.message.chat.id):
        message = await bot.send_message(query.message.chat.id, text=f"Пользователь {query.from_user.first_name} был успешно добавлен в список")
        logging.info(f"""User {(query.from_user.username, query.from_user.first_name,
                                query.from_user.id, query.message.chat.id,)} added to the database""")      
                
    else:
        message = await bot.send_message(query.message.chat.id, text=f"Пользователь {query.from_user.first_name} уже в есть в списке") 
        logging.info(f"""User {(query.from_user.username, query.from_user.first_name,
                                query.from_user.id, query.message.chat.id)} tried to be added to the database and was found is the database""")
        
    await query.answer()
    await timed_delete_message(message.chat.id, message.message_id)

#NEEDS TESTING
#func to add a member to the database upon entering a group
@menurouter.chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def new_member_handler(event: ChatMemberUpdated):
    member = event.new_chat_member.user
    if member.id != bot.id:
        if DBLoad.add_member_to_db(member, event.chat.id):
            logging.info(f"""User {(member.username, member.first_name,
                                    member.id, event.chat.id,)} added to the database""")      
            await event.answer(text= f"Пользователь {member.first_name} был успешно добавлен в список")        
        else: 
            logging.info(f"""User {(member.username, member.first_name,
                                    member.id, event.chat.id)} tried to be added to the database and was found is the database""")

#func to remove a member from the database upon leaving a group
@menurouter.chat_member(ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION))
async def left_member_handler(event: ChatMemberUpdated):
    member = event.old_chat_member.user
    if member.id != bot.id:
        if DBLoad.remove_member_from_db(member, event.chat.id):
            logging.info(f"""User {(member.username, member.first_name,
                                    member.id, event.chat.id)} removed from the database""")
            await event.answer(text=f"Пользователь {member.first_name} был удален из списка")
        else:
            logging.info(f"""User {(member.username, member.first_name,
                                    member.id, event.chat.id)} tried to be removed from the database and was not found""")