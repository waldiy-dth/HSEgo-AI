from telebot import *
from time import *
from datetime import datetime
from zoneinfo import ZoneInfo
import threading
import requests



token = "8576109638:AAHzF1kDSod-C-sB8PIKLryfzipE5UOJmic"
LLM_URL = "http://127.0.0.1:8000/ask"



def start_bot():
    bot.polling(none_stop=True)



bot = TeleBot(token)
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 'hi, i am a HSE bot for student mobility \n'
                            '/ask - умные ответы от нейронки \n'
                            '/clear - стереть память \n')

@bot.message_handler(func=lambda message: True)
def time_reply(message):
    moscow_time = datetime.now(ZoneInfo("Europe/Moscow"))
    bot.reply_to(message,'я пока не могу ответить на ваше сообщение, время в мск: ' + moscow_time.strftime("%H:%M:%S") + '\n чтобы писала нейронка: /ask')


@bot.message_handler(commands=['ask'])
def ask_llm():
    question = message.text.strip()
    if not question:
        bot.reply_to(message, 'пиши /ask, чтобы отвечала нейронка')
        return
    chat_id = message.chat.id
    if chat_id not in histories:
        histories = {}
    histories.append({'role': 'user','content': question})
    bot.reply('думаю...')

    try:
        resp = requests.post(LLM_URL, json={"text": question, "chat_id": chat_id}, timeout=30)
        resp.raise_for_status()
        answer = resp.json()    
    except Exception as e:
        answer = f"ошибка... ({e})\nПопробуй через секунду или перезапусти Ollama"

    histories.append({"role": "assistant", "content": answer})

    if len(histories) > 20:
        histories= histories
    bot.reply(answer)

@bot.message_handler(commands=['clear'])
def clear_history(message):
    chat_id = message.chat.id
    if chat_id in histories:
        del histories    
        bot.reply_to(message,"Память стёрта...")
    else: 
        bot.reply_to(message,"память уже пустая")

print("Бот запущен локально...")
while True:
    try:
        bot_thread = threading.Thread(target=start_bot, daemon=True)
        bot_thread.start()
        input()
        print("Завершение работы...")
    except KeyboardInterrupt:
        print("\n Бот остановлен вручную")
        exit()
    except Exception as e:
        print("Ошибка, перезапускаюсь...", e)
        sleep(5)