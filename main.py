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
from elevenlabs.client import ElevenLabs

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")

if not openai_api_key or not elevenlabs_api_key:
    logger.error("Переменные OPENAI_API_KEY или ELEVENLABS_API_KEY не заданы в окружении")
    raise RuntimeError("Не установлены ключи API")

# Настройка OpenAI (версия >= 1.0.0)
openai_client = openai.OpenAI(api_key=openai_api_key)

# Инициализация ElevenLabs клиента
elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)

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

# Pydantic-модель входных данных
class CardInput(BaseModel):
    situation: str
    thoughts: str
    emotions: str
    behavior: str

# Директория для хранения mp3
AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Опциональный трек для фона
BACKGROUND_MUSIC_PATH = "audio/background_music.mp3"

@app.post("/generate-meditation")
async def generate_meditation(card: CardInput):
    try:
        logger.info(f"Получены данные для медитации: {card.dict()}")

        # 1) Сформировать prompt для GPT
        prompt = f"""
Сгенерируй короткую медитацию (до 400 слов) на русском языке, в женском спокойном стиле, 
с медленным, расслабляющим тоном. Начни с фразы "Устройся удобно..." 
и используй информацию:
Ситуация: {card.situation}
Мысли: {card.thoughts}
Эмоции: {card.emotions}
Поведение: {card.behavior}
"""

        # 2) Вызов OpenAI
        chat_response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты медитативный гид."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600
        )
        meditation_text = chat_response.choices[0].message.content.strip()
        logger.info(f"Сгенерирован текст: {meditation_text[:100]}...")

        # 3) Уникальное имя для итогового MP3
        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        # 4) Генерация аудио через ElevenLabs
        try:
            audio_generator = elevenlabs_client.text_to_speech.convert(
                voice_id="EXAVITQu4vr4xnSDxMaL",    # проверьте, что этот голос существует
                model_id="eleven_multilingual_v2",  # и этот ID модели актуален
                text=meditation_text,
                output_format="mp3_44100_64"
            )
            audio_bytes = b"".join(audio_generator)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Ошибка ElevenLabs TTS:\n{tb}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Ошибка при генерации аудио",
                    "details": str(e)
                }
            )

        # 5) Записать полученные байты в временный mp3-файл
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_file_path = temp_file.name

        try:
            voice_audio = AudioSegment.from_mp3(temp_file_path)
            logger.info(f"Длина голосового аудио: {len(voice_audio) / 1000:.2f} сек")

            # 6) Наложение фоновой музыки (если файл есть)
            if os.path.exists(BACKGROUND_MUSIC_PATH):
                try:
                    background = AudioSegment.from_mp3(BACKGROUND_MUSIC_PATH)
                    # Обрезать фон до длины голоса и сделать его тише на 10 dB
                    background = background[: len(voice_audio)] - 10
                    combined = voice_audio.overlay(background)
                    combined.export(filepath, format="mp3", bitrate="64k")
                    logger.info(f"Комбинированный трек сохранён: {filepath}")
                except Exception as e:
                    logger.error(f"Ошибка наложения фоновой музыки:\n{e}")
                    voice_audio.export(filepath, format="mp3", bitrate="64k")
                    logger.info(f"Сохранён только голос: {filepath}")
            else:
                logger.warning("Фоновая музыка не найдена, сохраняем только голос")
                voice_audio.export(filepath, format="mp3", bitrate="64k")

            # 7) Удалить старые mp3 (старше 1 часа)
            now_ts = time.time()
            for old_file in os.listdir(AUDIO_DIR):
                old_path = os.path.join(AUDIO_DIR, old_file)
                if os.path.isfile(old_path) and now_ts - os.path.getmtime(old_path) > 3600:
                    os.remove(old_path)
                    logger.info(f"Удалён старый файл: {old_path}")

            # 8) Отправить финальный mp3 клиенту
            return FileResponse(
                path=filepath,
                media_type="audio/mpeg",
                filename="meditation.mp3"
            )

        finally:
            # Всегда удалять временный mp3 с голосом
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logger.info(f"Удалён временный файл TTS: {temp_file_path}")

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Ошибка всего процесса:\n{tb}")
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

Сформируй JSON-массив упражнений формата:
[
  {{
    "title": "Название упражнения",
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

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты когнитивный психолог."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        raw = response.choices[0].message.content.strip()
        logger.info(f"Сырой ответ по упражнениям (первые 100): {raw[:100]}...")

        if raw.startswith("```json"):
            raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            exercises = json.loads(raw)
            if not isinstance(exercises, list):
                logger.warning("Результат парсинга не список, возвращаю []")
                exercises = []
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Ошибка парсинга JSON в упражнениях:\n{tb}")
            exercises = []

        return {"result": exercises}

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Ошибка генерации упражнений:\n{tb}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# Для локального тестирования
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
