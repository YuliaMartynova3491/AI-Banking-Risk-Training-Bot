"""
Middleware для обработки пользователей и контекста
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

from core.database import db_service
from core.models import UserData
from core.enums import Constants
from services.progress_service import progress_service
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class UserMiddleware:
    """Middleware для управления пользователями и их контекстом"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.rate_limits: Dict[str, datetime] = {}
    
    async def process_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[Dict[str, Any]]:
        """Обработка пользователя перед выполнением основной логики"""
        user = update.effective_user
        
        if not user:
            logger.warning("Получено обновление без информации о пользователе")
            return None
        
        user_id = str(user.id)
        
        try:
            # Проверяем rate limiting
            if not self._check_rate_limit(user_id):
                logger.warning(f"Rate limit exceeded for user {user_id}")
                await self._send_rate_limit_message(update, context)
                return None
            
            # Получаем или создаем пользователя в БД
            user_data = UserData(
                user_id=user_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            db_user = db_service.get_or_create_user(user_data)
            
            # Обновляем активную сессию
            session_data = self._update_session(user_id, user_data)
            
            # Добавляем данные в контекст
            context.user_data.update({
                "db_user_id": db_user.id,
                "user_profile": self._build_user_profile(db_user),
                "session_data": session_data,
                "middleware_processed": True
            })
            
            # Проверяем сессию на валидность
            if self._is_session_expired(session_data):
                await self._handle_session_expiry(update, context, user_id)
            
            return {
                "user_id": user_id,
                "db_user": db_user,
                "session_data": session_data
            }
            
        except Exception as e:
            logger.error(f"Ошибка обработки пользователя {user_id}: {e}")
            await self._send_error_message(update, context)
            return None
    
    def _check_rate_limit(self, user_id: str) -> bool:
        """Проверка лимита частоты запросов"""
        now = datetime.utcnow()
        
        if user_id in self.rate_limits:
            last_request = self.rate_limits[user_id]
            if now - last_request < timedelta(seconds=1):  # 1 запрос в секунду
                return False
        
        self.rate_limits[user_id] = now
        
        # Очищаем старые записи
        cutoff_time = now - timedelta(minutes=5)
        self.rate_limits = {
            uid: timestamp for uid, timestamp in self.rate_limits.items()
            if timestamp > cutoff_time
        }
        
        return True
    
    def _update_session(self, user_id: str, user_data: UserData) -> Dict[str, Any]:
        """Обновление данных сессии пользователя"""
        now = datetime.utcnow()
        
        if user_id not in self.active_sessions:
            # Создаем новую сессию
            self.active_sessions[user_id] = {
                "created_at": now,
                "last_activity": now,
                "request_count": 1,
                "current_flow": None,
                "temp_data": {},
                "user_preferences": {},
                "ai_context": []
            }
        else:
            # Обновляем существующую сессию
            session = self.active_sessions[user_id]
            session["last_activity"] = now
            session["request_count"] += 1
        
        return self.active_sessions[user_id]
    
    def _build_user_profile(self, db_user) -> Dict[str, Any]:
        """Построение профиля пользователя для использования в обработчиках"""
        try:
            # Получаем статистику пользователя
            progress_stats = progress_service.get_overall_statistics(db_user.user_id)
            
            profile = {
                "user_id": db_user.user_id,
                "username": db_user.username,
                "first_name": db_user.first_name,
                "total_lessons": db_user.total_lessons_completed,
                "average_score": db_user.total_score,
                "current_topic": db_user.current_topic,
                "current_lesson": db_user.current_lesson,
                "created_at": db_user.created_at,
                "last_activity": db_user.last_activity,
                
                # Данные из анализа прогресса
                "experience_level": self._determine_experience_level(progress_stats),
                "learning_style": self._determine_learning_style(progress_stats),
                "motivation_level": self._determine_motivation_level(progress_stats),
                "support_needs": self._determine_support_needs(progress_stats),
                
                # Предпочтения
                "preferences": db_user.preferences or {},
                "ai_context": db_user.ai_context or {}
            }
            
            return profile
            
        except Exception as e:
            logger.error(f"Ошибка построения профиля пользователя: {e}")
            return {
                "user_id": db_user.user_id,
                "username": db_user.username,
                "first_name": db_user.first_name,
                "experience_level": "beginner",
                "learning_style": "balanced",
                "motivation_level": "medium",
                "support_needs": "medium"
            }
    
    def _determine_experience_level(self, progress_stats: Dict[str, Any]) -> str:
        """Определение уровня опыта пользователя"""
        completed_lessons = progress_stats.get("total_lessons_completed", 0)
        average_score = progress_stats.get("average_score", 0)
        
        if completed_lessons >= 15 and average_score >= 85:
            return "advanced"
        elif completed_lessons >= 5 and average_score >= 70:
            return "intermediate"
        else:
            return "beginner"
    
    def _determine_learning_style(self, progress_stats: Dict[str, Any]) -> str:
        """Определение стиля обучения (упрощенная версия)"""
        # В реальной реализации можно анализировать предпочтения пользователя
        # На основе того, какие типы контента он чаще использует
        return "balanced"  # По умолчанию
    
    def _determine_motivation_level(self, progress_stats: Dict[str, Any]) -> str:
        """Определение уровня мотивации"""
        completion_rate = progress_stats.get("overall_completion", 0)
        learning_streak = progress_stats.get("learning_streak", 0)
        
        if completion_rate >= 80 and learning_streak >= 5:
            return "high"
        elif completion_rate >= 40 and learning_streak >= 2:
            return "medium"
        else:
            return "low"
    
    def _determine_support_needs(self, progress_stats: Dict[str, Any]) -> str:
        """Определение потребности в поддержке"""
        weak_topics = progress_stats.get("weak_topics", [])
        average_score = progress_stats.get("average_score", 0)
        
        if len(weak_topics) >= 2 or average_score < 60:
            return "high"
        elif len(weak_topics) == 1 or average_score < 80:
            return "medium"
        else:
            return "low"
    
    def _is_session_expired(self, session_data: Dict[str, Any]) -> bool:
        """Проверка, истекла ли сессия"""
        last_activity = session_data.get("last_activity")
        if not last_activity:
            return True
        
        now = datetime.utcnow()
        session_timeout = timedelta(seconds=Constants.SESSION_TIMEOUT)
        
        return now - last_activity > session_timeout
    
    async def _handle_session_expiry(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str):
        """Обработка истечения сессии"""
        # Очищаем временные данные
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            session["temp_data"] = {}
            session["current_flow"] = None
            
        # Уведомляем пользователя (опционально)
        # await context.bot.send_message(
        #     chat_id=update.effective_chat.id,
        #     text="Сессия истекла. Начните заново с /start"
        # )
    
    async def _send_rate_limit_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка сообщения о превышении лимита запросов"""
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⏳ Пожалуйста, подождите немного между запросами."
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения о rate limit: {e}")
    
    async def _send_error_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка сообщения об ошибке"""
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Произошла ошибка обработки. Попробуйте позже."
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения об ошибке: {e}")
    
    def get_session_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Получение данных сессии пользователя"""
        return self.active_sessions.get(user_id)
    
    def update_session_data(self, user_id: str, key: str, value: Any):
        """Обновление данных сессии"""
        if user_id in self.active_sessions:
            self.active_sessions[user_id]["temp_data"][key] = value
    
    def clear_session_data(self, user_id: str, key: str = None):
        """Очистка данных сессии"""
        if user_id in self.active_sessions:
            if key:
                self.active_sessions[user_id]["temp_data"].pop(key, None)
            else:
                self.active_sessions[user_id]["temp_data"] = {}
    
    def set_current_flow(self, user_id: str, flow_name: str):
        """Установка текущего потока обработки"""
        if user_id in self.active_sessions:
            self.active_sessions[user_id]["current_flow"] = flow_name
    
    def get_current_flow(self, user_id: str) -> Optional[str]:
        """Получение текущего потока обработки"""
        session = self.active_sessions.get(user_id)
        return session.get("current_flow") if session else None
    
    def add_ai_context(self, user_id: str, context_item: Dict[str, Any]):
        """Добавление контекста для AI"""
        if user_id in self.active_sessions:
            ai_context = self.active_sessions[user_id].get("ai_context", [])
            ai_context.append({
                **context_item,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Ограничиваем размер контекста
            if len(ai_context) > 10:
                ai_context = ai_context[-10:]
            
            self.active_sessions[user_id]["ai_context"] = ai_context
    
    def get_ai_context(self, user_id: str) -> List[Dict[str, Any]]:
        """Получение контекста для AI"""
        session = self.active_sessions.get(user_id)
        return session.get("ai_context", []) if session else []
    
    def cleanup_inactive_sessions(self, max_age_hours: int = 24):
        """Очистка неактивных сессий"""
        now = datetime.utcnow()
        cutoff_time = now - timedelta(hours=max_age_hours)
        
        inactive_users = [
            user_id for user_id, session in self.active_sessions.items()
            if session.get("last_activity", now) < cutoff_time
        ]
        
        for user_id in inactive_users:
            del self.active_sessions[user_id]
            logger.info(f"Удалена неактивная сессия пользователя {user_id}")
        
        return len(inactive_users)


# Декоратор для автоматической обработки пользователей
def user_required(func):
    """Декоратор, требующий обработки пользователя через middleware"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # Проверяем, обработан ли пользователь через middleware
        if not context.user_data.get("middleware_processed"):
            middleware = UserMiddleware()
            user_context = await middleware.process_user(update, context)
            
            if not user_context:
                return  # Middleware обработал ошибку
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


# Глобальный экземпляр middleware
user_middleware = UserMiddleware()