# config.example.py
import os
from dotenv import load_dotenv

load_dotenv()

# ================= Langfuse =================
PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

# ================= 靶机 Ollama =================
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
TARGET_MODEL_NAME = os.getenv("TARGET_MODEL_NAME", "qwen2.5:3b")

# ================= 裁判 DeepSeek =================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
JUDGE_MODEL_NAME = os.getenv("JUDGE_MODEL_NAME", "deepseek-chat")

# ================= MySQL 数据库 =================
# ⚠️ 注意：如果你用 docker-compose 启动，DB_HOST 请填 "eval-db"
# 如果你在宿主机本地测试，DB_HOST 请填 "127.0.0.1"
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_USER = os.getenv("DB_USER", "your_mysql_user")
DB_PASS = os.getenv("DB_PASS", "your_mysql_password")
DB_NAME = os.getenv("DB_NAME", "ai_evaluator")
