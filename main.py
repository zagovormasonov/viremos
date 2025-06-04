from fastapi import FastAPI, Request
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

# Инициализация FastAPI
app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модель одной карточки
class CardInput(BaseModel):
    situation: str
    thoughts: str
    emotions: str
    behavior: str

# Модель списка карточек
class CompletedCardsRequest(BaseModel):
    cards: list[CardInput]

# Генерация упражнений по одной карточке
@app.post("/", response_class=JSONResponse)
async def generate_exercises(card: CardInput):
    try:
        prompt = f"""
Пользователь предоставил следующую информацию о своей ситуации:

Ситуация: {card.situation}
Мысли: {card.thoughts}
Эмоции: {card.emotions}
Поведение: {card.behavior}

Пожалуйста, предоставьте ответ на русском языке в формате JSON, содержащем массив упражнений. Каждое упражнение должно быть представлено как объект со следующими полями:
• 'title': строка — название упражнения.
• 'duration': строка — примерное время выполнения.
• 'description': строка — краткое описание упражнения.
• 'instructions': строка — общие инструкции.
• 'steps': массив объектов с:
    • 'stepTitle': строка — название шага.
    • 'stepDescription': строка — что делать.
    • 'inputRequired': true/false — нужно ли ввести текст.
Ответ должен быть ТОЛЬКО в виде корректного JSON без лишнего текста.
"""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты когнитивный психолог."},
                {"role": "user", "content": prompt}
            ]
        )

        result = response["choices"][0]["message"]["content"].strip()

        # Удаление лишнего форматирования
        if result.startswith("```json"):
            result = result.removeprefix("```json").removesuffix("```").strip()

        exercises = json.loads(result)
        return {"result": exercises}

    except Exception as e:
        print("❌ Ошибка:", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Обработка всех завершённых карточек
@app.post("/analyze_completed", response_class=JSONResponse)
async def analyze_completed_cards(request: CompletedCardsRequest):
    try:
        summaries = []
        for i, card in enumerate(request.cards):
            summary_text = f"""
Карточка {i+1}:
Ситуация: {card.situation}
Мысли: {card.thoughts}
Эмоции: {card.emotions}
Поведение: {card.behavior}
"""
            summaries.append(summary_text)

        full_prompt = (
            "Ниже представлены завершённые CBT-карточки пользователя. "
            "Проанализируй их и сделай общий вывод о типичных мыслях, эмоциях и паттернах поведения. "
            "Дай рекомендации по улучшению психологического состояния пользователя.\n\n"
            + "\n".join(summaries)
        )

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты опытный когнитивный психолог."},
                {"role": "user", "content": full_prompt}
            ]
        )

        result = response["choices"][0]["message"]["content"].strip()
        return {"summary": result}

    except Exception as e:
        print("❌ Ошибка при анализе завершённых карточек:", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Запуск локального сервера
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
