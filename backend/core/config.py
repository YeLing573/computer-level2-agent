from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()


def get_base_path():
    """获取项目根目录"""
    return Path(__file__).resolve().parent.parent.parent


def get_data_path():
    """获取数据目录（支持打包模式）"""
    env_path = os.environ.get("AGENT_DATA_PATH")
    if env_path:
        return Path(env_path)
    return get_base_path() / "data"


class Settings:
    DATABASE_PATH = get_data_path() / "education_agent.db"
    CHROMA_PATH = get_data_path() / "chroma_db"
    KIMI_API_KEY = os.environ.get("KIMI_API_KEY", "")
    KIMI_MODEL = os.environ.get("KIMI_MODEL", "kimi-k3")
    KIMI_BASE_URL = "https://api.moonshot.cn/v1"


settings = Settings()
