import asyncio, asyncpg, os
url = os.getenv("DATABASE_URL", "postgresql://user:1234@localhost:5432/dalgona_game")
async def main():
    conn = await asyncpg.connect(dsn=url.replace("+asyncpg",""))  # asyncpg는 postgresql:// 형식 사용
    v = await conn.fetchval("SELECT version();")
    print(v)
    await conn.close()
asyncio.run(main())