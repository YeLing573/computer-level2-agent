import sqlite3
from pathlib import Path


class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = str(db_path)
        self.db_path_obj = db_path
        self.db_path_obj.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self):
        """创建 questions 表"""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                chapter TEXT NOT NULL,
                question TEXT NOT NULL,
                options TEXT,
                answer TEXT NOT NULL,
                analysis TEXT,
                score_steps TEXT,
                knowledge_points TEXT,
                difficulty TEXT DEFAULT 'medium'
            )
        """)
        self.conn.commit()

    def get_all_questions(self, chapter: str = None, q_type: str = None) -> list:
        """获取题目列表，支持按章节和题型筛选"""
        query = "SELECT * FROM questions"
        conditions = []
        params = []
        if chapter:
            conditions.append("chapter = ?")
            params.append(chapter)
        if q_type:
            conditions.append("type = ?")
            params.append(q_type)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_question_by_id(self, q_id: int) -> dict | None:
        """根据ID获取单道题目"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM questions WHERE id = ?", (q_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_chapters(self) -> list:
        """获取所有章节列表"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT chapter FROM questions ORDER BY chapter")
        return [row["chapter"] for row in cursor.fetchall()]

    def get_stats(self) -> dict:
        """获取统计信息"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM questions")
        total = cursor.fetchone()["total"]
        cursor.execute("SELECT type, COUNT(*) as count FROM questions GROUP BY type")
        type_stats = {row["type"]: row["count"] for row in cursor.fetchall()}
        cursor.execute("SELECT chapter, COUNT(*) as count FROM questions GROUP BY chapter")
        chapter_stats = {row["chapter"]: row["count"] for row in cursor.fetchall()}
        return {
            "total": total,
            "by_type": type_stats,
            "by_chapter": chapter_stats
        }

    def close(self):
        """关闭数据库连接"""
        self.conn.close()
