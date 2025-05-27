from database import database
from schemas import CardCreate

async def create_card(card: CardCreate):
    query = """
        INSERT INTO cards (client_id, situation, thoughts, emotions, response)
        VALUES (:client_id, :situation, :thoughts, :emotions, :response)
        RETURNING id, client_id, situation, thoughts, emotions, response
    """
    values = {
        **card.dict(),
        "response": ""  # пока пустой ответ
    }
    return await database.fetch_one(query=query, values=values)

async def get_cards_by_client(client_id: int):
    query = "SELECT * FROM cards WHERE client_id = :client_id"
    return await database.fetch_all(query=query, values={"client_id": client_id})
