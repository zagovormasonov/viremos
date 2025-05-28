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
Ты психолог. Проанализируй когнитивные искажения в следующей CBT-карточке:

Ситуация: {situation}
Мысли: {thoughts}
Эмоции: {emotions}
Поведение: {behavior}

Выведи анализ, выделяя когнитивные искажения и рекомендации.
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

    return JSONResponse(content={"result": result})

# Для локального запуска
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
