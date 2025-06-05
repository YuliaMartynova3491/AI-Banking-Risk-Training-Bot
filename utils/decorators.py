"""
Декораторы для AI-агента
"""
import logging
import functools
import asyncio
from typing import Any, Callable, Dict, Optional
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

from core.database import db_service
from core.models import UserData
from core.enums import Constants
from bot.middleware.user_middleware import user_middleware

logger = logging.getLogger(__name__)


def error_handler(func: Callable) -> Callable:
    """Декоратор для обработки ошибок в обработчиках"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка в {func.__name__}: {e}", exc_info=True)
            
            # Отправляем пользователю сообщение об ошибке
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="😕 Произошла ошибка. Попробуйте еще раз или обратитесь в поддержку."
                )
            except Exception as send_error:
                logger.error(f"Не удалось отправить сообщение об ошибке: {send_error}")
    
    return wrapper


def user_authentication(func: Callable) -> Callable:
    """Декоратор для аутентификации пользователя"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        
        if not user:
            logger.warning("Попытка доступа без пользователя")
            return
        
        user_id = str(user.id)
        
        # Получаем или создаем пользователя
        user_data = UserData(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        db_user = db_service.get_or_create_user(user_data)
        
        # Добавляем данные пользователя в контекст
        context.user_data["authenticated_user"] = db_user
        context.user_data["user_id"] = user_id
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def rate_limit(requests_per_minute: int = 30):
    """Декоратор для ограничения частоты запросов"""
    user_requests: Dict[str, list] = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = str(update.effective_user.id) if update.effective_user else "anonymous"
            now = datetime.utcnow()
            
            # Инициализируем список запросов для пользователя
            if user_id not in user_requests:
                user_requests[user_id] = []
            
            # Очищаем старые запросы (старше минуты)
            minute_ago = now - timedelta(minutes=1)
            user_requests[user_id] = [
                req_time for req_time in user_requests[user_id] 
                if req_time > minute_ago
            ]
            
            # Проверяем лимит
            if len(user_requests[user_id]) >= requests_per_minute:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⏳ Слишком много запросов. Пожалуйста, подождите немного."
                )
                return
            
            # Добавляем текущий запрос
            user_requests[user_id].append(now)
            
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    return decorator


def session_required(func: Callable) -> Callable:
    """Декоратор, требующий активной сессии пользователя"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = str(update.effective_user.id) if update.effective_user else None
        
        if not user_id:
            return
        
        # Проверяем наличие активной сессии
        session_data = user_middleware.get_session_data(user_id)
        
        if not session_data:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Сессия не найдена. Начните с команды /start"
            )
            return
        
        # Проверяем, не истекла ли сессия
        last_activity = session_data.get("last_activity")
        if last_activity:
            now = datetime.utcnow()
            if now - last_activity > timedelta(seconds=Constants.SESSION_TIMEOUT):
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Сессия истекла. Начните заново с /start"
                )
                return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def admin_required(func: Callable) -> Callable:
    """Декоратор для проверки прав администратора"""
    # Список ID администраторов (в продакшене брать из конфигурации)
    ADMIN_IDS = {"123456789", "987654321"}  # Замените на реальные ID
    
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = str(update.effective_user.id) if update.effective_user else None
        
        if user_id not in ADMIN_IDS:
            logger.warning(f"Unauthorized admin access attempt by user {user_id}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Доступ запрещен. Эта функция доступна только администраторам."
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def typing_action(func: Callable) -> Callable:
    """Декоратор для отображения действия 'печатает'"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # Отправляем действие "печатает"
        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="typing"
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить chat action: {e}")
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def log_user_action(action_name: str):
    """Декоратор для логирования действий пользователя"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = str(update.effective_user.id) if update.effective_user else "unknown"
            username = update.effective_user.username if update.effective_user else "unknown"
            
            logger.info(f"User action: {action_name} by {user_id} ({username})")
            
            # Добавляем действие в контекст AI
            user_middleware.add_ai_context(user_id, {
                "type": "user_action",
                "action": action_name,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    return decorator


def timeout(seconds: int = 30):
    """Декоратор для установки таймаута выполнения функции"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.error(f"Timeout in {func.__name__} after {seconds} seconds")
                # Если есть update и context в аргументах, отправляем сообщение
                if len(args) >= 2 and hasattr(args[0], 'effective_chat'):
                    update, context = args[0], args[1]
                    try:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="⏰ Операция заняла слишком много времени. Попробуйте позже."
                        )
                    except Exception:
                        pass
                raise
        
        return wrapper
    return decorator


