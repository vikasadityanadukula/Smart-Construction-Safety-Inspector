from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, Boolean, String


class Base(DeclarativeBase):
    pass


class Violation(Base):
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True, index=True)

    worker_id = Column(Integer)

    helmet = Column(Boolean)

    vest = Column(Boolean)

    zone = Column(String)

    time = Column(String)