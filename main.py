from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import openai
import os
import json
from dotenv import load_dotenv
import uuid

# Загрузка переменных окружения
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Инициализация клиента OpenAI
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Инициализация FastAPI
app = FastAPI()

# Разрешение CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

# Создаём директорию для аудио, если её нет
AUDIO_DIR = "audios"
os.makedirs(AUDIO_DIR, exist_ok=True)

@app.get("/generate-meditation")
async def generate_meditation():
    try:
        # Генерация текста медитации
        prompt = """
Сгенерируй короткую медитацию на русском языке в женском спокойном стиле, длительностью до 2 минут. Начни с фразы "Устройся удобно..." и используй расслабляющий, поддерживающий тон.
"""

        chat_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты медитативный гид."},
                {"role": "user", "content": prompt}
            ]
        )

        meditation_text = chat_response.choices[0].message.content.strip()

        # Генерация уникального имени файла
        filename = f"{uuid.uuid4()}.ogg"
        filepath = os.path.join(AUDIO_DIR, filename)

        # Преобразование текста в речь (OGG)
        speech_response = client.audio.speech.create(
            model="tts-1",
            voice="nova",  # Женский голос
            input=meditation_text,
            response_format="ogg"
        )

        # Сохранение аудио
        with open(filepath, "wb") as f:
            f.write(speech_response.content)

        # Возврат файла
        return FileResponse(
            path=filepath,
            media_type="audio/ogg",
            filename="meditation.ogg"
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# Эндпоинт генерации упражнений
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

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты когнитивный психолог."},
                {"role": "user", "content": prompt}
            ]
        )

        result = response.choices[0].message.content.strip()

        # Очистка от обёртки ```json
        if result.startswith("```json"):
            result = result.removeprefix("```json").removesuffix("```").strip()

        exercises = json.loads(result)

        return {"result": exercises}

    except Exception as e:
        print("❌ Ошибка:", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Запуск локально
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)