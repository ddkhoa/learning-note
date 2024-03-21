from sqlalchemy import Column, Index
from sqlalchemy.ext.declarative import declarative_base

import enum
from sqlalchemy.dialects.postgresql import INTEGER, ENUM, TEXT

Base = declarative_base()
metadata = Base.metadata


class MyEnum(enum.Enum):
    one = 1
    two = 2
    three = 3


class TestTable(Base):
    __tablename__ = "test"
    id = Column(INTEGER(), primary_key=True)
    name = Column(TEXT(), nullable=False)
    enum_field = Column(ENUM(MyEnum))

    __table_args__ = (
        Index(
            "test_name_idx",
            name,
        ),
    )


class TestTable2(Base):
    __tablename__ = "test2"
    id = Column(INTEGER(), primary_key=True)
    email = Column(TEXT(), nullable=False)
    enum_field = Column(ENUM(MyEnum))


# class TestTable3(Base):
#     __tablename__ = "test3"
#     id = Column(INTEGER(), primary_key=True)
#     enum_field = Column(ENUM(MyEnum))
