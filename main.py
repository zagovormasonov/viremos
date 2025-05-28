from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import openai
import os


openai.api_key = "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"

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

На основе этой информации сгенерируйте терапевтические упражнения, чтобы помочь пользователю проработать свою ситуацию. Включите упражнения по крайней мере из трех из следующих подходов: КПТ (когнитивно-поведенческая терапия), АКТ (терапия принятия и ответственности), ДБТ (диалектическая поведенческая терапия), КФТ (терапия, сфокусированная на сострадании). Если ситуация сложная, вы можете добавить дополнительные упражнения.
Для каждого упражнения предоставьте:
•  Название
•  Примерное время выполнения (например, 10-15 минут)
•  Краткое описание, упоминающее терапевтический подход и как он может помочь пользователю
•  Четкие инструкции
•  Пронумерованные шаги, каждый с названием и описанием
•  Где это уместно, включите шаги, которые предлагают пользователю записать свои мысли, чувства или действия (укажите это фразой ‘Поле для ввода:’)
Убедитесь, что упражнения адаптированы к конкретным мыслям, эмоциям и поведению пользователя в контексте их ситуации. Упражнения должны быть поддерживающими, неосуждающими и легкими для понимания. Они также должны быть практическими и действенными, с четкими шагами, которые пользователь может выполнить
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
