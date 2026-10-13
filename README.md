# 计算机二级 Python 教育 Agent

> 后端服务 · FastAPI + RAG + Kimi AI

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| Web 框架 | FastAPI + uvicorn | RESTful API 服务，端口 8000 |
| 向量数据库 | ChromaDB | 知识点向量化存储与检索 |
| 嵌入模型 | all-MiniLM-L6-v2 (ONNX) | 本地离线运行 |
| AI 大模型 | Kimi (moonshot-k3) | 智能问答，支持 RAG 增强 |
| 数据库 | SQLite | 题库、用户答题记录 |
| 依赖管理 | Python Embeddable | 内嵌 Python 3.12 + 227 个包 |

## 项目结构

```
├── backend/
│   ├── api/            # API 路由层
│   │   └── routes.py   # 6 个 RESTful 端点
│   ├── core/           # 核心配置
│   │   └── config.py
│   ├── database/       # 题库数据
│   │   ├── init_db.py
│   │   └── questions_data.py   # 157 道真题
│   ├── models/         # 数据模型
│   │   ├── database.py
│   │   └── schemas.py
│   ├── services/       # 业务逻辑
│   │   ├── rag_service.py       # RAG + Kimi AI
│   │   └── scoring_service.py   # 编程题自动评分
│   ├── utils/          # 工具模块
│   │   └── update_checker.py    # 题库自动更新
│   └── main.py         # FastAPI 应用入口
├── .env.example        # 环境变量模板
├── .gitignore
── README.md
```

## 快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 Kimi API Key：

```env
KIMI_API_KEY=sk-xxxxx
KIMI_MODEL=kimi-k3
HOST=127.0.0.1
PORT=8000
```

> 获取 API Key：[platform.moonshot.cn](https://platform.moonshot.cn/console/api-keys)

### 3. 初始化数据库

```bash
python backend/database/init_db.py
```

首次运行会自动下载 all-MiniLM-L6-v2 嵌入模型（~80MB），后续离线可用。

### 4. 启动服务

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/chapters` | 获取章节列表 |
| `GET` | `/api/questions/{id}` | 获取题目详情 |
| `GET` | `/api/stats` | 获取统计信息 |
| `GET` | `/api/progress` | 获取学习进度 |
| `POST` | `/api/answer` | 提交答案评分 |
| `POST` | `/api/chat` | AI 智能问答 |

### 示例

```bash
# 获取题目
curl http://127.0.0.1:8000/api/questions/1

# 提交答案
curl -X POST http://127.0.0.1:8000/api/answer \
  -H "Content-Type: application/json" \
  -d '{"question_id": 1, "answer": "B"}'

# AI 问答
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Python中如何定义函数？"}'
```

## 题库自动更新

内置 Gitee 题库版本检查，每次启动时自动比对远程版本，有新版本则静默更新。

需要在 `.env` 中配置 Gitee Token：

```env
GITEE_TOKEN=your-gitee-token-here
```

## 配置说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `KIMI_API_KEY` | Kimi API 密钥（必填） | - |
| `KIMI_MODEL` | Kimi 模型名称 | `kimi-k3` |
| `HOST` | 服务监听地址 | `127.0.0.1` |
| `PORT` | 服务端口 | `8000` |
| `GITEE_TOKEN` | Gitee 私有令牌（题库更新） | - |

## 开发环境

- Python 3.12
- FastAPI 0.115+
- ChromaDB 0.4+
- Kimi API (moonshot)

## License

MIT
