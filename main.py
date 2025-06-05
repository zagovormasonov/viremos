from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import openai
import os
import json
from dotenv import load_dotenv
import uuid
from pydub import AudioSegment
import tempfile

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

# Путь к фоновой музыке
BACKGROUND_MUSIC_PATH = "audio/background_music.mp3"

@app.post("/generate-meditation")
async def generate_meditation(card: CardInput):
    try:
        # Генерация текста медитации с учётом данных карточки
        prompt = f"""
Сгенерируй короткую медитацию с легкой музыкой на заднем фоне, на русском языке в женском спокойном стиле, длительностью до 2 минут. 
Начни с фразы "Устройся удобно..." и используй расслабляющий, поддерживающий тон.
Учти следующую информацию о ситуации пользователя:
Ситуация: {card.situation}
Мысли: {card.thoughts}
Эмоции: {card.emotions}
Поведение: {card.behavior}
"""

        chat_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты медитативный гид."},
                {"role": "user", "content": prompt}
            ]
        )

        meditation_text = chat_response.choices[0].message.content.strip()

        # Генерация уникального имени файла
        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        # Преобразование текста в речь (MP3)
        speech_response = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=meditation_text,
            response_format="mp3"
        )

        # Создаем временный файл для TTS
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_tts_file:
            temp_tts_file.write(speech_response.content)
            temp_tts_file_path = temp_tts_file.name

        try:
            # Загружаем голос и фоновую музыку
            voice_audio = AudioSegment.from_mp3(temp_tts_file_path)
            background_music = AudioSegment.from_mp3(BACKGROUND_MUSIC_PATH)

            # Урезаем фоновую музыку до длины голосового аудио
            background_music = background_music[:len(voice_audio)]

            # Уменьшаем громкость фоновой музыки (например, на -20 дБ)
            background_music = background_music - 30

            # Накладываем фоновую музыку на голос
            combined_audio = voice_audio.overlay(background_music)

            # Сохраняем ит tradesоговый аудиофайл
            combined_audio.export(filepath, format="mp3")

            # Возврат файла
            return FileResponse(
                path=filepath,
                media_type="audio/mpeg",
                filename="meditation.mp3"
            )

        finally:
            # Удаляем временный файл TTS
            if os.path.exists(temp_tts_file_path):
                os.remove(temp_tts_file_path)

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
Ответ должен быть ТОЛЬКО вложенный JSON без лишнего текста.
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