from sqlmodel import Field, Session, SQLModel, create_engine, select, delete, BigInteger,Column
from sqlalchemy.exc import NoResultFound, MultipleResultsFound, OperationalError
from sqlalchemy.engine import URL

from dotenv import load_dotenv
from os import getenv

from aiogram.types import Message, CallbackQuery, User

#Database setup
class Member(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str | None
    first_name: str
    telegram_id: int = Field(sa_column=Column(BigInteger()))
    chat_id: int = Field(sa_column=Column(BigInteger()))

#added dotenv to hide info
load_dotenv()
connection_string = URL.create(
    drivername = getenv("DRIVERNAME"),
    username = getenv("USERNAME"),
    password = getenv("PASSWORD"),
    host = getenv("HOST"),
    port = getenv("PORT"),
    database = getenv("DATABASE"),
)

engine = create_engine(connection_string)
#End database setup

#convert sqlmodel object to dict, needed beacause you cand pass the object out of session 
def to_dict(obj):
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}

def call_to_member(call: Message | CallbackQuery):
    member = Member(
            username = call.from_user.username,
            #in case someone doesnt have a first name treat the last name as first 
            first_name = call.from_user.first_name if call.from_user.first_name else call.from_user.last_name, 
            telegram_id = call.from_user.id,
            #check if the call was from a message just in case
            chat_id = call.chat.id if isinstance(call, Message) else call.message.chat.id, 
        )
    return member

#func for selecting all members in a chat
def get_members_by_chat(chat_id: int):
    try:
        with Session(engine) as session:
            listOfMembers = session.exec(select(Member).where(Member.chat_id == chat_id))
            #Have to convert to dict beacouse you can't pass a query without a session
            membersDict = [to_dict(member) for member in listOfMembers]

    #if connection to the database is lost - retry
    except(OperationalError):
        membersDict = get_members_by_chat(chat_id)  
    return membersDict

#func for selecting all members 
def get_all_members() -> dict[str: str|int]:
    try:
        with Session(engine) as session:
            listOfMembers = session.exec(select(Member))
            membersDict = [to_dict(member) for member in listOfMembers]
    except(OperationalError):
        membersDict = get_all_members()
    return membersDict

#remove member from the database
def remove_member_from_list(call: Message | CallbackQuery):
    member = call_to_member(call)
    with Session(engine) as session:
        statement = session.exec(select(Member).where(Member.telegram_id == member.telegram_id, Member.chat_id == member.chat_id))
        try: 
            session.delete(statement.one())
            session.commit()
            return True 
        except (NoResultFound, MultipleResultsFound):
            session.commit()
            return False

#add member to the databasae     
def add_member_to_list(call: Message | CallbackQuery):
    member = call_to_member(call)
    with Session(engine) as session:
        statement = session.exec(select(Member).where(Member.telegram_id == member.telegram_id, Member.chat_id == member.chat_id))
        try: 
            statement.one()
            session.commit()
            return False
        except (NoResultFound):
            session.add(member)
            session.commit()
            return True
        
def message_to_member_for_db_handler(user: User, chatId: int):
    member = Member(
            username = user.username,
            #in case someone doesnt have a first name treat the last name as first 
            first_name = user.first_name if user.first_name else user.last_name, 
            telegram_id = user.id,
            #check if the call was from a message just in case
            chat_id = chatId
            )
    return member

def new_chat_member_db_handler(user: User, chatId: int):
    member = message_to_member_for_db_handler(user, chatId)
    with Session(engine) as session:
        statement = session.exec(select(Member).where(Member.telegram_id == member.telegram_id, Member.chat_id == member.chat_id))
        try: 
            statement.one()
            session.commit()
            return False
        except (NoResultFound):
            session.add(member)
            session.commit()
            return True

def chat_member_removed_dbhandler(user: User, chatId: int):
    member = message_to_member_for_db_handler(user, chatId)
    with Session(engine) as session:
        statement = session.exec(select(Member).where(Member.telegram_id == member.telegram_id, Member.chat_id == member.chat_id))
        try: 
            session.delete(statement.one())
            session.commit()
            return True 
        except (NoResultFound, MultipleResultsFound):
            session.commit()
            return False
        

#if this code is run directly will drop the table and create a a new empty copy 
if __name__ == "__main__":
    with Session(engine) as session:
        """ statement = delete(Member)
        result = session.exec(statement)
        session.commit()"""
        statement = select(Member).where(Member.telegram_id == "", Member.chat_id == "")
        session.exec(statement)
        session.commit()
    #SQLModel.metadata.create_all(engine)
            

        