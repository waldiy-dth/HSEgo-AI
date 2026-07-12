import sqlite3
import json
import os
import requests
import re

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL_NAME = "qwen2.5:14b"

NEW_DB_PATH = "hse_test_parsed.db"
SOURCE_FILE = "raw_data.txt"

def init_new_db():
    conn = sqlite3.connect(NEW_DB_PATH)
    cursor = conn.cursor()
    # Добавили поле housing_price
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS universities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT NOT NULL,
            university_name TEXT NOT NULL,
            faculty TEXT NOT NULL,
            required_hours INTEGER,
            description TEXT,
            slots INTEGER DEFAULT 2,
            housing_price TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print(f"✨ База данных {NEW_DB_PATH} готова (с полем housing_price).")

def extract_relevant_sections(raw_text):
    """
    Вырезает из огромного текста Factsheet только те абзацы, 
    которые скорее всего содержат направления обучения и цены.
    """
    lines = raw_text.split('\n')
    relevant_lines = []
    
    # Ключевые слова для поиска направлений и цен
    keywords = [
        'faculty', 'department', 'program', 'course', 'major', 'study', 
        'housing', 'accommodation', 'living', 'cost', 'expense', 'price',
        'exchange', 'business', 'economics', 'management', 'politics'
    ]
    
    for i, line in enumerate(lines):
        # Если строка содержит ключевое слово, берем её и соседние строки для контекста
        if any(kw in line.lower() for kw in keywords):
            # Берем предыдущую, текущую и следующую строки, чтобы не терять смысл
            start = max(0, i - 1)
            end = min(len(lines), i + 2)
            relevant_lines.extend(lines[start:end])
            
    # Убираем дубликаты строк и склеиваем обратно
    seen = set()
    clean_lines = []
    for line in relevant_lines:
        if line.strip() not in seen:
            seen.add(line.strip())
            clean_lines.append(line)
            
    return "\n".join(clean_lines)[:6000] # Ограничиваем размер для 3B модели

def ask_ollama_to_parse(raw_text):
    parser_prompt = (
        "Ты — профессиональный робот-переводчик и экстрактор данных. Твоя задача — извлечь информацию о программе мобильности из текста Factsheet и вернуть СТРОГО JSON.\n"
        "КРИТИЧЕСКОЕ ТРЕБОВАНИЕ: Весь текст внутри JSON-ответа должен быть СТРОГО НА РУССКОМ ЯЗЫКЕ. Использование английских слов, названий факультетов или терминов ЗАПРЕЩЕНО. Переводи всё смыслом или транслитерацией, если это имя собственное.\n\n"
        "СТРУКТУРА JSON, КОТОРУЮ ТЫ ОБЯЗАН ВЕРНУТЬ:\n"
        "{\n"
        '  "country": "Название страны строго на русском (например: Германия, Турция, Южная Корея)",\n'
        '  "university_name": "Полное название университета, переведенное на русский язык (например: Коч Университет, Сеульский Национальный Университет)",\n'
        '  "faculty": "Перечисли через запятую конкретные доступные направления обучения СТРОГО НА РУССКОМ (например: Экономика, Бизнес-администрирование, Международные отношения, Компьютерные науки). Переведи каждое англоязычное направление из текста на русский. Не оставляй английских слов!",\n'
        '  "required_hours": целое_число_минимальных_часов_или_кредитов_если_нет_ставишь_30,\n'
        '  "housing_price": "Вилка цен за проживание в месяц с указанием валюты СТРОГО НА РУССКОМ. Например: \'$500-$700\', \'400-600 евро\', \'Не указано\'",\n'
        '  "description": "Описание требований к языку, дедлайнов и особенностей СТРОГО на русском языке в одно предложение",\n'
        '  "slots": целое_число_мест_если_нет_ставишь_2\n'
        "}\n\n"
        "ДОПОЛНИТЕЛЬНЫЕ ПРАВИЛА ЧИСТКИ:\n"
        "1. Запрещено использовать слова 'различные', 'много', 'и так далее' в поле faculty. Перечисляй только конкретные переведенные названия.\n"
        "2. В ответе должен быть ТОЛЬКО чистый JSON. Любые пояснения вне JSON запрещены.\n"
        "3. Если официальное название вуза сложно перевести, напиши его русскими буквами (например, 'Университет Боккони')."
    )

    payload = {
        "model": MODEL_NAME,
        "options": {
            "temperature": 0.0,
            "num_predict": 1500  # Даем еще больше места для подробного перевода
        },
        "stream": False,
        "messages": [
            {"role": "system", "content": parser_prompt},
            {"role": "user", "content": f"Текст Factsheet для анализа и полного перевода на русский:\n{raw_text[:8000]}"}
        ]
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=None)
        response.raise_for_status()
        result_text = response.json()['message']['content']
        clean_json = result_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        print(f"❌ Ошибка ИИ: {e}")
        return None

def insert_to_db(data):
    if not data: return
    conn = sqlite3.connect(NEW_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO universities (country, university_name, faculty, required_hours, description, slots, housing_price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('country'),
            data.get('university_name'),
            data.get('faculty'),
            int(data.get('required_hours', 30)),
            data.get('description'),
            int(data.get('slots', 2)),
            data.get('housing_price', 'Не указано')
        ))
        conn.commit()
        print(f"✅ Добавлено: {data.get('university_name')} | Проживание: {data.get('housing_price')}")
    except Exception as e:
        print(f"❌ Ошибка SQL: {e}")
    finally:
        conn.close()

def main():
    if not os.path.exists(SOURCE_FILE):
        print(f"❌ Файл {SOURCE_FILE} не найден. Сначала запусти pdf_extractor.py!")
        return

    init_new_db()

    # Читаем весь файл и делим его по блокам документов
    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Ищем блоки между === НАЧАЛО... === и === КОНЕЦ... ===
    blocks = re.findall(r"=== НАЧАЛО ДОКУМЕНТА: (.*?) ===\n(.*?)\n=== КОНЕЦ ДОКУМЕНТА:", content, re.DOTALL)

    if not blocks:
        print("❌ В raw_data.txt не найдено валидных блоков документов.")
        return

    print(f"📂 Найдено {len(blocks)} вузов для обработки в файле.\n")

    for i, (file_name, block_text) in enumerate(blocks, 1):
        print(f"[{i}/{len(blocks)}] ИИ анализирует Factsheet: {file_name}...")
        structured_data = ask_ollama_to_parse(block_text)
        if structured_data:
            insert_to_db(structured_data)
        else:
            print(f"❌ Ошибка парсинга для {file_name}")

    print(f"\n🏁 Парсинг завершен! Проверяй базу '{NEW_DB_PATH}'")

if __name__ == "__main__":
    main()