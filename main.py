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
from elevenlabs import save

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

# Создаём директорию для аудио, если её нет
AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Путь к фоновой музыке
BACKGROUND_MUSIC_PATH = "audio/background_music.mp3"

@app.post("/generate-meditation")
async def generate_meditation(card: CardInput):
    try:
        logger.info(f"Received request with input: {card.dict()}")

        # Генерация текста медитации
        prompt = f"""
Сгенерируй короткую медитацию (до 400 слов) с легкой музыкой на заднем фоне, на русском языке в женском спокойном стиле с медленной, успокаивающей речью, длительностью около 3 минут. 
Начни с фразы "Устройся удобно..." и используй расслабляющий, поддерживающий тон.
Учти следующую информацию о ситуации пользователя:
Ситуация: {card.situation}
Мысли: {card.thoughts}
Эмоции: {card.emotions}
Поведение: {card.behavior}
"""

        chat_response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты медитативный гид."},
                {"role": "user", "content": prompt}
            ]
        )

        meditation_text = chat_response.choices[0].message.content.strip()
        logger.info(f"Generated meditation text: {meditation_text[:100]}...")

        # Уникальное имя файла
        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        # Генерация аудио через ElevenLabs
        try:
            audio = elevenlabs_client.text_to_speech.convert(
                voice_id="EXAVITQu4vr4xnSDxMaL",  # Замените при необходимости
                model_id="eleven_multilingual_v2",
                text=meditation_text,
                output_format="mp3_44100_64"
            )
        except Exception as e:
            logger.error(f"Ошибка при генерации речи через ElevenLabs: {e}")
            return JSONResponse(status_code=500, content={"error": "Ошибка при генерации аудио"})

        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_tts_file:
            temp_tts_file.write(audio)
            temp_tts_file_path = temp_tts_file.name

        try:
            # Загрузка голоса
            voice_audio = AudioSegment.from_mp3(temp_tts_file_path)
            logger.info(f"Voice audio loaded, duration: {len(voice_audio)/1000:.2f} sec")

            # Проверка фоновой музыки
            if os.path.exists(BACKGROUND_MUSIC_PATH):
                try:
                    background_music = AudioSegment.from_mp3(BACKGROUND_MUSIC_PATH)
                    logger.info(f"Background music loaded, duration: {len(background_music)/1000:.2f} sec")
                    background_music = background_music[:len(voice_audio)]
                    background_music = background_music - 10
                    combined_audio = voice_audio.overlay(background_music)
                    combined_audio.export(filepath, format="mp3", bitrate="64k")
                    logger.info(f"Combined audio saved to {filepath}")
                except Exception as e:
                    logger.error(f"Ошибка при наложении музыки: {e}")
                    voice_audio.export(filepath, format="mp3", bitrate="64k")
            else:
                logger.warning("Фоновая музыка не найдена, используется только голос")
                voice_audio.export(filepath, format="mp3", bitrate="64k")

            # Удаляем старые файлы
            for old_file in os.listdir(AUDIO_DIR):
                old_file_path = os.path.join(AUDIO_DIR, old_file)
                if os.path.isfile(old_file_path) and os.path.getmtime(old_file_path) < time.time() - 3600:
                    os.remove(old_file_path)
                    logger.info(f"Удален старый файл: {old_file_path}")

            return FileResponse(
                path=filepath,
                media_type="audio/mpeg",
                filename="meditation.mp3"
            )

        finally:
            if os.path.exists(temp_tts_file_path):
                os.remove(temp_tts_file_path)
                logger.info(f"Удален временный файл TTS: {temp_tts_file_path}")

    except Exception as e:
        logger.error(f"Ошибка при генерации медитации: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/", response_class=JSONResponse)
async def generate_exercises(card: CardInput):
    try:
        logger.info(f"Received exercise request with input: {card.dict()}")

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
    •  'inputRequired': boolean — нужно ли ввести текст.
Ответ должен быть ТОЛЬКО валидным JSON без лишнего текста. Если JSON невалидный, верни пустой массив [].
"""

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты когнитивный психолог."},
                {"role": "user", "content": prompt}
            ]
        )

        result = response.choices[0].message.content.strip()
        logger.info(f"Raw response: {result[:100]}...")

        if result.startswith("```json"):
            result = result.removeprefix("```json").removesuffix("```").strip()

        try:
            exercises = json.loads(result)
            if not isinstance(exercises, list):
                logger.warning("Ответ не является списком. Возвращаю пустой массив.")
                exercises = []
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON: {e}")
            exercises = []

        return {"result": exercises}

    except Exception as e:
        logger.error(f"Ошибка при генерации упражнений: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Запуск локально
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
