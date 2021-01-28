# coding: utf-8
from sqlalchemy import BigInteger, Column, DateTime, String, UniqueConstraint, text, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata

class Comment(Base):
    __tablename__ = 'comments'

    id = Column(BigInteger, primary_key=True, server_default=text("nextval('diagnostics_id_seq'::regclass)"))
    sensor_id = Column(BigInteger, index=True)
    created_at = Column(DateTime(True))
    comment = Column(String(255))
    created_by = Column(String(255))


class Ignore(Base):
    __tablename__ = 'ignores'

    id = Column(BigInteger, primary_key=True, server_default=text("nextval('sensors_id_seq'::regclass)"))
    created_at = Column(DateTime(True))
    ignore_untill = Column(DateTime(True))
    sensor_id = Column(BigInteger)
    reason = Column(String(255))
    created_by = Column(String(255))


class Incident(Base):
    __tablename__ = 'incidents'
    __table_args__ = (
        UniqueConstraint('sensor_id', 'start_at'),
    )

    id = Column(BigInteger, primary_key=True, server_default=text("nextval('installations_id_seq'::regclass)"))
    sensor_id = Column(BigInteger, index=True)
    start_at = Column(DateTime(True))
    end_at = Column(DateTime(True))
    created_at = Column(DateTime)
    alert_at = Column(DateTime)
    ignored = Column(Boolean, nullable=False, server_default=text("false"))