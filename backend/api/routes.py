import json
from datetime import datetime, date
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.core.config import settings, get_data_path
from backend.models.database import DatabaseManager
from backend.models.schemas import (
    AnswerRequest, AnswerResponse, ChatRequest, ChatResponse, ScoreResult
)
from backend.services.scoring_service import AnswerScorer
from backend.services.rag_service import RAGService

router = APIRouter()

# 延迟初始化单例（避免模块导入时立即创建数据库连接）
_db: Optional[DatabaseManager] = None
_scorer: Optional[AnswerScorer] = None
_rag: Optional[RAGService] = None

# ==================== 进度追踪 ====================
_PROGRESS_FILE: Optional[Path] = None
_progress_cache: Optional[dict] = None


def _get_progress_file() -> Path:
    """获取进度文件路径"""
    global _PROGRESS_FILE
    if _PROGRESS_FILE is None:
        _PROGRESS_FILE = get_data_path() / "progress.json"
    return _PROGRESS_FILE


def _load_progress() -> list:
    """加载进度记录列表"""
    global _progress_cache
    pf = _get_progress_file()
    if _progress_cache is None:
        if pf.exists():
            try:
                _progress_cache = json.loads(pf.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                _progress_cache = []
        else:
            _progress_cache = []
    return _progress_cache


def _save_progress(records: list):
    """保存进度记录"""
    global _progress_cache
    _progress_cache = records
    pf = _get_progress_file()
    pf.parent.mkdir(parents=True, exist_ok=True)
    pf.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def record_answer(question_id: int, is_correct: bool, chapter: str, q_type: str):
    """记录一次答题"""
    records = _load_progress()
    records.append({
        "question_id": question_id,
        "is_correct": is_correct,
        "chapter": chapter,
        "type": q_type,
        "answered_at": datetime.now().isoformat(),
        "date": date.today().isoformat(),
    })
    _save_progress(records)


def compute_progress():
    """计算学习进度统计"""
    records = _load_progress()
    total = len(records)
    if total == 0:
        return {
            "total_attempted": 0,
            "total_correct": 0,
            "accuracy": 0,
            "streak_days": 0,
            "chapters": [],
            "unique_questions": 0,
        }

    correct = sum(1 for r in records if r.get("is_correct", False))
    unique_questions = len(set(r.get("question_id") for r in records))
    accuracy = correct / total * 100

    # 连续学习天数
    dates = sorted(set(r.get("date", "") for r in records if r.get("date")), reverse=True)
    streak = 0
    today = date.today()
    for i, d_str in enumerate(dates):
        try:
            d = date.fromisoformat(d_str)
        except ValueError:
            continue
        if i == 0 and (today - d).days > 1:
            break
        if i > 0:
            prev = date.fromisoformat(dates[i - 1])
            if (prev - d).days > 1:
                break
        streak += 1

    # 按章节统计
    chapter_map = {}
    for r in records:
        ch = r.get("chapter", "未知章节")
        if ch not in chapter_map:
            chapter_map[ch] = {"name": ch, "attempted": 0, "correct": 0}
        chapter_map[ch]["attempted"] += 1
        if r.get("is_correct", False):
            chapter_map[ch]["correct"] += 1

    # 获取每个章节的题目总数
    db = get_db()
    stats = db.get_stats()
    by_chapter = stats.get("by_chapter", {})
    chapters = []
    for ch_name, ch_data in chapter_map.items():
        ch_total = by_chapter.get(ch_name, 0)
        ch_acc = ch_data["correct"] / ch_data["attempted"] * 100 if ch_data["attempted"] > 0 else 0
        chapters.append({
            "name": ch_name,
            "total": ch_total,
            "attempted": ch_data["attempted"],
            "correct": ch_data["correct"],
            "accuracy": ch_acc,
        })

    return {
        "total_attempted": total,
        "total_correct": correct,
        "accuracy": accuracy,
        "streak_days": streak,
        "chapters": chapters,
        "unique_questions": unique_questions,
    }


def get_db() -> DatabaseManager:
    global _db
    if _db is None:
        _db = DatabaseManager(settings.DATABASE_PATH)
    return _db


def get_scorer() -> AnswerScorer:
    global _scorer
    if _scorer is None:
        _scorer = AnswerScorer()
    return _scorer


def get_rag() -> RAGService:
    global _rag
    if _rag is None:
        _rag = RAGService()
    return _rag


def _parse_json_field(value):
    """安全解析 JSON 字符串字段"""
    if not value:
        return None
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def _format_question(row: dict) -> dict:
    """格式化题目数据，解析 JSON 字段"""
    return {
        "id": row["id"],
        "type": row["type"],
        "chapter": row["chapter"],
        "question": row["question"],
        "options": _parse_json_field(row.get("options")),
        "answer": row["answer"],
        "analysis": row.get("analysis", ""),
        "score_steps": _parse_json_field(row.get("score_steps")),
        "knowledge_points": _parse_json_field(row.get("knowledge_points")),
        "difficulty": row.get("difficulty", "中等")
    }


@router.get("/api/questions")
def get_questions(
    chapter: Optional[str] = Query(None),
    type: Optional[str] = Query(None)
):
    """获取题目列表，支持按章节和题型筛选"""
    questions = get_db().get_all_questions(chapter=chapter, q_type=type)
    return [_format_question(q) for q in questions]


@router.get("/api/questions/{question_id}")
def get_question(question_id: int):
    """获取单道题目"""
    q = get_db().get_question_by_id(question_id)
    if not q:
        raise HTTPException(status_code=404, detail="题目不存在")
    return _format_question(q)


@router.get("/api/chapters")
def get_chapters():
    """获取章节列表"""
    return get_db().get_chapters()


@router.get("/api/stats")
def get_stats():
    """获取统计信息"""
    return get_db().get_stats()


@router.get("/api/progress")
def get_progress():
    """获取学习进度（基于本地答题记录）"""
    return compute_progress()


@router.post("/api/answer", response_model=AnswerResponse)
def submit_answer(req: AnswerRequest):
    """提交答案评分"""
    q = get_db().get_question_by_id(req.question_id)
    if not q:
        raise HTTPException(status_code=404, detail="题目不存在")

    score_steps = _parse_json_field(q.get("score_steps"))
    if not score_steps:
        raise HTTPException(status_code=400, detail="该题未配置评分步骤")

    result = get_scorer().score(req.answer, score_steps)

    # 判断是否正确：得分达到满分 80% 以上视为正确
    is_correct = result.percentage >= 80.0

    # 记录答题进度
    record_answer(
        question_id=req.question_id,
        is_correct=is_correct,
        chapter=q.get("chapter", "未知章节"),
        q_type=q.get("type", "unknown"),
    )

    return AnswerResponse(
        question_id=req.question_id,
        is_correct=is_correct,
        score=result,
        correct_answer=q["answer"],
        analysis=q.get("analysis", "")
    )


@router.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """AI 问答"""
    return get_rag().chat(req.question)
