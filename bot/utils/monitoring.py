"""
Система мониторинга и диагностики
Помогает отслеживать работу бота и AI-агента
"""
import logging
import time
import asyncio
from functools import wraps
from datetime import datetime
from typing import Dict, Any, Optional
from core.database import db_service

logger = logging.getLogger(__name__)

class BotMonitoring:
    """Класс для мониторинга работы бота"""
    
    def __init__(self):
        self.stats = {
            "total_requests": 0,
            "ai_requests": 0,
            "ai_timeouts": 0,
            "errors": 0,
            "lesson_completions": 0,
            "quiz_attempts": 0,
            "start_time": datetime.now()
        }
        self.response_times = []
        self.ai_response_times = []
    
    def track_request(self):
        """Отслеживание общего запроса"""
        self.stats["total_requests"] += 1
    
    def track_ai_request(self, response_time: float, success: bool = True, timeout: bool = False):
        """Отслеживание AI-запроса"""
        self.stats["ai_requests"] += 1
        if timeout:
            self.stats["ai_timeouts"] += 1
        if not success:
            self.stats["errors"] += 1
        if response_time > 0:
            self.ai_response_times.append(response_time)
    
    def track_error(self):
        """Отслеживание ошибки"""
        self.stats["errors"] += 1
    
    def track_lesson_completion(self):
        """Отслеживание завершения урока"""
        self.stats["lesson_completions"] += 1
    
    def track_quiz_attempt(self):
        """Отслеживание попытки тестирования"""
        self.stats["quiz_attempts"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        uptime = datetime.now() - self.stats["start_time"]
        avg_ai_time = sum(self.ai_response_times) / len(self.ai_response_times) if self.ai_response_times else 0
        
        return {
            **self.stats,
            "uptime_minutes": int(uptime.total_seconds() / 60),
            "avg_ai_response_time": round(avg_ai_time, 2),
            "ai_success_rate": round((self.stats["ai_requests"] - self.stats["ai_timeouts"] - self.stats["errors"]) / max(self.stats["ai_requests"], 1) * 100, 1),
            "error_rate": round(self.stats["errors"] / max(self.stats["total_requests"], 1) * 100, 1)
        }
    
    def get_status_report(self) -> str:
        """Генерация отчета о состоянии"""
        stats = self.get_stats()
        
        report = f"""🔍 **МОНИТОРИНГ БОТА**

⏱️ **Время работы:** {stats['uptime_minutes']} минут

📊 **Общая статистика:**
• Всего запросов: {stats['total_requests']}
• AI-запросов: {stats['ai_requests']}
• Ошибок: {stats['errors']} ({stats['error_rate']}%)
• Завершено уроков: {stats['lesson_completions']}
• Попыток тестирования: {stats['quiz_attempts']}

🤖 **AI-агент:**
• Успешность: {stats['ai_success_rate']}%
• Таймауты: {stats['ai_timeouts']}
• Среднее время ответа: {stats['avg_ai_response_time']}с

{"🟢 Система работает стабильно" if stats['error_rate'] < 5 else "🟡 Обнаружены проблемы" if stats['error_rate'] < 15 else "🔴 Критические ошибки"}"""
        
        return report

# Глобальный экземпляр мониторинга
monitoring = BotMonitoring()

def track_performance(operation_name: str = "operation"):
    """Декоратор для отслеживания производительности"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            monitoring.track_request()
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                monitoring.track_error()
                logger.error(f"Ошибка в {operation_name}: {e}")
                raise
            finally:
                end_time = time.time()
                response_time = end_time - start_time
                monitoring.response_times.append(response_time)
                if response_time > 5:  # Логируем медленные операции
                    logger.warning(f"Медленная операция {operation_name}: {response_time:.2f}с")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            monitoring.track_request()
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                monitoring.track_error()
                logger.error(f"Ошибка в {operation_name}: {e}")
                raise
            finally:
                end_time = time.time()
                response_time = end_time - start_time
                monitoring.response_times.append(response_time)
                if response_time > 3:  # Логируем медленные операции
                    logger.warning(f"Медленная операция {operation_name}: {response_time:.2f}с")
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def track_ai_performance(func):
    """Специальный декоратор для AI-операций"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        success = True
        timeout = False
        
        try:
            result = await func(*args, **kwargs)
            return result
        except asyncio.TimeoutError:
            timeout = True
            success = False
            logger.warning("AI-запрос превысил таймаут")
            raise
        except Exception as e:
            success = False
            logger.error(f"Ошибка AI-запроса: {e}")
            raise
        finally:
            response_time = time.time() - start_time
            monitoring.track_ai_request(response_time, success, timeout)
    
    @wraps(func) 
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        success = True
        timeout = False
        
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            success = False
            logger.error(f"Ошибка AI-запроса: {e}")
            raise
        finally:
            response_time = time.time() - start_time
            monitoring.track_ai_request(response_time, success, timeout)
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper