import asyncio
import logging

from Member_menagement import get_reminder_text
from common import timed_delete_message, get_time_gmt3
from os import getenv

from aiogram import Bot, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Chat

#Bot setup
TOKEN = getenv("BOT_TOKEN")
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

menurouter = Router()
timer_started = False

sleepTime = 10 * 60 
lastReminder = dict() #dict to keep track of the last hour of a sent reminder
functionality = dict()
running_chats = dict() #dict to keep track of chat timers

last_time_message_sent = dict() #Dict to check the last time reminder was sent  
message_sent = dict() #Dict to check if the reminder was sent this hour


@menurouter.callback_query(F.data == "sendreminder")
async def send_single_reminder_callback(query: CallbackQuery):
    chat = query.message.chat
    user = query.from_user.username if query.from_user.username else query.from_user.first_name

    logging.info(f"Single reminder sent by {user}")
    text = await get_reminder_text(chat=chat)
    await query.message.answer(text = text, parse_mode=ParseMode.MARKDOWN_V2)

    await query.answer()

#send a reminder by GMT+3 time every cycle(sleepTime)
@menurouter.callback_query(F.data == "starttimer")
async def send_weekday_message_callback(query: CallbackQuery, state: FSMContext):
    chat = query.message.chat
    user = query.from_user.username if query.from_user.username else query.from_user.first_name
    chat_name = chat.title if chat.title else chat.username

    chat_schedule =  await state.get_data()

    #Check if the timer is already running in the chat
    if running_chats.get(chat.id, False):
        message =  await query.message.answer(text="Таймер уже запущен")
        await query.answer()
        
        logging.info(f"{user} tried to activate timer in chat {(chat_name,chat.id)} while timer is already active")
    
    elif not chat_schedule:
        message =  await query.message.answer(text="Розписание не назначено")
        await query.answer()
    else:
        gmt_plus_3_time = get_time_gmt3()
        global timer_started

        running_chats[chat.id] = True
        message_sent[chat.id] = True
        last_time_message_sent[chat.id] = gmt_plus_3_time.hour #hour of a sent message 

        logging.info(f"Timer activated by {user} in chat {(chat_name,chat.id)}")
        await query.answer()

        message = await query.message.answer(text="Таймер запущен")
        await timed_delete_message(message, awaitTilDelete = 3)
        
        await runtimer(chat=chat, query=query, state = state)

async def runtimer(chat: Chat, query: CallbackQuery, state: FSMContext):
    chat_name = chat.title if chat.title else chat.username
    chat_schedule =  await state.get_data()

    text = await get_reminder_text(chat)
    await query.message.answer(text=text, parse_mode=ParseMode.MARKDOWN_V2)

    while running_chats[chat.id]:
            gmt_plus_3_time = get_time_gmt3()
            #Check if time is in a schedule 
            if gmt_plus_3_time.hour in chat_schedule['chosen_schedule']:
                #check if a message wasn't sent this hour if in a schedule 
                if not message_sent.get(chat.id, False):
                    #set that the message was sent recently to true and update last hour the message was sent
                    message_sent[chat.id] = True
                    last_time_message_sent[chat.id] = gmt_plus_3_time.hour
                    
                    text = await get_reminder_text(chat)
                    await query.message.answer(text=text, parse_mode=ParseMode.MARKDOWN_V2)
                    
                    logging.info(f"Reminder sent at: {gmt_plus_3_time.strftime('%H:%M:%S')} in chat {chat_name} chat's schedule: {chat_schedule['chosen_schedule']}")
                #if reminder needs to be sent on consecutive hours reset the message_sent
                elif gmt_plus_3_time.hour != last_time_message_sent[chat.id]:
                    message_sent[chat.id] = False
                    logging.info(f"Inappropriate time for a reminder: {gmt_plus_3_time.strftime('%H:%M:%S')} in chat {chat_name} chat's schedule: {chat_schedule['chosen_schedule']}")
                    
                #if the time for a message is inapropriete log it 
                else:
                    logging.info(f"Inappropriate time for a reminder: {gmt_plus_3_time.strftime('%H:%M:%S')} in chat {chat_name} last sent message at {last_time_message_sent[chat.id]} chat's schedule: {chat_schedule['chosen_schedule']}")
            #if time isn't in a schedule set the message_sent to false to be ready to send a new message
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

    gmt_plus_3_time = get_time_gmt3()
    
    #check if the timer is on in a chat
    if running_chats.get(chat.id, False):
        running_chats[chat.id] = False
        logging.info(f"Timer was stopped at {gmt_plus_3_time.strftime('%d %H:%M:%S')} by {user} at chat {(chat_name,chat.id)}")
        message = await query.message.answer(text="Таймер остановлен")
    
    else:
        message = await query.message.answer(text="Таймер не запущен")
        logging.info(f"{user} tried to stop the timer in chat {(chat_name,chat.id)} while timer is not active")
    await query.answer()
    await timed_delete_message(message, 3)

