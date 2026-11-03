from flask import g
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from .config import MYSQL_URL

engine = create_engine(
    MYSQL_URL,
    pool_pre_ping=True,          # 保持开启，用于检测失效连接
    pool_recycle=1800,
    pool_reset_on_return=None,   # ★ 关键：禁用归还时的 rollback 重置
    future=True
)

SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
)


def get_db():
    if "db" not in g:
        g.db = SessionLocal()
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
    SessionLocal.remove()