from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import openai
import os
import json
import time
from dotenv import load_dotenv
import uuid
from pydub import AudioSegment
import tempfile
import logging
from elevenlabs import generate, set_api_key

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")

if not openai_api_key or not elevenlabs_api_key:
    logger.error("Переменные OPENAI_API_KEY или ELEVENLABS_API_KEY не заданы")
    raise RuntimeError("Не заданы API-ключи")

# Настройка OpenAI
openai.api_key = openai_api_key

# Настройка ElevenLabs
set_api_key(elevenlabs_api_key)

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

# Директория для аудио
AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Путь к фоновой музыке
BACKGROUND_MUSIC_PATH = "audio/background_music.mp3"

@app.post("/generate-meditation")
async def generate_meditation(card: CardInput):
    try:
        logger.info(f"Получены данные: {card.dict()}")

        # Шаблон prompt для OpenAI
        prompt = f"""
Сгенерируй короткую медитацию (до 400 слов) на русском языке, в женском спокойном стиле, с медленным, расслабляющим тоном. 
Начни с фразы "Устройся удобно..." и создай медитацию длительностью около 3 минут. Используй следующую информацию:
Ситуация: {card.situation}
Мысли: {card.thoughts}
Эмоции: {card.emotions}
Поведение: {card.behavior}
"""

        # Генерируем текст через OpenAI
        chat_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты медитативный гид."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600
        )
        meditation_text = chat_response.choices[0].message["content"].strip()
        logger.info(f"Сгенерирован текст: {meditation_text[:100]}...")

        # Уникальное имя для mp3
        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        # Генерация речи через ElevenLabs
        try:
            # потоковые данные (stream=True) вернут генератор байтов
            audio_stream = generate(
                text=meditation_text,
                voice="Bella",                   # проверенный голос, поддерживает русский
                model="eleven_multilingual_v1",  # мультилингвальный, поддерживает русский
                stream=True
            )
            audio_bytes = b"".join(audio_stream)  # объединяем весь поток в bytes
        except Exception as e:
            logger.error(f"Ошибка TTS ElevenLabs: {e}")
            return JSONResponse(status_code=500, content={"error": "Ошибка при генерации аудио"})

        # Сохраняем результат во временный mp3-файл
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_file_path = temp_file.name

        try:
            voice_audio = AudioSegment.from_mp3(temp_file_path)
            logger.info(f"Длина голоса: {len(voice_audio) / 1000:.2f} сек")

            # Если есть фоновой трек — наложим его
            if os.path.exists(BACKGROUND_MUSIC_PATH):
                try:
                    background = AudioSegment.from_mp3(BACKGROUND_MUSIC_PATH)
                    # обрезаем фон до длины голоса и делаем его тише на 10 dB
                    background = background[: len(voice_audio)] - 10
                    combined = voice_audio.overlay(background)
                    combined.export(filepath, format="mp3", bitrate="64k")
                    logger.info(f"Комбинированный трек сохранён: {filepath}")
                except Exception as e:
                    logger.error(f"Ошибка наложения фоновой музыки: {e}")
                    # Если что-то пошло не так — просто сохраняем голос
                    voice_audio.export(filepath, format="mp3", bitrate="64k")
                    logger.info(f"Сохранён только голос: {filepath}")
            else:
                logger.warning("Фоновая музыка не найдена, сохраняем только голос")
                voice_audio.export(filepath, format="mp3", bitrate="64k")

            # Удаляем старые файлы из AUDIO_DIR (старше часа)
            now_ts = time.time()
            for old in os.listdir(AUDIO_DIR):
                old_path = os.path.join(AUDIO_DIR, old)
                if os.path.isfile(old_path) and now_ts - os.path.getmtime(old_path) > 3600:
                    os.remove(old_path)
                    logger.info(f"Удалён старый файл: {old_path}")

            # Отправляем готовый mp3-файл клиенту
            return FileResponse(
                path=filepath,
                media_type="audio/mpeg",
                filename="meditation.mp3"
            )

        finally:
            # В любом случае удаляем временный файл с голосом
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logger.info(f"Удалён временный файл TTS: {temp_file_path}")

    except Exception as e:
        logger.error(f"Ошибка всего процесса генерации медитации: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/", response_class=JSONResponse)
async def generate_exercises(card: CardInput):
    try:
        logger.info(f"Получены данные для упражнений: {card.dict()}")

        prompt = f"""
Пользователь описал свою ситуацию:
Ситуация: {card.situation}
Мысли: {card.thoughts}
Эмоции: {card.emotions}
Поведение: {card.behavior}

Сформируй JSON-массив упражнений следующего формата:
[
  {{
    "title": "Название",
    "duration": "Примерное время",
    "description": "Описание",
    "instructions": "Общие инструкции",
    "steps": [
      {{
        "stepTitle": "Название шага",
        "stepDescription": "Описание шага",
        "inputRequired": true/false
      }}
    ]
  }}
]
Ответ должен быть ТОЛЬКО валидным JSON.
"""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты когнитивный психолог."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        raw = response.choices[0].message["content"].strip()
        logger.info(f"Сырой ответ по упражнениям: {raw[:100]}...")

        if raw.startswith("```json"):
            raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            exercises = json.loads(raw)
            if not isinstance(exercises, list):
                logger.warning("Парсинг вернул не список, возвращаю пустой массив")
                exercises = []
        except Exception as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            exercises = []

        return {"result": exercises}

    except Exception as e:
        logger.error(f"Ошибка генерации упражнений: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# Для локального тестирования
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