def validate_callback_data(expected_pattern: str):
    """Декоратор для валидации callback_data"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            if not update.callback_query:
                logger.warning(f"Expected callback query in {func.__name__}")
                return
            
            callback_data = update.callback_query.data
            
            # Простая проверка на соответствие паттерну
            if not callback_data.startswith(expected_pattern):
                logger.warning(f"Invalid callback data: {callback_data}, expected pattern: {expected_pattern}")
                await update.callback_query.answer("❌ Некорректные данные", show_alert=True)
                return
            
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    return decorator


def quiz_session_required(func: Callable) -> Callable:
    """Декоратор, требующий активной сессии тестирования"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = str(update.effective_user.id) if update.effective_user else None
        
        if not user_id:
            return
        
        # Проверяем наличие активной сессии тестирования
        quiz_session = db_service.get_active_quiz_session(user_id)
        
        if not quiz_session:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Активная сессия тестирования не найдена. Начните урок заново."
            )
            return
        
        # Проверяем таймаут сессии
        session_start = quiz_session.started_at
        if session_start:
            now = datetime.utcnow()
            if now - session_start > timedelta(seconds=Constants.QUIZ_TIMEOUT):
                # Завершаем просроченную сессию
                db_service.complete_quiz_session(quiz_session.id, 0)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⏰ Время тестирования истекло. Начните урок заново."
                )
                return
        
        # Добавляем сессию в контекст
        context.user_data["quiz_session"] = quiz_session
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def performance_monitor(func: Callable) -> Callable:
    """Декоратор для мониторинга производительности"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = datetime.utcnow()
        
        try:
            result = await func(*args, **kwargs)
            
            # Логируем успешное выполнение
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Function {func.__name__} executed in {execution_time:.3f}s")
            
            # Предупреждаем о медленных функциях
            if execution_time > 5.0:
                logger.warning(f"Slow function detected: {func.__name__} took {execution_time:.3f}s")
            
            return result
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Function {func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    
    return wrapper


def cache_result(ttl_seconds: int = 300):
    """Декоратор для кэширования результатов функций"""
    cache: Dict[str, Dict[str, Any]] = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Создаем ключ кэша
            cache_key = f"{func.__name__}_{hash(str(args))}_{hash(str(sorted(kwargs.items())))}"
            
            now = datetime.utcnow()
            
            # Проверяем кэш
            if cache_key in cache:
                cached_data = cache[cache_key]
                if now - cached_data["timestamp"] < timedelta(seconds=ttl_seconds):
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached_data["result"]
                else:
                    # Удаляем устаревшую запись
                    del cache[cache_key]
            
            # Выполняем функцию и кэшируем результат
            result = await func(*args, **kwargs)
            cache[cache_key] = {
                "result": result,
                "timestamp": now
            }
            
            logger.debug(f"Cache miss for {func.__name__}, result cached")
            return result
        
        return wrapper
    return decorator


def ai_context_tracker(context_type: str):
    """Декоратор для отслеживания контекста AI-взаимодействий"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = str(update.effective_user.id) if update.effective_user else None
            
            if user_id:
                # Добавляем контекст перед выполнением
                user_middleware.add_ai_context(user_id, {
                    "type": context_type,
                    "function": func.__name__,
                    "start_time": datetime.utcnow().isoformat()
                })
            
            try:
                result = await func(update, context, *args, **kwargs)
                
                if user_id:
                    # Добавляем контекст после успешного выполнения
                    user_middleware.add_ai_context(user_id, {
                        "type": f"{context_type}_completed",
                        "function": func.__name__,
                        "end_time": datetime.utcnow().isoformat(),
                        "status": "success"
                    })
                
                return result
                
            except Exception as e:
                if user_id:
                    # Добавляем контекст об ошибке
                    user_middleware.add_ai_context(user_id, {
                        "type": f"{context_type}_error",
                        "function": func.__name__,
                        "end_time": datetime.utcnow().isoformat(),
                        "status": "error",
                        "error": str(e)
                    })
                raise
        
        return wrapper
    return decorator


# Комбинированные декораторы для удобства

def standard_handler(func: Callable) -> Callable:
    """Стандартный набор декораторов для обработчиков"""
    return error_handler(
        user_authentication(
            typing_action(
                performance_monitor(func)
            )
        )
    )


def quiz_handler(func: Callable) -> Callable:
    """Набор декораторов для обработчиков тестирования"""
    return error_handler(
        user_authentication(
            quiz_session_required(
                rate_limit(10)(  # Ограничиваем до 10 запросов в минуту для квизов
                    performance_monitor(func)
                )
            )
        )
    )


def ai_handler(func: Callable) -> Callable:
    """Набор декораторов для AI-обработчиков"""
    return error_handler(
        user_authentication(
            ai_context_tracker("ai_interaction")(
                timeout(30)(  # 30 секунд таймаут для AI-операций
                    performance_monitor(func)
                )
            )
        )
    )