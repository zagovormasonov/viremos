import asyncio
from databases import Database

# 🔧 Вставь сюда свою строку подключения:
DATABASE_URL = "postgresql://postgres.ehnguyuzpffqzaednrnn:z8O26qYv4Perh997@aws-0-eu-west-2.pooler.supabase.com:6543/postgres"

async def test_connection():
    database = Database(DATABASE_URL)
    try:
        print("🔌 Connecting to database...")
        await database.connect()
        print("✅ Connected successfully!")

        # Пробуем простой запрос
        result = await database.fetch_one("SELECT 1;")
        print("📄 Query result:", result)

    except Exception as e:
        print("❌ Error while connecting to DB:")
        print(e)
    finally:
        await database.disconnect()
        print("🔌 Disconnected.")

if __name__ == "__main__":
    asyncio.run(test_connection())