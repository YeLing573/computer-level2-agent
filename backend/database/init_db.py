"""数据库初始化脚本 - 创建表并导入题库数据"""
import sqlite3
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.database.questions_data import QUESTIONS
from backend.core.config import settings


def init_db():
    """初始化数据库"""
    db_path = settings.DATABASE_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 创建questions表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            chapter TEXT NOT NULL,
            question TEXT NOT NULL,
            options TEXT,
            answer TEXT NOT NULL,
            analysis TEXT NOT NULL,
            score_steps TEXT,
            knowledge_points TEXT,
            difficulty TEXT DEFAULT 'medium'
        )
    ''')

    # 检查是否已有数据
    cursor.execute("SELECT COUNT(*) FROM questions")
    count = cursor.fetchone()[0]

    if count == 0:
        for q in QUESTIONS:
            cursor.execute('''
                INSERT INTO questions (id, type, chapter, question, options, answer, analysis, score_steps, knowledge_points, difficulty)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                q['id'], q['type'], q['chapter'], q['question'],
                json.dumps(q.get('options'), ensure_ascii=False) if q.get('options') else None,
                q['answer'], q['analysis'],
                json.dumps(q.get('score_steps'), ensure_ascii=False) if q.get('score_steps') else None,
                json.dumps(q.get('knowledge_points'), ensure_ascii=False) if q.get('knowledge_points') else None,
                q.get('difficulty', 'medium')
            ))
        conn.commit()
        print(f"✅ 成功导入 {len(QUESTIONS)} 道题目")
    else:
        print(f"⚠️ 数据库已有 {count} 道题目，跳过导入")

    conn.close()


if __name__ == "__main__":
    init_db()
