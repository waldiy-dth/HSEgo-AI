from fastapi import FastAPI
from pydantic import BaseModel
import ollama
import uvicorn
import sqlite3
import os

app = FastAPI(title="The Brain of HSEgo AI")

class SurveyForm(BaseModel):
    chat_id: str
    faculty: str
    country: str
    hours: int

# Класс для обычных текстовых вопросов (продолжение диалога)
class ChatMessage(BaseModel):
    chat_id: str
    text: str

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
client = ollama.Client(host=OLLAMA_HOST)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "hse_mobility.db")

# Хранилище истории для контекстного диалога
history = {}

def search_db_flexible(faculty: str, country: str, hours: int):
    conn = sqlite3.connect(DB_PATH)
    conn.create_function("LOWER_RU", 1, lambda s: s.lower() if s else s)
    cursor = conn.cursor()
    
    # Ищем программы, которые дают БОЛЬШЕ или РАВНО часов, чем нужно студенту
    query_exact = """
        SELECT university_name, country, faculty, required_hours, description, slots 
        FROM universities WHERE LOWER_RU(country) = ? AND LOWER_RU(faculty) LIKE ? AND required_hours >= ?
    """
    cursor.execute(query_exact, (country.strip().lower(), f"%{faculty.strip().lower()}%", hours))
    rows = cursor.fetchall()
    if rows:
        conn.close()
        return rows, "exact"
    
    # Альтернатива: Тот же факультет в других странах
    query_alt = """
        SELECT university_name, country, faculty, required_hours, description, slots 
        FROM universities WHERE LOWER_RU(faculty) LIKE ? AND required_hours >= ?
    """
    cursor.execute(query_alt, (f"%{faculty.strip().lower()}%", hours))
    rows_alt = cursor.fetchall()
    conn.close()
    
    if rows_alt:
        return rows_alt, "alternative"
    return [], "none"

@app.post("/ask")
async def ask_llm(form: SurveyForm):
    data, match_type = search_db_flexible(form.faculty, form.country, form.hours)
    
    if match_type == "none":
        return {"answer": "❌ К сожалению, подходящих программ не найдено. Попробуйте ввести другие параметры через команду /ask."}
    
    # Зачищаем старую историю диалога для этой сессии, так как начался новый подбор
    history[form.chat_id] = []
    
    # Формируем сухой факт-лист для ИИ
    db_text = ""
    if match_type == "exact":
        db_text = "Найденные точные варианты:\n"
    else:
        db_text = f"Точных совпадений в стране {form.country} нет. Вот альтернативные страны:\n"
        
    for r in data:
        db_text += f"- Вуз: {r[0]}, Страна: {r[1]}, Факультет: {r[2]}, Часов в наличии: {r[3]} (студенту надо: {form.hours}), Мест: {r[5]}. Описание: {r[4]}\n"

    # Предельно короткий системный промпт — супер-инструкция для 3B моделей
    system_instruction = (
        "Ты — ИИ-ассистент НИУ ВШЭ, по студенчекой мобильности. Твоя задача — красиво, вежливо и грамотно пересказать студенту предоставленные факты из БД.\n"
        "ПРАВИЛА:\n"
        "1. Пиши естественным языком. Оформи список красиво (используй эмодзи, жирный текст).\n"
        "2. Выведи ВСЕ вузы из текста ниже.\n"
        "3. Не придумывай другие вузы, которых нет в тексте.\n"
        "4. Отвечай тольуо в рамках студенческой мобильности НИУ ВШЭ и только на русском языке и эмодзи"
        f"Данные из БД:\n{db_text}"
    )
    
    # Сохраняем системный промпт в историю, чтобы ИИ помнил контекст вузов в следующих вопросах
    history[form.chat_id].append({"role": "system", "content": system_instruction})
    
    try:
        response = client.chat(
            model='qwen2.5:3b',
            options={"temperature": 0.3}, # Чуть-чуть добавляем для красоты слога
            messages=history[form.chat_id] + [{"role": "user", "content": "Покажи мне доступные варианты."}]
        )
        answer = response['message']['content']
        # Запоминаем ответ ИИ в историю
        history[form.chat_id].append({"role": "assistant", "content": answer})
    except Exception as e:
        answer = f"Ошибка ИИ: {e}"
        
    return {"answer": answer}

# НОВЫЙ ЭНДПОИНТ: Для продолжения переписки по выбранным вузам
@app.post("/chat")
async def chat_continue(msg: ChatMessage):
    if msg.chat_id not in history:
        return {"answer": "Сессия устарела или не найдена. Пожалуйста, запустите подбор заново через команду /ask."}
    
    # Добавляем свободный вопрос пользователя в историю
    history[msg.chat_id].append({"role": "user", "content": msg.text})
    
    try:
        response = client.chat(
            model='qwen2.5:3b',
            options={"temperature": 0.5},
            messages=history[msg.chat_id]
        )
        answer = response['message']['content']
        history[msg.chat_id].append({"role": "assistant", "content": answer})
    except Exception as e:
        answer = f"Ошибка ИИ в режиме диалога: {e}"
        
    # Ограничиваем длину истории, чтобы память не переполнялась
    if len(history[msg.chat_id]) > 15:
        history[msg.chat_id] = [history[msg.chat_id][0]] + history[msg.chat_id][-14:]
        
    return {"answer": answer}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)