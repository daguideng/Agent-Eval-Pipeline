# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# 从 .env 文件中读取，不要写死！
PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
TARGET_MODEL_NAME = os.getenv("TARGET_MODEL_NAME", "qwen2.5:3b")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
JUDGE_MODEL_NAME = os.getenv("JUDGE_MODEL_NAME", "deepseek-chat")
