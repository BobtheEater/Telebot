import DBLoad
import logging

from common import timed_delete_message

from aiogram import Bot, Router, F
from aiogram.filters import JOIN_TRANSITION, LEAVE_TRANSITION
from aiogram.filters.command import Command
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter
from aiogram.types import Message, ChatMemberUpdated, CallbackQuery, Chat


memberrouter = Router()

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
async def get_reminder_text(chat:Chat):
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

    text += call 
    
    logging.info(f"Message | {text} | sent at chat {(chat_name, chat.id)}")
     
    return text

#secret command to get all of the database entries
@memberrouter.message(Command("checkall"))
async def get_all_members(message: Message, bot: Bot):
    allMembers = DBLoad.get_all_members()
    for member in allMembers:
        await bot.send_message(chat_id=message.chat.id, text=str(member))

#removes a users id, username and firstname from the Database and notifies a user
@memberrouter.callback_query(F.data == "rmme")
async def rmme_callback(query: CallbackQuery, bot: Bot):
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
@memberrouter.callback_query(F.data == "addme")
async def addme_callback(query: CallbackQuery, bot: Bot):
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
@memberrouter.chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def new_member_handler(event: ChatMemberUpdated, bot: Bot):
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
@memberrouter.chat_member(ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION))
async def left_member_handler(event: ChatMemberUpdated, bot: Bot):
    member = event.old_chat_member.user
    if member.id != bot.id:
        if DBLoad.remove_member_from_db(member, event.chat.id):
            logging.info(f"""User {(member.username, member.first_name,
                                    member.id, event.chat.id)} removed from the database""")
            await event.answer(text=f"Пользователь {member.first_name} был удален из списка")
        else:
            logging.info(f"""User {(member.username, member.first_name,
                                    member.id, event.chat.id)} tried to be removed from the database and was not found""")