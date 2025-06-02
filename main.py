from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import openai
import os
import json
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Инициализация приложения
app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить все источники (можно указать конкретные)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модель входных данных
class CardInput(BaseModel):
    situation: str
    thoughts: str
    emotions: str
    behavior: str

# Эндпоинт для получения карточки и генерации упражнений
@app.post("/", response_class=JSONResponse)
async def submit_card(card: CardInput):
    try:
        # Формирование промпта для OpenAI
        prompt = f"""
Пользователь предоставил следующую информацию о своей ситуации:

Ситуация: {card.situation}
Мысли: {card.thoughts}
Эмоции: {card.emotions}
Поведение: {card.behavior}

Пожалуйста, предоставьте ответ в формате JSON, содержащем массив упражнений. Каждое упражнение должно быть представлено как объект со следующими полями:
•  'title': строка — название упражнения.
•  'duration': строка — примерное время выполнения.
•  'description': строка — краткое описание упражнения.
•  'instructions': строка — общие инструкции.
•  'steps': массив объектов с:
    •  'stepTitle': строка — название шага.
    •  'stepDescription': строка — что делать.
    •  'inputRequired': true/false — нужно ли ввести текст.
Ответ должен быть ТОЛЬКО в виде корректного JSON без лишнего текста.
"""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты когнитивный психолог."},
                {"role": "user", "content": prompt}
            ]
        )

        raw_result = response["choices"][0]["message"]["content"].strip()

        # Удаление лишнего, если ответ начинается с ```json
        if raw_result.startswith("```json"):
            raw_result = raw_result.removeprefix("```json").removesuffix("```").strip()

        # Парсинг JSON
        json_data = json.loads(raw_result)

        return {"result": json_data}

    except Exception as e:
        print("❌ Ошибка:", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Локальный запуск
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
