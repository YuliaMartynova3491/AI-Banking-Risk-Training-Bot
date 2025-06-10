"""
Настройки приложения
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Корневая директория проекта
BASE_DIR = Path(__file__).parent.parent

# ЯВНО загружаем ТОЛЬКО .env файл, игнорируя .env.example
env_file = BASE_DIR / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)
    print(f"✅ Загружен файл настроек: {env_file}")
else:
    print(f"⚠️ Файл {env_file} не найден")


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Telegram Bot
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    
    # OpenAI/LM Studio
    openai_api_key: str = Field("not-needed", env="OPENAI_API_KEY")
    openai_api_base: str = Field("http://localhost:1234/v1", env="OPENAI_API_BASE")
    openai_model: str = Field("local-model", env="OPENAI_MODEL")
    
    # LangSmith (опционально)
    langchain_tracing_v2: bool = Field(False, env="LANGCHAIN_TRACING_V2")
    langchain_endpoint: Optional[str] = Field(None, env="LANGCHAIN_ENDPOINT")
    langchain_api_key: Optional[str] = Field(None, env="LANGCHAIN_API_KEY")
    langchain_project: str = Field("telegram-ai-trainer", env="LANGCHAIN_PROJECT")
    
    # База данных
    database_url: str = Field("sqlite:///data/user_progress.db", env="DATABASE_URL")
    
    # RAG настройки
    chroma_persist_directory: str = Field("data/chroma_db", env="CHROMA_PERSIST_DIRECTORY")
    embedding_model: str = Field(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", 
        env="EMBEDDING_MODEL"
    )
    knowledge_base_path: str = Field("data/knowledge_base.jsonl")
    
    # Настройки обучения - ИСПРАВЛЕНО: порог снижен до 67% (2 из 3 правильных)
    min_score_to_pass: int = Field(67, env="MIN_SCORE_TO_PASS")
    questions_per_lesson: int = Field(3, env="QUESTIONS_PER_LESSON")
    
    # Логирование
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("logs/bot.log", env="LOG_FILE")
    
    class Config:
        # НЕ указываем env_file чтобы избежать конфликтов
        extra = "ignore"


# Глобальная переменная настроек
settings = Settings()

# Создание необходимых директорий
os.makedirs(BASE_DIR / "data", exist_ok=True)
os.makedirs(BASE_DIR / "logs", exist_ok=True)
os.makedirs(settings.chroma_persist_directory, exist_ok=True)