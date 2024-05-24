from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy.exc import NoResultFound, MultipleResultsFound

from aiogram.types import Message, CallbackQuery
#Database setup


class Member(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str | None
    first_name: str
    telegram_id: int = Field(index=True)
    chat_id: int = Field(index=True)

sqlite_file_name = "allience.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, echo=False)
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
            telegram_id= call.from_user.id,
            chat_id = call.chat.id if isinstance(call, Message) else call.message.chat.id
        )
    with Session(engine) as session:
        statement = session.exec(select(Member).where(Member.telegram_id == member.telegram_id, Member.chat_id == member.chat_id))
        try: 
            session.delete(statement.one())
            session.commit()
            return True 
        except (NoResultFound, MultipleResultsFound):
            return False
        
def add_member_to_list(call: Message | CallbackQuery):
    member = Member(
            username = call.from_user.username,
            first_name = call.from_user.first_name,
            telegram_id= call.from_user.id,
            chat_id = call.chat.id if isinstance(call, Message) else call.message.chat.id
        )
    with Session(engine) as session:
        statement = session.exec(select(Member).where(Member.telegram_id == member.telegram_id, Member.chat_id == member.chat_id))
        try: 
            statement.one()
            return False
        except (NoResultFound, MultipleResultsFound):
            session.add(member)
            session.commit()
            return True
        
if __name__ == "__main__":
    SQLModel.metadata.create_all(engine)
            

        