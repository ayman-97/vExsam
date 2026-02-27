import sqlite3
import csv
import os

DB_NAME = "exam_simulator.db"

def init_db():
    """تهيئة قاعدة البيانات وإنشاء الجدول بالهيكلية الجديدة إذا لم يكن موجوداً."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                section TEXT DEFAULT 'عام',
                passage_text TEXT DEFAULT '',
                question_text TEXT,
                option_a TEXT,
                option_b TEXT,
                option_c TEXT,
                option_d TEXT,
                correct_option TEXT
            )
        ''')
        conn.commit()

def import_real_questions_from_csv(csv_file_path):
    if not os.path.exists(csv_file_path):
        print(f"خطأ: الملف {csv_file_path} غير موجود. تأكد من مسار الملف.")
        return

    # إنشاء الجدول أولاً لتجنب خطأ OperationalError
    init_db()

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            inserted_count = 0
            
            for row_num, row in enumerate(reader, start=2):
                if not row.get('subject') or not row.get('question_text') or not row.get('correct_option'):
                    print(f"تحذير: تم تخطي الصف رقم {row_num} بسبب نقص في البيانات الأساسية.")
                    continue
                    
                cursor.execute('''
                    INSERT INTO Questions (subject, section, passage_text, question_text, option_a, option_b, option_c, option_d, correct_option)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['subject'].strip(),
                    row.get('section', 'قسم عام').strip(),
                    row.get('passage_text', '').strip(),
                    row['question_text'].strip(), 
                    row['option_a'].strip(), 
                    row['option_b'].strip(), 
                    row['option_c'].strip(), 
                    row['option_d'].strip(), 
                    row['correct_option'].strip()
                ))
                inserted_count += 1
        
        conn.commit()
        print(f"تم إدخال {inserted_count} سؤال إلى قاعدة البيانات بنجاح.")

if __name__ == "__main__":
    import_real_questions_from_csv("real_questions.csv")