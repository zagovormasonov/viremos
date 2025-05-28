from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# Разрешаем CORS для всех источников (можно ограничить при необходимости)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Укажи сюда адрес Flutter-приложения на проде
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
•  ‘title’: строка — название упражнения.
•  ‘duration’: строка — примерное время выполнения (например, ‘10-15 минут’).
•  ‘description’: строка — краткое описание упражнения, включая его цель и пользу для пользователя.
•  ‘instructions’: строка — общие инструкции для пользователя перед началом упражнения.
•  ‘steps’: массив объектов, каждый из которых описывает отдельный шаг упражнения. Каждый шаг должен содержать:
 •  ‘stepTitle’: строка — название шага.
 •  ‘stepDescription’: строка — подробное описание действий, которые нужно выполнить на этом шаге.
 •  ‘inputRequired’: булево значение (true/false) — указывает, требуется ли от пользователя ввести текст на этом шаге.
Требования:
•  Если шаг требует от пользователя записи мыслей, ответов или другой информации, установите ‘inputRequired’: true. Это позволит приложению автоматически добавить поле для ввода текста.
•  Все поля должны быть заполнены корректными данными.
•  Ответ должен содержать только JSON-структуру, без дополнительных комментариев или текста вне формата.
"""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты когнитивный психолог."},
                {"role": "user", "content": prompt}
            ]
        )

        result = response["choices"][0]["message"]["content"]
    except Exception as e:
        print("❌ Ошибка при запросе к OpenAI API:", e)
        result = "Ошибка при запросе к OpenAI API."

    return JSONResponse(content={"result": result}, media_type="application/json; charset=utf-8")

# Для локального запуска
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
