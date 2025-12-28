from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def create_engine_from_url(database_url: str) -> Engine:
    if database_url.startswith("sqlite:///:memory:"):
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    if database_url.startswith("sqlite:"):
        return create_engine(database_url, connect_args={"check_same_thread": False})
    return create_engine(database_url)


def create_sessionmaker(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)
