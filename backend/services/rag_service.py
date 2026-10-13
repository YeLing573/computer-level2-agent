import json
import httpx
from pathlib import Path
from backend.core.config import settings
from backend.models.schemas import ChatResponse


class RAGService:
    """RAG 知识库问答服务"""

    def __init__(self):
        self.collection = self._init_chroma()
        self._build_knowledge()

    def _init_chroma(self):
        """创建/加载 ChromaDB collection"""
        import chromadb
        client = chromadb.PersistentClient(path=str(settings.CHROMA_PATH))
        collection = client.get_or_create_collection(
            name="knowledge_base",
            metadata={"hnsw:space": "cosine"}
        )
        return collection

    def _build_knowledge(self):
        """从数据库题目中提取知识点构建向量库"""
        from backend.models.database import DatabaseManager
        db = DatabaseManager(settings.DATABASE_PATH)
        questions = db.get_all_questions()
        db.close()

        documents = []
        metadatas = []
        ids = []

        for q in questions:
            kp_raw = q.get("knowledge_points", "")
            if isinstance(kp_raw, str):
                try:
                    knowledge_points = json.loads(kp_raw) if kp_raw else []
                except json.JSONDecodeError:
                    knowledge_points = []
            else:
                knowledge_points = kp_raw if kp_raw else []

            if not knowledge_points:
                continue

            for kp in knowledge_points:
                doc_id = f"q{q['id']}_kp_{kp}"
                if doc_id in [i for i in ids]:
                    continue
                documents.append(kp)
                metadatas.append({
                    "question_id": q["id"],
                    "chapter": q.get("chapter", ""),
                    "type": q.get("type", ""),
                    "question": q.get("question", "")
                })
                ids.append(doc_id)

        if documents:
            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

    def query(self, question: str) -> str:
        """检索最相关的知识点"""
        results = self.collection.query(
            query_texts=[question],
            n_results=3
        )
        if not results["documents"] or not results["documents"][0]:
            return ""
        return "\n".join(results["documents"][0])

    def generate_answer(self, question: str, context: str) -> str:
        """调用 Kimi API 生成回答"""
        if not settings.KIMI_API_KEY:
            return context

        headers = {
            "Authorization": f"Bearer {settings.KIMI_API_KEY}",
            "Content-Type": "application/json"
        }
        messages = [
            {
                "role": "system",
                "content": "你是一个计算机二级Python考试辅导老师。请根据以下知识库内容回答学生的问题。如果知识库中没有相关信息，请如实告知。\n\n相关知识：\n" + context
            },
            {
                "role": "user",
                "content": question
            }
        ]
        payload = {
            "model": settings.KIMI_MODEL,
            "messages": messages
        }

        try:
            with httpx.Client(timeout=120) as client:
                response = client.post(
                    f"{settings.KIMI_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"AI 回答生成失败：{str(e)}\n\n以下是从知识库检索到的相关内容：\n{context}"

    def chat(self, question: str) -> ChatResponse:
        """完整 RAG 流程：检索 + 生成"""
        context = self.query(question)
        if not context:
            return ChatResponse(
                answer="抱歉，知识库中未找到相关内容，请尝试换个关键词。",
                sources=[]
            )

        answer = self.generate_answer(question, context)
        return ChatResponse(
            answer=answer,
            sources=[context] if context else []
        )
