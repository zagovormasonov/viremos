from fastapi import APIRouter

psychologist_router = APIRouter(tags=["Психолог"])

@psychologist_router.get("/")
async def get_psychologist_home():
    return {"message": "Добро пожаловать в кабинет психолога"}