from fastapi import APIRouter

client_router = APIRouter(tags=["Клиент"])

@client_router.get("/")
async def get_client_home():
    return {"message": "Добро пожаловать в кабинет клиента"}
