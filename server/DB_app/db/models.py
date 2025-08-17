from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Integer, BigInteger, Boolean, DateTime, ForeignKey, MetaData
)
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

# 선택 1) Base에 스키마 지정 (search_path를 코드에서 강제했다면 생략 가능)
metadata = MetaData(schema="gameapp")
Base = declarative_base(metadata=metadata)

# users --------------------------------------------------------

class UserORM(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    progresses = relationship("UserStageProgressORM", back_populates="user")

# stages -------------------------------------------------------

class StageORM(Base):
    __tablename__ = "stages"

    stage_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, index=True)   # 'A1' ~ 'E5'
    next_stage_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stages.stage_id"), nullable=True)

    next_stage = relationship("StageORM", remote_side=[stage_id])
    progresses = relationship("UserStageProgressORM", back_populates="stage")

# user_stage_progress ------------------------------------------

class UserStageProgressORM(Base):
    __tablename__ = "user_stage_progress"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    stage_id: Mapped[int] = mapped_column(ForeignKey("stages.stage_id"), primary_key=True)

    unlocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cleared:  Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    prompt_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    clear_time_ms: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    cleared_at:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("UserORM", back_populates="progresses")
    stage = relationship("StageORM", back_populates="progresses")

# run_logs -----------------------------------------------------

class RunLogORM(Base):
    __tablename__ = "run_logs"

    record_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id:   Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    stage_code: Mapped[str] = mapped_column(String(8), ForeignKey("stages.code"), index=True)

    prompt_length: Mapped[int] = mapped_column(Integer, nullable=False)
    clear_time_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cleared_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)