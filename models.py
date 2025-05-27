from pydantic import BaseModel
from uuid import UUID

class CardIn(BaseModel):
    user_id: UUID
    situation: str
    thoughts: str
    emotions: str
    intensity: int

class CardOut(CardIn):
    id: UUID
