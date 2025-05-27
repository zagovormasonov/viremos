import openai

openai.api_key = "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"

response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": "Привет!, напиши от лица Ивана Ардашева приветственное письмо, кратко"}
    ]
)

print(response['choices'][0]['message']['content'])