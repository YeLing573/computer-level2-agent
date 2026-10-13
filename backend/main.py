"""计算机二级 Python 教育 Agent - FastAPI 后端入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Computer Level 2 Education Agent backend started")
    yield
    print("Service shutdown")


app = FastAPI(
    title="计算机二级 Python 教育 Agent",
    description="157道题库 · 步骤评分 · RAG问答 · AI辅导",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {"message": "计算机二级 Python 教育 Agent API", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
