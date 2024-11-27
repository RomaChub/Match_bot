from sqlalchemy import AsyncAdaptedQueuePool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from config import settings

engine = create_async_engine(settings.get_database_url, poolclass=AsyncAdaptedQueuePool)
new_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class AboutOrm(Base):
    __tablename__ = "about"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[str]
    dialog: Mapped[str]
    tread_id: Mapped[str]


