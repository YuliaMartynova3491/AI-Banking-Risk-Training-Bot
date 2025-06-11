"""
Система восстановления после ошибок
"""
import logging
import asyncio
from typing import Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)

class ErrorRecovery:
    """Класс для восстановления после ошибок"""
    
    @staticmethod
    def with_retry(max_retries: int = 2, delay: float = 1.0):
        """Декоратор для повторных попыток"""
        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_retries:
                            logger.warning(f"Попытка {attempt + 1} неудачна, повторяю через {delay}с: {e}")
                            await asyncio.sleep(delay)
                        else:
                            logger.error(f"Все {max_retries + 1} попыток неудачны: {e}")
                
                raise last_exception
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_retries:
                            logger.warning(f"Попытка {attempt + 1} неудачна, повторяю через {delay}с: {e}")
                            import time
                            time.sleep(delay)
                        else:
                            logger.error(f"Все {max_retries + 1} попыток неудачны: {e}")
                
                raise last_exception
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    @staticmethod
    def safe_execute(func: Callable, fallback_value: Any = None, log_errors: bool = True):
        """Безопасное выполнение функции с fallback"""
        try:
            return func()
        except Exception as e:
            if log_errors:
                logger.error(f"Ошибка в safe_execute: {e}")
            return fallback_value
    
    @staticmethod
    async def safe_execute_async(func: Callable, fallback_value: Any = None, log_errors: bool = True):
        """Безопасное асинхронное выполнение функции с fallback"""
        try:
            return await func()
        except Exception as e:
            if log_errors:
                logger.error(f"Ошибка в safe_execute_async: {e}")
            return fallback_value

# Экземпляр восстановления
recovery = ErrorRecovery()