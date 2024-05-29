from sqlmodel import Field, Session, SQLModel, create_engine, select, delete, BigInteger,Column
from sqlalchemy.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.engine import URL

from os import getenv
from aiogram.types import Message, CallbackQuery

#Database setup
class Member(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str | None
    first_name: str
    telegram_id: int = Field(sa_column=Column(BigInteger()))
    chat_id: int = Field(sa_column=Column(BigInteger()))

connection_string = URL.create(
    drivername = "mysql",
    username = "avnadmin",
    password = "AVNS_Z5L5KnaciZGPX-hq1AT",
    host = "allience-alliencedb.i.aivencloud.com",
    port = 28670,
    database = "defaultdb",
)

engine = create_engine(connection_string)
#End database setup

def to_dict(obj):
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}

def get_members_by_chat(chat_id: int):
    with Session(engine) as session:
        listOfMembers = session.exec(select(Member).where(Member.chat_id == chat_id))
        #Have to convert to dict beacouse you can't pass a query without a session
        membersDict = [to_dict(member) for member in listOfMembers]
    return membersDict

def remove_member_from_list(call: Message | CallbackQuery):
    member = Member(
            username = call.from_user.username,
            first_name = call.from_user.first_name,
            telegram_id = call.from_user.id,
            chat_id = call.chat.id if isinstance(call, Message) else call.message.chat.id
        )
    with Session(engine) as session:
        statement = session.exec(select(Member).where(Member.telegram_id == member.telegram_id, Member.chat_id == member.chat_id))
        try: 
            session.delete(statement.one())
            session.commit()
            return True 
        except (NoResultFound, MultipleResultsFound):
            session.commit()
            return False
        
def add_member_to_list(call: Message | CallbackQuery):
    member = Member(
            username = call.from_user.username,
            first_name = call.from_user.first_name,
            telegram_id = call.from_user.id,
            chat_id = call.chat.id if isinstance(call, Message) else call.message.chat.id
        )   
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
        
if __name__ == "__main__":
    with Session(engine) as session:
        statement = delete(Member)
        result = session.exec(statement)
        session.commit()
    SQLModel.metadata.create_all(engine)
            

        