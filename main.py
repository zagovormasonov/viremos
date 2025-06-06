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
from openai import OpenAI
from elevenlabs.client import ElevenLabs

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")

if not openai_api_key or not elevenlabs_api_key:
    logger.error("Переменные OPENAI_API_KEY или ELEVENLABS_API_KEY не установлены.")
    raise RuntimeError("Отсутствуют ключи API в окружении.")

# Инициализация клиентов
openai_client = OpenAI(api_key=openai_api_key)
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

# Директория для хранения mp3
AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Путь к фоновой музыке (опционально)
BACKGROUND_MUSIC_PATH = "audio/background_music.mp3"

@app.post("/generate-meditation")
async def generate_meditation(card: CardInput):
    try:
        logger.info(f"Получены данные для медитации: {card.dict()}")

        # 1. Составляем prompt для GPT
        prompt = f"""
Сгенерируй короткую медитацию (до 400 слов) на русском языке, в женском спокойном стиле, 
с медленным, расслабляющим тоном. Начни с фразы "Устройся удобно..." и создай медитацию 
длительностью около 3 минут. Используй следующую информацию:
Ситуация: {card.situation}
Мысли: {card.thoughts}
Эмоции: {card.emotions}
Поведение: {card.behavior}
"""

        # 2. Запрос к GPT-3.5 через новый клиент
        chat_response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты медитативный гид."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600
        )
        meditation_text = chat_response.choices[0].message.content.strip()
        logger.info(f"Сгенерирован текст (первые 100 chars): {meditation_text[:100]}...")

        # 3. Подготовка уникального имени mp3
        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        # 4. Генерация аудио через ElevenLabs
        try:
            audio_generator = elevenlabs_client.text_to_speech.convert(
                voice_id="EXAVITQu4vr4xnSDxMaL",    # Проверьте, что голос доступен
                model_id="eleven_multilingual_v2",  # Проверьте, что модель существует
                text=meditation_text,
                output_format="mp3_44100_64"
            )
            audio_bytes = b"".join(audio_generator)
        except Exception as e:
            # Логируем полную трассировку в консоль
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Ошибка ElevenLabs TTS:\n{tb}")

            # Возвращаем клиенту текст ошибки (для отладки)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Ошибка при генерации аудио",
                    "details": str(e)
                }
            )

        # 5. Сохраняем результат во временный mp3-файл
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_file_path = temp_file.name

        try:
            # 6. Загружаем голосовое аудио в pydub
            voice_audio = AudioSegment.from_mp3(temp_file_path)
            logger.info(f"Длина голосового аудио: {len(voice_audio) / 1000:.2f} сек")

            # 7. Если есть фоновая музыка — накладываем её
            if os.path.exists(BACKGROUND_MUSIC_PATH):
                try:
                    background = AudioSegment.from_mp3(BACKGROUND_MUSIC_PATH)
                    # Обрезаем фон до длины голоса и убавляем громкость на 10 dB
                    background = background[: len(voice_audio)] - 10
                    combined = voice_audio.overlay(background)
                    combined.export(filepath, format="mp3", bitrate="64k")
                    logger.info(f"Комбинированный трек сохранён: {filepath}")
                except Exception as e:
                    logger.error(f"Ошибка наложения фоновой музыки: {e}")
                    # Если не удалось наложить, сохраняем только голос
                    voice_audio.export(filepath, format="mp3", bitrate="64k")
                    logger.info(f"Сохранён только голос: {filepath}")
            else:
                logger.warning("Фоновая музыка не найдена, сохраняем только голосовое аудио.")
                voice_audio.export(filepath, format="mp3", bitrate="64k")

            # 8. Удаляем старые файлы (старше 1 часа)
            now_ts = time.time()
            for old_file in os.listdir(AUDIO_DIR):
                old_path = os.path.join(AUDIO_DIR, old_file)
                if os.path.isfile(old_path) and now_ts - os.path.getmtime(old_path) > 3600:
                    os.remove(old_path)
                    logger.info(f"Удалён старый файл: {old_path}")

            # 9. Возвращаем готовый mp3-файл клиенту
            return FileResponse(
                path=filepath,
                media_type="audio/mpeg",
                filename="meditation.mp3"
            )

        finally:
            # Всегда удаляем временный файл с голосом
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logger.info(f"Удалён временный файл TTS: {temp_file_path}")

    except Exception as e:
        # Ловим любую неожиданную ошибку всего процесса
        logger.error(f"Ошибка при генерации медитации:\n{e}")
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
Ответ должен быть ТОЛЬКО валидным JSON без лишнего текста.
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
                logger.warning("Результат не список, возвращаю пустой массив.")
                exercises = []
        except Exception as e:
            logger.error(f"Ошибка парсинга JSON:\n{e}")
            exercises = []

        return {"result": exercises}

    except Exception as e:
        logger.error(f"Ошибка при генерации упражнений:\n{e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# Для локального тестирования
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000, 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
