from telebot import *
from time import *
from datetime import datetime
import threading
import requests
import random

token = "8576109638:AAGK03NaFVpXHHLQH15zZX1aa6E5kyQtRpY"
API_URL = "http://127.0.0.1:8000"

bot = TeleBot(token)

brain_mode = {}      # chat_id -> True/False (включен ли режим общения с ИИ)
chat_sessions = {}   # chat_id -> ID сессии для ИИ
user_forms = {}      # Временный сбор анкеты

def start_bot():
    bot.infinity_polling(timeout=90, long_polling_timeout=20, skip_pending=True)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 
        "Привет! Я HSEgo AI, ваш универсальный помощник в студенческой мобильности. 🎓\n"
        "Чтобы подобрать вуз по анкете и обсудить варианты с ИИ, введи команду /ask")

@bot.message_handler(commands=['ask'])
def start_survey(message):
    chat_id = message.chat.id
    # Выключаем режим чата, пока заполняется анкета
    brain_mode[chat_id] = False
    
    # Каждая анкета — уникальная сессия для истории FastAPI
    session_id = "".join([str(random.randint(0, 9)) for _ in range(12)])
    chat_sessions[chat_id] = session_id
    user_forms[chat_id] = {}
    
    msg = bot.send_message(chat_id, "Отлично! Давай подберем программу мобильности. \n\nШаг 1: На каком направлении/факультете ты учишься? (например: Экономика, Политология)")
    bot.register_next_step_handler(msg, process_faculty_step)

def process_faculty_step(message):
    chat_id = message.chat.id
    user_forms[chat_id]['faculty'] = message.text
    msg = bot.send_message(chat_id, "Шаг 2: В какую страну хочешь поехать? (например: Германия, Китай)")
    bot.register_next_step_handler(msg, process_country_step)

def process_country_step(message):
    chat_id = message.chat.id
    user_forms[chat_id]['country'] = message.text
    msg = bot.send_message(chat_id, "Шаг 3: Сколько минимум учебных часов нужно перекрыть? (числом, например: 30)")
    bot.register_next_step_handler(msg, process_hours_step)

def process_hours_step(message):
    chat_id = message.chat.id
    try:
        user_forms[chat_id]['hours'] = int(message.text)
    except ValueError:
        msg = bot.reply_to(message, "Пожалуйста, введи количество часов цифрами:")
        bot.register_next_step_handler(msg, process_hours_step)
        return

    waiting_msg = bot.send_message(chat_id, "Формирую запрос к базе данных и ИИ...")
    session_id = chat_sessions[chat_id]
    form_data = user_forms[chat_id]

    try:
        resp = requests.post(
            f"{API_URL}/ask",
            json={
                "chat_id": session_id,
                "faculty": form_data['faculty'],
                "country": form_data['country'],
                "hours": form_data['hours']
            },
            timeout=180
        )
        resp.raise_for_status()
        answer = resp.json().get("answer", "Ошибка обработки.")
    except Exception as e:
        answer = f"Ошибка связи с сервером: {e}"

    bot.delete_message(chat_id, waiting_msg.message_id)
    bot.send_message(chat_id, answer)
    
    # Очищаем временную анкету
    user_forms.pop(chat_id, None)
    
    # ВАЖНО: Включаем режим свободного общения с ИИ по этой сессии!
    brain_mode[chat_id] = True
    bot.send_message(chat_id, "✨ Фильтр применён. Ты можешь задать мне любые вопросы по этим вузам прямо в чат! (Для нового поиска введи /ask)")

# Обработчик ВСЕХ остальных сообщений
@bot.message_handler(func=lambda message: True)
def handle_conversation(message):
    chat_id = message.chat.id
    
    # Если режим ИИ активен — отправляем текст на эндпоинт свободного общения /chat
    if brain_mode.get(chat_id, False):
        session_id = chat_sessions.get(chat_id)
        waiting_msg = bot.send_message(chat_id, "Думаю...")
        
        try:
            resp = requests.post(
                f"{API_URL}/chat",
                json={"chat_id": session_id, "text": message.text},
                timeout=180
            )
            resp.raise_for_status()
            answer = resp.json().get("answer", "Нет ответа от ИИ.")
        except Exception as e:
            answer = f"Ошибка диалога: {e}"
            
        bot.delete_message(chat_id, waiting_msg.message_id)
        bot.send_message(chat_id, answer)
    else:
        # Если анкета не заполнялась, напоминаем про команду /ask
        from datetime import timezone, timedelta
        moscow_tz = timezone(timedelta(hours=3))
        moscow_time = datetime.now(moscow_tz)
        bot.reply_to(message, f"Я готов подобрать программу мобильности. Время МСК: {moscow_time.strftime('%H:%M:%S')}\nЧтобы запустить подбор, нажми /ask")

if __name__ == "__main__":
    print("Бот успешно запущен и слушает команды...")
    try:
        start_bot()
    except KeyboardInterrupt:
        print("\nБот остановлен вручную.")
    except Exception as e:
        print(f"Критическая ошибка: {e}")