import openai
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

openai.api_key = "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"  # или замени на свой ключ напрямую в виде строки

app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def get_form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})


@app.post("/", response_class=HTMLResponse)
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

    return templates.TemplateResponse("form.html", {
        "request": request,
        "result": result
    })

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))  # Render задаёт PORT в env
    uvicorn.run("main:app", host="0.0.0.0", port=port)
