from telebot import *
from time import *
from datetime import datetime
from zoneinfo import ZoneInfo
import threading
import requests


histories = {}
brain_mode = {} # chat_id → True/False
chat_sessions = {}   # chat_id -> 12-значный ID сессии
token = "8576109638:AAGK03NaFVpXHHLQH15zZX1aa6E5kyQtRpY"
LLM_URL = "http://127.0.0.1:8000/ask"

bot = TeleBot(token)
def start_bot():
      bot.infinity_polling(timeout=90, long_polling_timeout=20, skip_pending=True)

flag = False



@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 
        "Я HSEgo бот. Помогу со студ. мобильностью.\n"
        "/ask — включить/выключить AI mode")

@bot.message_handler(commands=['ask'])
def toggle_brain(message):
    chat_id = message.chat.id
    is_on = not brain_mode.get(chat_id, False)
    brain_mode[chat_id] = is_on
    
    if is_on:
        # Генерируем случайное 12-значное число
        session_id = "".join([str(random.randint(0, 9)) for _ in range(12)])
        chat_sessions[chat_id] = session_id
        status = f"AI mode ВКЛЮЧЕН."
    else:
        chat_sessions.pop(chat_id, None) # Удаляем сессию при выключении
        status = "AI mode ВЫКЛЮЧЕН."
    
    bot.send_message(chat_id, status)


@bot.message_handler(func=lambda m: brain_mode.get(m.chat.id, False))
def brain_on(message):
    chat_id = message.chat.id
    if message.text.startswith('/'):
        return

    # Берем сгенерированный ID сессии
    session_id = chat_sessions.get(chat_id)
    waiting_msg = bot.send_message(chat_id, "Думаю...")

    try:
        resp = requests.post(
            LLM_URL,
            json={
                "text": message.text, 
                "chat_id": session_id  # Отправляем именно ID сессии вместо chat.id
            },
            timeout=180
        )
        resp.raise_for_status()
        
        try:
            data = resp.json()
            answer = data.get("answer", resp.text) if isinstance(data, dict) else data
        except:
            answer = resp.text

    except Exception as e:
        answer = f"Ошибка: {e}"

    bot.send_message(chat_id, answer)
    bot.delete_message(chat_id, waiting_msg.message_id)


@bot.message_handler(func=lambda message: True)
def time_reply(message):
    moscow_time = datetime.now(ZoneInfo("Europe/Moscow"))
    bot.reply_to(message,'я пока не могу ответить на ваше сообщение, время в мск: ' + moscow_time.strftime("%H:%M:%S") + '\n чтобы писала нейронка: /ask')


if __name__ == "__main__":
    print("Бот запущен локально...")
    while True:
        try:
            bot_thread = threading.Thread(target=start_bot, daemon=True)
            bot_thread.start()
            input()
        except KeyboardInterrupt:
            print("\n Бот остановлен вручную")
            exit()
        except Exception as e:
            print("Ошибка, перезапускаюсь...", e)
            sleep(5)