from fastapi import APIRouter
from db import database
from models import cards
from schemas import Card, CardCreate

router = APIRouter(prefix="/client/cards", tags=["Client Cards"])

@router.get("/{user_id}", response_model=list[Card])
async def get_cards(user_id: str):
    query = cards.select().where(cards.c.user_id == user_id, cards.c.role == "client")
    return await database.fetch_all(query)

@router.post("/", response_model=Card)
async def create_card(card: CardCreate):
    query = cards.insert().values(**card.dict())
    card_id = await database.execute(query)
    return {**card.dict(), "id": card_id}