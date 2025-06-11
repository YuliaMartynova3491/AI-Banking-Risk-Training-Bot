"""
Оптимизатор производительности
"""
import asyncio
import time
from typing import Dict, Any, Optional
from functools import lru_cache
from config.performance_config import TIMEOUTS, LIMITS, CACHE_SETTINGS

class PerformanceOptimizer:
    """Класс для оптимизации производительности бота"""
    
    def __init__(self):
        self.operation_queue = asyncio.Queue()
        self.active_operations = {}
        self.cache = {}
    
    @staticmethod
    @lru_cache(maxsize=100)
    def get_cached_lesson_data(topic_id: str, lesson_id: int) -> Optional[Dict[str, Any]]:
        """Кэшированное получение данных урока"""
        if not CACHE_SETTINGS["enable_lesson_cache"]:
            return None
        
        from config.bot_config import LEARNING_STRUCTURE
        topic_data = LEARNING_STRUCTURE.get(topic_id)
        if not topic_data:
            return None
            
        for lesson in topic_data["lessons"]:
            if lesson["id"] == lesson_id:
                return lesson
        return None
    
    @staticmethod
    def optimize_message_length(message: str, max_length: int = None) -> str:
        """Оптимизация длины сообщения"""
        if max_length is None:
            max_length = LIMITS["max_message_length"]
        
        if len(message) <= max_length:
            return message
        
        # Умная обрезка с сохранением смысла
        sentences = message.split('. ')
        optimized = ""
        
        for sentence in sentences:
            if len(optimized + sentence + '. ') <= max_length - 50:
                optimized += sentence + '. '
            else:
                break
        
        if optimized:
            return optimized + "...\n\n*Сообщение сокращено для удобства чтения*"
        else:
            return message[:max_length-50] + "..."
    
    @staticmethod
    async def with_timeout(operation, timeout_key: str, *args, **kwargs):
        """Выполнение операции с таймаутом"""
        timeout = TIMEOUTS.get(timeout_key, 30)
        
        try:
            return await asyncio.wait_for(operation(*args, **kwargs), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Операция {timeout_key} превысила таймаут {timeout}с")
            raise
    
    def add_to_cache(self, key: str, value: Any, ttl: int = 300):
        """Добавление в кэш с TTL"""
        self.cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl
        }
    
    def get_from_cache(self, key: str) -> Optional[Any]:
        """Получение из кэша"""
        if key not in self.cache:
            return None
        
        cache_entry = self.cache[key]
        if time.time() > cache_entry["expires_at"]:
            del self.cache[key]
            return None
        
        return cache_entry["value"]
    
    def clear_expired_cache(self):
        """Очистка устаревшего кэша"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items() 
            if current_time > entry["expires_at"]
        ]
        
        for key in expired_keys:
            del self.cache[key]

# Глобальный оптимизатор
optimizer = PerformanceOptimizer()