from datetime import datetime
from sqlalchemy import String, Integer, BigInteger, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column, declarative_base

Base = declarative_base()

class RunLogORM(Base):
    __tablename__ = "run_logs"

    seq:        Mapped[int]       = mapped_column(primary_key=True, autoincrement=True)
    id:         Mapped[str]       = mapped_column(String(64), index=True)
    stage:      Mapped[str]       = mapped_column(String(4), index=True)
    tokens:     Mapped[int]       = mapped_column(Integer)
    clear_time: Mapped[int]       = mapped_column(BigInteger)
    created_at: Mapped[datetime]  = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False
    )