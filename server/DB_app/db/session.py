from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from DB_app.config import settings

engine = create_async_engine(settings.database_url, pool_size=10, max_overflow=20)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        # 테스트 환경이라면 테이블 자동 생성
        # await conn.run_sync(Base.metadata.create_all)
        pass

async def dispose_db():
    await engine.dispose()