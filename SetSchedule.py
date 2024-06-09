from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message,CallbackQuery
from aiogram.fsm.storage.redis import RedisStorage

from dotenv import load_dotenv
from os import getenv

from MainMenu import timed_delete_message
from redis.asyncio import Redis 

load_dotenv()

r = Redis(host=getenv("REDIS_HOST"),
          port=getenv("REDIS_PORT"),
          password=getenv("REDIS_PASSWORD"))

storage = RedisStorage(redis=r) 

router = Router()

class Schedule(StatesGroup):
    scheduledTime = State()

@router.callback_query(F.data == "setschedule")
async def set_schedule(query: CallbackQuery, state: FSMContext):
    new_message = await query.message.answer(text="Введи время отсилания сообщений через кому.\n\nПример: 12,13,14,....",)
    await query.answer()
    await state.set_state(Schedule.scheduledTime)
    await timed_delete_message(message_id=new_message.message_id, chat_id=new_message.chat.id, awaitTilDelete=10)
    
@router.message(Schedule.scheduledTime, F.text.strip().regexp(r"^\d+(,\d+)*$"))
async def schedule_chosen(message: Message, state: FSMContext):
    #convert data to a set to remove duplicates and back to a list to store it
    await state.update_data(chosen_schedule=list(set(message.text.split(sep = ","))))
    new_message = await message.answer(text="Спасибо. Время напоминаний записаны",)

    await timed_delete_message(message_id=message.message_id, chat_id=message.chat.id)
    await timed_delete_message(message_id=new_message.message_id, chat_id=new_message.chat.id)
    await state.set_state(state = None)

@router.message(Schedule.scheduledTime)
async def schedule_chosen_incorrectly(message: Message, state: FSMContext):
    await state.update_data(chosen_schedule=message.text.strip().split(sep = ","))
    new_message = await message.answer(text="Введи время отсылания сообщений через кому, без пробелов.\n\nПример: 12,13,14,....",)
    
    await timed_delete_message(message_id=message.message_id, chat_id=message.chat.id)
    await timed_delete_message(message_id=new_message.message_id, chat_id=new_message.chat.id)

@router.message(Command("getSchedule"))
async def cmd_cancel_no_state(message: Message, state: FSMContext):
    chat_schedule = await state.get_data()
    if chat_schedule:
        await message.answer(text = f"Chat's schedule: {chat_schedule['chosen_schedule']}")
    else:
        await message.answer(text = "No schedule")


@router.message(StateFilter(None), Command(commands=["cancel"]))
@router.message(StateFilter(None), F.text.lower() == "отмена")
async def cmd_cancel_no_state(message: Message, state: FSMContext):
    # Стейт сбрасывать не нужно, удалим только данные
    new_message = await message.answer(text="Нечего отменять")

    await timed_delete_message(message_id=message.message_id, chat_id=message.chat.id)
    await timed_delete_message(message_id=new_message.message_id, chat_id=new_message.chat.id)

@router.message(Command(commands=["cancel"]))
@router.message(F.text.lower() == "отмена")
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    new_message = await message.answer(text="Действие отменено")

    await timed_delete_message(message_id=new_message.message_id, chat_id=new_message.chat.id)
    await timed_delete_message(message_id=message.message_id, chat_id=message.chat.id)