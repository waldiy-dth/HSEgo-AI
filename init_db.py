import sqlite3
import os

def init_db():
    db_name = 'hse_mobility.db'
    
    # Если старая база еще осталась, удаляем её для чистоты эксперимента
    if os.path.exists(db_name):
        try:
            os.remove(db_name)
            print("Старый файл базы данных удален.")
        except Exception as e:
            print(f"Не удалось удалить старый файл (возможно, он открыт в другой программе): {e}")

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    print("Создаю таблицу universities...")
    # Создаем таблицу
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS universities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT NOT NULL,
            university_name TEXT NOT NULL,
            faculty TEXT NOT NULL,
            required_hours INTEGER,
            description TEXT,
            slots INTEGER DEFAULT 2
        )
    ''')
    
    # Настоящие, чистые тестовые данные (без лишнего текста и комментариев внутри строк)
    test_data = [
        ('Германия', 'Университет Хумбольдта', 'Экономика', 30, 'Известный экономический факультет в Берлине. Сильные курсы по макроэкономике и анализу данных. Требуется английский B2.', 3),
        ('Китай', 'Пекинский Университет', 'Бизнес и Менеджмент', 45, 'Программа международного бизнеса в Пекине. Курсы по глобальным рынкам и логистике на английском языке.', 2),
        ('Италия', 'Болонский Университет', 'Политология', 25, 'Старейший университет Европы. Мобильность для факультетов социальных наук и международных отношений.', 4),
        ('Казахстан', 'КИМЭП', 'Экономика', 30, 'Обучение полностью на английском языке в Алматы. Сильные курсы по финансам, аудиту и микроэкономике.', 5)
    ]
    
    print("Заполняю таблицу данными...")
    # Вставляем данные. Строго 6 знаков вопросов на 6 колонок
    cursor.executemany('''
        INSERT INTO universities (country, university_name, faculty, required_hours, description, slots)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', test_data)
    
    conn.commit()
    
    # Крошечная проверка: выведем в консоль то, что реально записалось
    print("\n--- Проверка записанных данных в БД: ---")
    cursor.execute("SELECT id, country, university_name, faculty FROM universities")
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID: {row[0]} | Страна: {row[1]} | Вуз: {row[2]} | Факультет: {row[3]}")
    print("----------------------------------------\n")
    
    conn.close()
    print("База данных успешно пересоздана!")

if __name__ == '__main__':
    init_db()