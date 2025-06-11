"""
Настройки приложения AI-агента
"""
import os
import logging
from pathlib import Path
from typing import Optional, List
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Корневая директория проекта
BASE_DIR = Path(__file__).parent.parent

# Настройка логирования для загрузки настроек
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
env_file = BASE_DIR / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)
    logger.info(f"✅ [Settings] Загружен файл настроек: {env_file}")
else:
    logger.warning(f"⚠️ [Settings] Файл {env_file} не найден, используются значения по умолчанию")


class Settings(BaseSettings):
    """Настройки AI-агента для обучения банковским рискам"""
    
    # === TELEGRAM BOT ===
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN", description="Токен Telegram бота")
    
    # === AI-АГЕНТ (LLM) ===
    openai_api_key: str = Field("not-needed", env="OPENAI_API_KEY", description="API ключ для LLM")
    openai_api_base: str = Field("http://localhost:1234/v1", env="OPENAI_API_BASE", description="URL сервера LLM")
    openai_model: str = Field("gpt-4o-mini", env="OPENAI_MODEL", description="Модель LLM")
    
    # === НАСТРОЙКИ LLM ДЛЯ АГЕНТА ===
    llm_temperature: float = Field(0.3, env="LLM_TEMPERATURE", description="Температура LLM (0.0-2.0)")
    llm_max_tokens: int = Field(1000, env="LLM_MAX_TOKENS", description="Максимум токенов в ответе")
    llm_timeout: int = Field(30, env="LLM_TIMEOUT", description="Таймаут запросов к LLM (сек)")
    llm_max_retries: int = Field(3, env="LLM_MAX_RETRIES", description="Количество повторов при ошибках")
    
    # === LANGSMITH (ОТЛАДКА АГЕНТА) ===
    langchain_tracing_v2: bool = Field(False, env="LANGCHAIN_TRACING_V2", description="Включить трейсинг LangChain")
    langchain_endpoint: Optional[str] = Field(None, env="LANGCHAIN_ENDPOINT", description="Endpoint LangSmith")
    langchain_api_key: Optional[str] = Field(None, env="LANGCHAIN_API_KEY", description="API ключ LangSmith")
    langchain_project: str = Field("ai-bank-risk-agent", env="LANGCHAIN_PROJECT", description="Проект в LangSmith")
    
    # === БАЗА ДАННЫХ ===
    database_url: str = Field("sqlite:///data/ai_agent.db", env="DATABASE_URL", description="URL базы данных")
    db_pool_size: int = Field(10, env="DB_POOL_SIZE", description="Размер пула соединений БД")
    db_max_overflow: int = Field(20, env="DB_MAX_OVERFLOW", description="Максимальное переполнение пула БД")
    db_pool_recycle: int = Field(3600, env="DB_POOL_RECYCLE", description="Время жизни соединений БД (сек)")
    
    # === RAG И БАЗА ЗНАНИЙ ===
    chroma_persist_directory: str = Field("data/chroma_db", env="CHROMA_PERSIST_DIRECTORY", description="Директория ChromaDB")
    chroma_collection_name: str = Field("bank_risks_knowledge", env="CHROMA_COLLECTION_NAME", description="Имя коллекции ChromaDB")
    embedding_model: str = Field(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", 
        env="EMBEDDING_MODEL",
        description="Модель для эмбеддингов"
    )
    knowledge_base_path: str = Field("data/knowledge_base.jsonl", env="KNOWLEDGE_BASE_PATH", description="Путь к базе знаний")
    
    # === НАСТРОЙКИ ОБУЧЕНИЯ ===
    min_score_to_pass: float = Field(67.0, env="MIN_SCORE_TO_PASS", description="Минимальный балл для прохождения (%)")
    questions_per_lesson: int = Field(3, env="QUESTIONS_PER_LESSON", description="Количество вопросов в уроке")
    max_attempts_per_lesson: int = Field(5, env="MAX_ATTEMPTS_PER_LESSON", description="Максимум попыток на урок")
    
    # === НАСТРОЙКИ AI-АГЕНТА ===
    agent_processing_timeout: int = Field(60, env="AGENT_PROCESSING_TIMEOUT", description="Таймаут обработки агентом (сек)")
    agent_response_max_length: int = Field(1000, env="AGENT_RESPONSE_MAX_LENGTH", description="Максимальная длина ответа агента")
    knowledge_search_timeout: int = Field(10, env="KNOWLEDGE_SEARCH_TIMEOUT", description="Таймаут поиска в базе знаний (сек)")
    
    # === СТРАТЕГИИ FALLBACK ===
    enable_static_fallback: bool = Field(True, env="ENABLE_STATIC_FALLBACK", description="Включить статические ответы как fallback")
    enable_llm_fallback: bool = Field(True, env="ENABLE_LLM_FALLBACK", description="Включить LLM fallback")
    fallback_response_quality: str = Field("high", env="FALLBACK_RESPONSE_QUALITY", description="Качество fallback ответов")
    
    # === ОТЛАДКА И МОНИТОРИНГ ===
    enable_agent_debug: bool = Field(True, env="ENABLE_AGENT_DEBUG", description="Включить отладку агента")
    log_agent_responses: bool = Field(True, env="LOG_AGENT_RESPONSES", description="Логировать ответы агента")
    log_level: str = Field("INFO", env="LOG_LEVEL", description="Уровень логирования")
    log_file: str = Field("logs/ai_agent.log", env="LOG_FILE", description="Файл логов")
    log_max_size: int = Field(10, env="LOG_MAX_SIZE", description="Максимальный размер лога (MB)")
    log_backup_count: int = Field(5, env="LOG_BACKUP_COUNT", description="Количество backup логов")
    
    # === ПРОИЗВОДИТЕЛЬНОСТЬ ===
    enable_caching: bool = Field(True, env="ENABLE_CACHING", description="Включить кэширование")
    cache_ttl: int = Field(3600, env="CACHE_TTL", description="Время жизни кэша (сек)")
    max_concurrent_users: int = Field(100, env="MAX_CONCURRENT_USERS", description="Максимум одновременных пользователей")
    
    # === БЕЗОПАСНОСТЬ ===
    allowed_user_ids: Optional[List[str]] = Field(None, env="ALLOWED_USER_IDS", description="Разрешенные ID пользователей")
    rate_limit_requests: int = Field(60, env="RATE_LIMIT_REQUESTS", description="Лимит запросов в минуту")
    
    # === ВАЛИДАТОРЫ (Pydantic v2) ===
    
    @field_validator('llm_temperature')
    @classmethod
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError('Температура LLM должна быть от 0.0 до 2.0')
        return v
    
    @field_validator('min_score_to_pass')
    @classmethod
    def validate_min_score(cls, v):
        if not 0.0 <= v <= 100.0:
            raise ValueError('Минимальный балл должен быть от 0 до 100')
        return v
    
    @field_validator('questions_per_lesson')
    @classmethod
    def validate_questions_count(cls, v):
        if not 1 <= v <= 10:
            raise ValueError('Количество вопросов должно быть от 1 до 10')
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Уровень логирования должен быть одним из: {valid_levels}')
        return v.upper()
    
    @field_validator('fallback_response_quality')
    @classmethod
    def validate_fallback_quality(cls, v):
        valid_qualities = ['low', 'medium', 'high']
        if v.lower() not in valid_qualities:
            raise ValueError(f'Качество fallback должно быть одним из: {valid_qualities}')
        return v.lower()
    
    @field_validator('allowed_user_ids', mode='before')
    @classmethod
    def parse_allowed_users(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return [uid.strip() for uid in v.split(',') if uid.strip()]
        return v
    
    @model_validator(mode='after')
    def validate_paths_exist(self):
        """Проверяем и создаем необходимые директории"""
        try:
            # Создаем базовые директории
            data_dir = BASE_DIR / "data"
            logs_dir = BASE_DIR / "logs"
            
            data_dir.mkdir(exist_ok=True)
            logs_dir.mkdir(exist_ok=True)
            
            # Создаем директорию ChromaDB
            chroma_dir = BASE_DIR / self.chroma_persist_directory
            chroma_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"✅ [Settings] Созданы директории: {data_dir}, {logs_dir}, {chroma_dir}")
            
        except Exception as e:
            logger.error(f"❌ [Settings] Ошибка создания директорий: {e}")
            raise ValueError(f"Не удалось создать необходимые директории: {e}")
        
        return self
    
    # === ВЫЧИСЛЯЕМЫЕ СВОЙСТВА ===
    
    @property
    def data_dir(self) -> Path:
        """Директория данных"""
        return BASE_DIR / "data"
    
    @property
    def logs_dir(self) -> Path:
        """Директория логов"""
        return BASE_DIR / "logs"
    
    @property
    def chroma_path(self) -> Path:
        """Полный путь к ChromaDB"""
        return BASE_DIR / self.chroma_persist_directory
    
    @property
    def knowledge_base_file(self) -> Path:
        """Полный путь к базе знаний"""
        return BASE_DIR / self.knowledge_base_path
    
    @property
    def log_file_path(self) -> Path:
        """Полный путь к файлу логов"""
        return BASE_DIR / self.log_file
    
    @property
    def is_local_llm(self) -> bool:
        """Используется ли локальная LLM"""
        return 'localhost' in self.openai_api_base or '127.0.0.1' in self.openai_api_base
    
    @property
    def is_production(self) -> bool:
        """Режим продакшена"""
        return os.getenv('ENVIRONMENT', 'development').lower() == 'production'
    
    # === МЕТОДЫ ===
    
    def get_llm_config(self) -> dict:
        """Получить конфигурацию для LLM"""
        return {
            'api_key': self.openai_api_key,
            'base_url': self.openai_api_base,
            'model': self.openai_model,
            'temperature': self.llm_temperature,
            'max_tokens': self.llm_max_tokens,
            'timeout': self.llm_timeout,
            'max_retries': self.llm_max_retries
        }
    
    def get_database_config(self) -> dict:
        """Получить конфигурацию для базы данных"""
        config = {
            'url': self.database_url,
            'pool_size': self.db_pool_size,
            'max_overflow': self.db_max_overflow,
            'pool_recycle': self.db_pool_recycle,
            'pool_pre_ping': True,
            'echo': self.enable_agent_debug and self.log_level == 'DEBUG'
        }
        
        # Добавляем настройки для SQLite
        if 'sqlite' in self.database_url:
            config['connect_args'] = {"check_same_thread": False}
        
        return config
    
    def get_chroma_config(self) -> dict:
        """Получить конфигурацию для ChromaDB"""
        return {
            'persist_directory': str(self.chroma_path),
            'collection_name': self.chroma_collection_name,
            'embedding_model': self.embedding_model
        }
    
    def validate_required_files(self) -> List[str]:
        """Проверить наличие обязательных файлов"""
        missing_files = []
        
        # Проверяем базу знаний
        if not self.knowledge_base_file.exists():
            missing_files.append(str(self.knowledge_base_file))
        
        return missing_files
    
    def get_agent_config(self) -> dict:
        """Получить конфигурацию агента"""
        return {
            'processing_timeout': self.agent_processing_timeout,
            'response_max_length': self.agent_response_max_length,
            'knowledge_search_timeout': self.knowledge_search_timeout,
            'enable_static_fallback': self.enable_static_fallback,
            'enable_llm_fallback': self.enable_llm_fallback,
            'fallback_response_quality': self.fallback_response_quality,
            'enable_debug': self.enable_agent_debug,
            'log_responses': self.log_agent_responses
        }
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
        "validate_assignment": True
    }


