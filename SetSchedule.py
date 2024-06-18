import logging

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message,CallbackQuery
from aiogram.fsm.storage.redis import RedisStorage

from dotenv import load_dotenv
from os import getenv

from common import timed_delete_message
from redis.asyncio import Redis 

load_dotenv()

r = Redis(host=getenv("REDIS_HOST"),
          port=getenv("REDIS_PORT"),
          password=getenv("REDIS_PASSWORD"),
          )

storage = RedisStorage(redis=r) 

router = Router()

class Schedule(StatesGroup):
    scheduledTime = State()

@router.callback_query(F.data == "setschedule")
async def set_schedule(query: CallbackQuery, state: FSMContext):
    new_message = await query.message.answer(text="Введи время отправки сообщений через запятую.\n\nПример: 12,13,14,....",)
    await query.answer()
    await state.set_state(Schedule.scheduledTime)
    await timed_delete_message(message_id=new_message.message_id, chat_id=new_message.chat.id, awaitTilDelete=10)
    
@router.message(Schedule.scheduledTime, Command(commands=["cancel"]))
@router.message(Schedule.scheduledTime, F.text.lower() == "отмена")
async def cmd_cancel(message: Message, state: FSMContext):
    await state.set_state(state = None)
    new_message = await message.answer(text="Действие отменено")

    chat = message.chat
    user = message.from_user.username if  message.from_user.username else message.from_user.first_name
    chat_name = chat.title if chat.title else chat.username
    logging.info(f"Schedule creation canceled in chat {(chat.id,chat_name)} by {user}")
    await timed_delete_message(message_id=new_message.message_id, chat_id=new_message.chat.id)
    await timed_delete_message(message_id=message.message_id, chat_id=message.chat.id)

@router.message(Schedule.scheduledTime, F.text.strip().regexp(r"^\d+(,\d+)*$"))
async def schedule_chosen(message: Message, state: FSMContext):
    #convert data to a set to remove duplicates and back to a list to store it
    chosen_times = list(set(message.text.split(sep = ",")))
    #convert all the str to int and sort them
    chosen_schedule = [int(time) for time in chosen_times if int(time) <= 23]
    chosen_schedule.sort()

    await state.update_data(chosen_schedule=chosen_schedule)
    new_message = await message.answer(text="Спасибо. Время напоминаний записаны",)

    chat = message.chat
    user = message.from_user.username if  message.from_user.username else message.from_user.first_name
    chat_name = chat.title if chat.title else chat.username
    logging.info(f"New schedule created for chat {(chat.id, chat_name)} by user {user}, chat's schedule {chosen_schedule}")

    await state.set_state(state = None)
    await timed_delete_message(message_id=message.message_id, chat_id=message.chat.id)
    await timed_delete_message(message_id=new_message.message_id, chat_id=new_message.chat.id)

@router.message(Schedule.scheduledTime)
async def schedule_chosen_incorrectly(message: Message, state: FSMContext):
    new_message = await message.answer(text="Введи время отсылания сообщений через кому, без пробелов.\n\nПример: 12,13,14,....",)
    
    await timed_delete_message(message_id=message.message_id, chat_id=message.chat.id)
    await timed_delete_message(message_id=new_message.message_id, chat_id=new_message.chat.id, awaitTilDelete=10)

@router.callback_query(F.data == "getschedule")
async def cmd_cancel_no_state(query: CallbackQuery, state: FSMContext):
    chat_schedule = await state.get_data()
    if chat_schedule:
        text = "Расписание напоминаний: "
        for time in chat_schedule['chosen_schedule']:
            if time == chat_schedule['chosen_schedule'][-1]:
                text += str(time)
            else:
                text += str(time)+", "
    else:
        text = "Раписание не назначено"
    new_message = await query.message.answer(text = text)
    await query.answer()
    await timed_delete_message(message_id=new_message.message_id, chat_id=new_message.chat.id)

@router.message(StateFilter(None), Command(commands=["cancel"]))
@router.message(StateFilter(None), F.text.lower() == "отмена")
async def cmd_cancel_no_state(message: Message, state: FSMContext):
    new_message = await message.answer(text="Нечего отменять")

    await timed_delete_message(message_id=message.message_id, chat_id=message.chat.id)
    await timed_delete_message(message_id=new_message.message_id, chat_id=new_message.chat.id)