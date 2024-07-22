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
from keyboard import generate_menu
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
    scheduledDay = State()

@router.callback_query(StateFilter(None), F.data == "setschedule")
async def choose_schedule(query: CallbackQuery, state: FSMContext):
    menu = {"Назначить время":"setscheduletime",
            "Назначить день":"setscheduleday",}

    await query.message.answer(text = "Назначить дни или само время?", reply_markup=generate_menu(menu))
    await query.answer()

#Section to set the time of day in a schedule
@router.callback_query(F.data == "setscheduletime")
async def set_schedule(query: CallbackQuery, state: FSMContext):
    new_message = await query.message.answer(text="Введи время отправки сообщений через запятую.\n\nПример: 12,13,14,....",)
    await query.answer()
    await state.set_state(Schedule.scheduledTime)
    await timed_delete_message(new_message, awaitTilDelete=10)

#Section to set the days of the week in a schedule
@router.callback_query(F.data == "setscheduleday")
async def set_schedule(query: CallbackQuery, state: FSMContext):
    new_message = await query.message.answer(text="""Введи числа дней отправки сообщений через запятую, без пробелов.
Пн - 0;
Вт - 1;
Ср - 2;
Чт - 3;
Пт - 4;
Сб - 5;
Вс - 6;""",)
    await query.answer()
    await state.set_state(Schedule.scheduledDay)
    await timed_delete_message(new_message, awaitTilDelete=10)

@router.message(StateFilter(Schedule.scheduledTime,Schedule.scheduledDay), Command(commands=["cancel"]))
@router.message(StateFilter(Schedule.scheduledTime,Schedule.scheduledDay), F.text.lower() == "отмена")
async def cmd_cancel(message: Message, state: FSMContext):
    await state.set_state(state = None)
    new_message = await message.answer(text="Установка расписания отмененa")

    chat = message.chat
    user = message.from_user.username if  message.from_user.username else message.from_user.first_name
    chat_name = chat.title if chat.title else chat.username
    logging.info(f"Schedule creation canceled in chat {(chat.id,chat_name)} by {user}")
    
    await timed_delete_message(message)
    await timed_delete_message(new_message)

#store chats schedule in hours (0-23) 
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
    await timed_delete_message(message)
    await timed_delete_message(new_message)

#store weekdays for schedule (0-6)
@router.message(Schedule.scheduledDay, F.text.strip().regexp(r"^\d+(,\d+)*$"))
async def schedule_chosen(message: Message, state: FSMContext):
    #convert data to a set to remove duplicates and back to a list to store it
    chosen_days = list(set(message.text.split(sep = ",")))
    #convert all the str to int and sort them
    chosen_schedule_days = [int(day) for day in chosen_days if int(day) <= 6]
    chosen_schedule_days.sort()

    await state.update_data(chosen_days=chosen_schedule_days)
    new_message = await message.answer(text="Спасибо. Дни напоминаний записаны",)

    chat = message.chat
    user = message.from_user.username if  message.from_user.username else message.from_user.first_name
    chat_name = chat.title if chat.title else chat.username
    logging.info(f"New DAY schedule created for chat {(chat.id, chat_name)} by user {user}, chat's schedule {chosen_schedule_days}")

    await state.set_state(state = None)
    await timed_delete_message(message)
    await timed_delete_message(new_message)

@router.message(Schedule.scheduledTime)
async def schedule_chosen_incorrectly(message: Message, state: FSMContext):
    new_message = await message.answer(text="Введи время отсылания сообщений через кому, без пробелов.\n\nПример: 12,13,14,....",)
    
    await timed_delete_message(message)
    await timed_delete_message(new_message, 10)

@router.message(Schedule.scheduledDay)
async def day_schedule_chosen_incorrectly(message: Message, state: FSMContext):
    new_message = await message.answer(text="""Введи числа дней отправки сообщений через запятую, без пробелов.
Пн - 0;
Вт - 1;
Ср - 2;
Чт - 3;
Пт - 4;
Сб - 5;
Вс - 6;""",)
    await timed_delete_message(message)
    await timed_delete_message(new_message, 10)


@router.callback_query(F.data == "getschedule")
async def cmd_cancel_no_state(query: CallbackQuery, state: FSMContext):
    int_to_days = {0:"Пн",1:"Вт",2:"Ср",3:"Чт",4:"Пт",5:"Сб",6:"Вс",}

    chat_schedule = await state.get_data()
    if chat_schedule:
        text = "Время напоминаний: "
        for time in chat_schedule['chosen_schedule']:
            if time == chat_schedule['chosen_schedule'][-1]:
                text += str(time)
            else:
                text += str(time)+", "
        text += "\nДни напоминаний: "        
        for day in chat_schedule['chosen_days']:
            if day == chat_schedule['chosen_days'][-1]:
                text += str(int_to_days[day])
            else:
                text += str(int_to_days[day])+", "
    else:
        text = "Раписание не назначено"
    new_message = await query.message.answer(text = text)
    await query.answer()
    await timed_delete_message(new_message)