# Создаем глобальный экземпляр настроек
try:
    settings = Settings()
    logger.info("✅ [Settings] Настройки AI-агента загружены успешно")
    
    # Проверяем обязательные файлы
    missing_files = settings.validate_required_files()
    if missing_files:
        logger.warning(f"⚠️ [Settings] Отсутствуют файлы: {missing_files}")
    
    # Логируем важные настройки
    logger.info(f"🤖 [Settings] LLM: {settings.openai_model} @ {settings.openai_api_base}")
    logger.info(f"🗄️ [Settings] БД: {settings.database_url}")
    logger.info(f"📚 [Settings] База знаний: {settings.knowledge_base_file}")
    logger.info(f"🔧 [Settings] Режим отладки: {settings.enable_agent_debug}")
    
except Exception as e:
    logger.error(f"❌ [Settings] Критическая ошибка загрузки настроек: {e}")
    raise SystemExit(f"Не удалось загрузить настройки: {e}")


# === ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ ===

def get_environment_info() -> dict:
    """Получить информацию об окружении"""
    return {
        'base_dir': str(BASE_DIR),
        'python_version': os.sys.version,
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'is_production': settings.is_production,
        'is_local_llm': settings.is_local_llm,
        'data_dir_exists': settings.data_dir.exists(),
        'logs_dir_exists': settings.logs_dir.exists(),
        'chroma_dir_exists': settings.chroma_path.exists(),
        'knowledge_base_exists': settings.knowledge_base_file.exists()
    }

def print_config_summary():
    """Вывести сводку конфигурации"""
    print("\n" + "="*60)
    print("🤖 AI-АГЕНТ КОНФИГУРАЦИЯ")
    print("="*60)
    
    print(f"📱 Telegram Token: {'✅ Настроен' if settings.telegram_bot_token else '❌ Отсутствует'}")
    print(f"🧠 LLM Модель: {settings.openai_model}")
    print(f"🌐 LLM URL: {settings.openai_api_base}")
    print(f"🗄️ База данных: {settings.database_url}")
    print(f"📚 База знаний: {settings.knowledge_base_file}")
    print(f"🔧 Отладка: {'Включена' if settings.enable_agent_debug else 'Отключена'}")
    print(f"📊 Мин. балл: {settings.min_score_to_pass}%")
    print(f"❓ Вопросов в уроке: {settings.questions_per_lesson}")
    
    env_info = get_environment_info()
    print(f"🌍 Окружение: {env_info['environment']}")
    print(f"🏠 Базовая папка: {env_info['base_dir']}")
    
    print("="*60 + "\n")

# Выводим сводку при импорте (только если это главный модуль)
if __name__ == "__main__":
    print_config_summary()