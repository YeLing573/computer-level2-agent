"""
题库自动更新检查器
每次启动时运行，检查远程是否有新版题库，有则自动下载替换。

托管方式：Gitee 私有仓库 + 私人令牌
- 仓库地址: https://gitee.com/yeleing/db_file
- 版本信息: GitHub Gist 上的 version.json
- 下载方式: Gitee API (archive/download) + 私人令牌
"""
import os
import sys
import json
import ssl
import zipfile
import tempfile
import urllib.request
from pathlib import Path
from io import BytesIO

# 加载 .env（如果存在）
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass

# ==================== 配置 ====================
# 版本信息文件 URL
UPDATE_INDEX_URL = "https://gist.githubusercontent.com/YeLing573/938611095b28d6b7d0629b2ddcf0c6c0/raw/076f729dfd574f47e83996fa2c8723e2e07d0bad/version.json"

# Gitee 配置（从 .env 读取，避免硬编码）
GITEE_TOKEN = os.environ.get("GITEE_TOKEN", "")
GITEE_OWNER = "yeleing"
GITEE_REPO = "db_file"
# ==============================================

DATA_DIR = Path(__file__).parent.parent.parent / "data"
VERSION_FILE = DATA_DIR / "db_version.txt"
DB_FILE = DATA_DIR / "education_agent.db"
BACKUP_DIR = DATA_DIR / "backups"

# 数据库文件最小有效大小 (bytes)
MIN_DB_SIZE = 10240  # 10KB


def _ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch_json(url: str, headers: dict = None) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=15, context=_ctx()) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def fetch_bytes(url: str, headers: dict = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=120, context=_ctx()) as r:
        return r.read()


def get_current_version() -> str:
    try:
        return VERSION_FILE.read_text().strip()
    except (OSError, ValueError):
        return "0.0.0"


def save_version(v: str):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    VERSION_FILE.write_text(v)


def version_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return (0, 0, 0)


def get_gitee_headers() -> dict:
    if GITEE_TOKEN:
        return {"Authorization": f"token {GITEE_TOKEN}"}
    return {}


def download_from_gitee_release(dl_url: str) -> bytes:
    """
    从 Gitee Release 下载 zip 并提取 education_agent.db。
    支持两种 URL 格式:
    1. Gitee Release 下载链接: /releases/download/...
    2. Gitee API 下载链接: /api/v5/repos/.../releases/...
    """
    print("[Updater] Downloading from Gitee...")
    auth_headers = get_gitee_headers()

    # 下载 zip 文件
    zip_bytes = fetch_bytes(dl_url, auth_headers)

    # 验证是 ZIP 文件 (PK header: 0x50 0x4B)
    if len(zip_bytes) < 4 or zip_bytes[0:2] != b'PK':
        raise RuntimeError(f"Downloaded file is not a valid ZIP (first bytes: {zip_bytes[0:4].hex()})")

    print(f"[Updater] Downloaded ZIP: {len(zip_bytes)} bytes")

    # 从 ZIP 中提取 education_agent.db
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        # 查找 db 文件（可能在根目录或子目录中）
        db_entry = None
        for name in zf.namelist():
            if name.endswith("education_agent.db") and not name.endswith("/"):
                db_entry = name
                break

        if db_entry is None:
            # 如果没找到 db，列出所有文件帮助调试
            all_files = zf.namelist()
            raise RuntimeError(f"education_agent.db not found in ZIP. Contents: {all_files[:10]}")

        db_bytes = zf.read(db_entry)
        print(f"[Updater] Extracted {db_entry}: {len(db_bytes)} bytes")
        return db_bytes


def download_from_direct_url(dl_url: str) -> bytes:
    """直接下载 .db 文件"""
    auth_headers = get_gitee_headers()
    db_bytes = fetch_bytes(dl_url, auth_headers)

    if len(db_bytes) < MIN_DB_SIZE:
        raise RuntimeError(f"Downloaded file too small ({len(db_bytes)} bytes)")

    # 验证不是 HTML 页面
    if db_bytes[:5] in (b'<!DOC', b'<html', b'<HTML'):
        raise RuntimeError("Downloaded file is HTML, not a database")

    return db_bytes


def check_and_update():
    print("[Updater] Checking question bank version...")

    current = get_current_version()
    print(f"[Updater] Local version: {current}")

    # 获取远程版本信息
    try:
        info = fetch_json(UPDATE_INDEX_URL)
    except Exception as e:
        print(f"[Updater] Cannot reach update server: {e}")
        return

    remote_version = info.get("version", "0.0.0")
    print(f"[Updater] Remote version: {remote_version}")

    if version_tuple(remote_version) <= version_tuple(current):
        print("[Updater] Already up to date.")
        return

    dl_url = info.get("download_url", "")
    if not dl_url:
        print("[Updater] No download URL in version info.")
        return

    print(f"[Updater] New version available! Downloading update...")

    try:
        # 判断下载方式
        is_gitee = "gitee.com" in dl_url
        is_zip = dl_url.endswith(".zip") or "archive" in dl_url or "download" in dl_url

        if is_gitee and is_zip:
            # Gitee 下载 -> 需要解压 ZIP
            db_bytes = download_from_gitee_release(dl_url)
        elif is_gitee:
            # 直接下载 db 文件
            db_bytes = download_from_direct_url(dl_url)
        else:
            # 其他 URL，尝试直接下载
            db_bytes = fetch_bytes(dl_url)

        # 验证数据库大小
        if len(db_bytes) < MIN_DB_SIZE:
            print(f"[Updater] WARNING: Downloaded file too small ({len(db_bytes)} bytes)")
            return

        # 备份旧数据库
        if DB_FILE.exists():
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            backup = BACKUP_DIR / f"education_agent_v{current}.db"
            backup.write_bytes(DB_FILE.read_bytes())
            print(f"[Updater] Backed up v{current}")

        # 写入新数据库
        DB_FILE.write_bytes(db_bytes)
        save_version(remote_version)
        print(f"[Updater] Updated to v{remote_version} ({len(db_bytes) / 1024:.0f} KB)")

    except Exception as e:
        print(f"[Updater] Failed to update: {e}")

    print("[Updater] Done.")


if __name__ == "__main__":
    check_and_update()
