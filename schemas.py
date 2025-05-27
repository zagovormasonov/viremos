from pydantic import BaseModel

class CardBase(BaseModel):
    situation: str
    thoughts: str
    emotions: str

class CardCreate(CardBase):
    client_id: int

class Card(CardBase):
    id: int
    response: str