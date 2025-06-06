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
from elevenlabs.client import ElevenLabs  # используем клиент

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")

if not openai_api_key or not elevenlabs_api_key:
    logger.error("OPENAI_API_KEY или ELEVENLABS_API_KEY не заданы в окружении.")
    raise RuntimeError("Не заданы обязательные ключи API.")

# Настройка OpenAI (версия 0.28.x или аналогичная)
openai.api_key = openai_api_key

# Инициализация ElevenLabs-клиента
elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)

# Инициализация FastAPI
app = FastAPI()

# Разрешаем CORS для любых источников (при необходимости уточните)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic-модель входных данных
class CardInput(BaseModel):
    situation: str
    thoughts: str
    emotions: str
    behavior: str

# Директория для хранения сгенерированных mp3
AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Путь к файлу с фоновой музыкой (если есть)
BACKGROUND_MUSIC_PATH = "audio/background_music.mp3"

@app.post("/generate-meditation")
async def generate_meditation(card: CardInput):
    try:
        logger.info(f"Получены входные данные для медитации: {card.dict()}")

        # Сборка prompt для OpenAI
        prompt = f"""
Сгенерируй короткую медитацию (до 400 слов) на русском языке, в женском спокойном стиле, с медленным, расслабляющим тоном.
Начни с фразы "Устройся удобно..." и создай медитацию длительностью около 3 минут. Используй следующую информацию:
Ситуация: {card.situation}
Мысли: {card.thoughts}
Эмоции: {card.emotions}
Поведение: {card.behavior}
"""

        # Запрос к GPT-3.5 для получения текста медитации
        chat_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты медитативный гид."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600
        )
        meditation_text = chat_response.choices[0].message["content"].strip()
        logger.info(f"Сгенерирован текст медитации (первые 100 символов): {meditation_text[:100]}...")

        # Уникальное имя для mp3-файла
        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        # Генерация аудио через ElevenLabs
        try:
            # convert(...) возвращает генератор чанков байтов
            audio_generator = elevenlabs_client.text_to_speech.convert(
                voice_id="EXAVITQu4vr4xnSDxMaL",    # проверенный голос, поддерживающий русский
                model_id="eleven_multilingual_v2", # мультилингвальный, поддерживает русский
                text=meditation_text,
                output_format="mp3_44100_64"
            )
            audio_bytes = b"".join(audio_generator)  # объединяем чанки в единый bytes
        except Exception as e:
            logger.error(f"Ошибка при вызове ElevenLabs TTS:\n{e}")
            return JSONResponse(status_code=500, content={"error": "Ошибка при генерации аудио с ElevenLabs."})

        # Сохраняем байты в временный mp3-файл (чтобы можно было работать через pydub)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_file_path = temp_file.name

        try:
            # Загружаем mp3 через pydub
            voice_audio = AudioSegment.from_mp3(temp_file_path)
            logger.info(f"Длина голосового аудио: {len(voice_audio)/1000:.2f} сек")

            # Если есть фоновая музыка, накладываем
            if os.path.exists(BACKGROUND_MUSIC_PATH):
                try:
                    background = AudioSegment.from_mp3(BACKGROUND_MUSIC_PATH)
                    background = background[:len(voice_audio)] - 10  # уменьшаем громкость фоновой музыки на 10 dB
                    combined = voice_audio.overlay(background)
                    combined.export(filepath, format="mp3", bitrate="64k")
                    logger.info(f"Комбинированный трек сохранён: {filepath}")
                except Exception as e:
                    logger.error(f"Ошибка при наложении фоновой музыки:\n{e}")
                    # Если наложение не удалось, сохраняем только голос
                    voice_audio.export(filepath, format="mp3", bitrate="64k")
                    logger.info(f"Сохранён только голос: {filepath}")
            else:
                logger.warning("Фоновая музыка не найдена, сохраняем только голосовое аудио.")
                voice_audio.export(filepath, format="mp3", bitrate="64k")

            # Удаляем старые файлы (старше 1 часа)
            now_ts = time.time()
            for old_file in os.listdir(AUDIO_DIR):
                old_path = os.path.join(AUDIO_DIR, old_file)
                if os.path.isfile(old_path) and now_ts - os.path.getmtime(old_path) > 3600:
                    os.remove(old_path)
                    logger.info(f"Удалён старый файл: {old_path}")

            # Возвращаем готовый mp3-клиенту
            return FileResponse(path=filepath, media_type="audio/mpeg", filename="meditation.mp3")

        finally:
            # В любом случае удаляем временный файл из pydub
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logger.info(f"Удалён временный файл TTS: {temp_file_path}")

    except Exception as e:
        logger.error(f"Ошибка в процессе генерации медитации:\n{e}")
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

Сформируй JSON-массив упражнений в формате:
[
  {{
    "title": "Название упражнения",
    "duration": "Примерное время",
    "description": "Краткое описание",
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
Ответ должен быть ТОЛЬКО валидным JSON без лишнего текста.
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
        logger.info(f"Сырой ответ от GPT (первые 100 символов): {raw[:100]}...")

        if raw.startswith("```json"):
            raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            exercises = json.loads(raw)
            if not isinstance(exercises, list):
                logger.warning("Парсинг не вернул список — возвращаю пустой массив.")
                exercises = []
        except Exception as e:
            logger.error(f"Ошибка при парсинге JSON: {e}")
            exercises = []

        return {"result": exercises}

    except Exception as e:
        logger.error(f"Ошибка в процессе генерации упражнений:\n{e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# Запуск локально для тестирования
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
