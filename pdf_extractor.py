import os
from pypdf import PdfReader

FACTSHEETS_DIR = "factsheets"
OUTPUT_FILE = "raw_data.txt"

def extract_text_from_pdfs():
    if not os.path.exists(FACTSHEETS_DIR):
        os.makedirs(FACTSHEETS_DIR)
        print(f"⚠️ Создана папка '{FACTSHEETS_DIR}'. Закинь туда свои 5 PDF-файлов и запусти скрипт снова.")
        return

    pdf_files = [f for f in os.listdir(FACTSHEETS_DIR) if f.endswith('.pdf')]
    
    if not pdf_files:
        print(f"❌ В папке '{FACTSHEETS_DIR}' не найдено PDF-файлов.")
        return

    print(f"📂 Найдено {len(pdf_files)} PDF-файлов. Начинаю извлечение текста...")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        for i, file_name in enumerate(pdf_files, 1):
            file_path = os.path.join(FACTSHEETS_DIR, file_name)
            print(f"[{i}/{len(pdf_files)}] Читаю {file_name}...")
            
            try:
                reader = PdfReader(file_path)
                full_text = []
                
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        full_text.append(text)
                
                # Записываем текст одного вуза как единый блок, 
                # чтобы ИИ понимал, что это данные одного университета
                out_f.write(f"=== НАЧАЛО ДОКУМЕНТА: {file_name} ===\n")
                out_f.write("\n".join(full_text))
                out_f.write(f"\n=== КОНЕЦ ДОКУМЕНТА: {file_name} ===\n\n")
                
            except Exception as e:
                print(f"❌ Ошибка при чтении файла {file_name}: {e}")

    print(f"🏁 Готово! Сырой текст из всех PDF собран в файл '{OUTPUT_FILE}'")

if __name__ == "__main__":
    extract_text_from_pdfs()