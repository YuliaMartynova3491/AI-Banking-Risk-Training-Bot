"""
Конфигурация производительности
"""

# Таймауты (в секундах)
TIMEOUTS = {
    "ai_response": 20,
    "quiz_generation": 15,
    "database_query": 10,
    "user_analysis": 25
}

# Лимиты
LIMITS = {
    "max_message_length": 4000,
    "max_ai_retries": 2,
    "max_concurrent_ai_requests": 3,
    "quiz_questions_per_lesson": 5
}

# Кэширование
CACHE_SETTINGS = {
    "enable_lesson_cache": True,
    "lesson_cache_ttl": 3600,  # 1 час
    "enable_ai_cache": False,  # Отключено для уникальности ответов
    "user_progress_cache_ttl": 300  # 5 минут
}

# Приоритеты операций
OPERATION_PRIORITIES = {
    "quiz_start": "high",
    "ai_question": "medium", 
    "progress_update": "high",
    "statistics": "low"
}