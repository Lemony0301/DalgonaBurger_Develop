from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, update
from DB_app.config import settings
from DB_app.db.models import Base, StageORM, UserORM, UserStageProgressORM

engine = create_async_engine(
    settings.database_url,          # postgresql+asyncpg://...
    pool_pre_ping=True,
    connect_args={
        "server_settings": {
            "search_path": "gameapp,public"   # ← 여기서 스키마 고정
        }
    },
)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    # 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 스테이지 시드 (A1~A5, B1~B5, ... E1~E5)
    async with async_session() as session, session.begin():
        exists = (await session.execute(select(StageORM).limit(1))).scalars().first()
        if not exists:
            groups = ["A", "B", "C", "D", "E"]
            stages = []

            for g in groups:
                for i in range(1, 6):
                    stages.append(StageORM(code=f"{g}{i}"))
            session.add_all(stages)
            await session.flush()  # stage_id 채우기

            # next_stage_id 연결
            code_to_obj = {st.code: st for st in stages}
            for g in groups:
                for i in range(1, 5):  # g1→g2, g2→g3, ...
                    cur = code_to_obj[f"{g}{i}"]
                    nxt = code_to_obj[f"{g}{i+1}"]
                    cur.next_stage_id = nxt.stage_id

async def dispose_db():
    await engine.dispose()