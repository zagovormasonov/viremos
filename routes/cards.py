from fastapi import APIRouter, Depends
from db import database, cbt_cards
from models import CardIn, CardOut
import uuid

router = APIRouter(prefix="/cards", tags=["CBT Cards"])

@router.post("/", response_model=CardOut)
async def create_card(card: CardIn):
    query = cbt_cards.insert().values(
        id=uuid.uuid4(),
        user_id=card.user_id,
        situation=card.situation,
        thoughts=card.thoughts,
        emotions=card.emotions,
        intensity=card.intensity
    )
    await database.execute(query)
    return {**card.dict(), "id": str(uuid.uuid4())}
