from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from social_video_formatter.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    from social_video_formatter.models import db_models  # noqa: F401
    Base.metadata.create_all(bind=engine)
