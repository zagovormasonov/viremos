from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import openai
import os
import json
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# Разрешаем CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/")
async def submit_card(
    request: Request,
    situation: str = Form(...),
    thoughts: str = Form(...),
    emotions: str = Form(...),
    behavior: str = Form(...)
):
    try:
        prompt = f"""
Пользователь предоставил следующую информацию о своей ситуации:

Ситуация: {situation}
Мысли: {thoughts}
Эмоции: {emotions}
Поведение: {behavior}

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

        # Удалим обертки Markdown, если вдруг они остались
        if raw_result.startswith("```json"):
            raw_result = raw_result.removeprefix("```json").removesuffix("```").strip()

        # Преобразуем в Python-объект
        json_data = json.loads(raw_result)

        return JSONResponse(content={"result": json_data}, media_type="application/json; charset=utf-8")

    except Exception as e:
        print("❌ Ошибка:", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Для локального запуска
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
