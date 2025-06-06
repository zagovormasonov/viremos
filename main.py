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

# Инициализация клиентов
openai_client = openai.OpenAI(api_key=openai_api_key)
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

# Модель входных данных
class CardInput(BaseModel):
    situation: str
    thoughts: str
    emotions: str
    behavior: str

# Создаём директорию для аудио
AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Путь к фоновой музыке
BACKGROUND_MUSIC_PATH = "audio/background_music.mp3"

@app.post("/generate-meditation")
async def generate_meditation(card: CardInput):
    try:
        logger.info(f"Получены данные: {card.dict()}")

        # Генерация текста медитации
        prompt = f"""
Сгенерируй короткую медитацию (до 400 слов) на русском языке, в женском спокойном стиле, с медленным, расслабляющим тоном. Начни с фразы "Устройся удобно..." и создай медитацию длительностью около 3 минут. Используй следующую информацию:
Ситуация: {card.situation}
Мысли: {card.thoughts}
Эмоции: {card.emotions}
Поведение: {card.behavior}
"""

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты медитативный гид."},
                {"role": "user", "content": prompt}
            ]
        )
        meditation_text = response.choices[0].message.content.strip()
        logger.info(f"Сгенерирован текст: {meditation_text[:100]}...")

        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        # Генерация аудио
        try:
            audio = elevenlabs_client.text_to_speech.convert(
                voice_id="EXAVITQu4vr4xnSDxMaL",
                model_id="eleven_multilingual_v2",
                text=meditation_text,
                output_format="mp3_44100_64"
            )
        except Exception as e:
            logger.error(f"Ошибка TTS ElevenLabs: {e}")
            return JSONResponse(status_code=500, content={"error": "Ошибка при генерации аудио"})

        # Временный файл для голоса
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(audio)
            temp_file_path = temp_file.name

        try:
            voice_audio = AudioSegment.from_mp3(temp_file_path)
            logger.info(f"Длина аудио: {len(voice_audio) / 1000:.2f} сек")

            if os.path.exists(BACKGROUND_MUSIC_PATH):
                try:
                    background = AudioSegment.from_mp3(BACKGROUND_MUSIC_PATH)
                    background = background[:len(voice_audio)] - 10  # Тише на 10 dB
                    combined = voice_audio.overlay(background)
                    combined.export(filepath, format="mp3", bitrate="64k")
                except Exception as e:
                    logger.error(f"Ошибка наложения музыки: {e}")
                    voice_audio.export(filepath, format="mp3", bitrate="64k")
            else:
                logger.warning("Фоновая музыка не найдена")
                voice_audio.export(filepath, format="mp3", bitrate="64k")

            # Удаление старых файлов
            now = time.time()
            for f in os.listdir(AUDIO_DIR):
                f_path = os.path.join(AUDIO_DIR, f)
                if os.path.isfile(f_path) and now - os.path.getmtime(f_path) > 3600:
                    os.remove(f_path)
                    logger.info(f"Удалён старый файл: {f_path}")

            return FileResponse(filepath, media_type="audio/mpeg", filename="meditation.mp3")

        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logger.info(f"Удалён временный файл: {temp_file_path}")

    except Exception as e:
        logger.error(f"Ошибка генерации медитации: {e}")
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

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты когнитивный психолог."},
                {"role": "user", "content": prompt}
            ]
        )

        result = response.choices[0].message.content.strip()
        logger.info(f"Ответ от GPT: {result[:100]}...")

        if result.startswith("```json"):
            result = result.replace("```json", "").replace("```", "").strip()

        try:
            exercises = json.loads(result)
            if not isinstance(exercises, list):
                logger.warning("Результат не список, возвращаю []")
                exercises = []
        except Exception as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            exercises = []

        return {"result": exercises}

    except Exception as e:
        logger.error(f"Ошибка генерации упражнений: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# Запуск (для локального тестирования)
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
