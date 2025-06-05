"""
Сервис управления стикерами
"""
import random
import logging
from typing import Dict, Any, Optional
from config.bot_config import STICKERS, StickerType

logger = logging.getLogger(__name__)


class StickerService:
    """Сервис для управления отправкой стикеров"""
    
    def __init__(self):
        self.user_sticker_history: Dict[str, Dict[str, int]] = {}
    
    def get_sticker(self, sticker_type: StickerType, user_id: str = None) -> str:
        """Получить стикер определенного типа"""
        try:
            stickers_list = STICKERS.get(sticker_type, [])
            
            if not stickers_list:
                logger.warning(f"Стикеры типа {sticker_type} не найдены")
                return ""
            
            # Если только один стикер - возвращаем его
            if len(stickers_list) == 1:
                return stickers_list[0]
            
            # Если несколько стикеров - выбираем случайно, избегая повторов
            if user_id:
                return self._get_sticker_with_rotation(sticker_type, stickers_list, user_id)
            else:
                return random.choice(stickers_list)
                
        except Exception as e:
            logger.error(f"Ошибка получения стикера {sticker_type}: {e}")
            return ""
    
    def _get_sticker_with_rotation(self, sticker_type: StickerType, 
                                  stickers_list: list, user_id: str) -> str:
        """Выбор стикера с ротацией для избежания повторов"""
        
        # Инициализируем историю пользователя если нужно
        if user_id not in self.user_sticker_history:
            self.user_sticker_history[user_id] = {}
        
        sticker_type_str = sticker_type.value
        
        # Если история для этого типа стикера пуста
        if sticker_type_str not in self.user_sticker_history[user_id]:
            self.user_sticker_history[user_id][sticker_type_str] = 0
            return stickers_list[0]
        
        # Получаем индекс следующего стикера
        current_index = self.user_sticker_history[user_id][sticker_type_str]
        next_index = (current_index + 1) % len(stickers_list)
        
        # Обновляем историю
        self.user_sticker_history[user_id][sticker_type_str] = next_index
        
        return stickers_list[next_index]
    
    def get_welcome_sticker(self, user_id: str = None) -> str:
        """Получить приветственный стикер"""
        return self.get_sticker(StickerType.WELCOME, user_id)
    
    def get_correct_answer_sticker(self, user_id: str, is_first_correct: bool = False) -> str:
        """Получить стикер за правильный ответ"""
        if is_first_correct:
            return self.get_sticker(StickerType.FIRST_CORRECT, user_id)
        else:
            return self.get_sticker(StickerType.CORRECT, user_id)
    
    def get_wrong_answer_sticker(self, user_id: str, consecutive_wrong_count: int) -> str:
        """Получить стикер за неправильный ответ"""
        if consecutive_wrong_count == 1:
            return self.get_sticker(StickerType.FIRST_WRONG, user_id)
        else:
            return self.get_sticker(StickerType.SECOND_WRONG, user_id)
    
    def get_lesson_complete_sticker(self, user_id: str) -> str:
        """Получить стикер за завершение урока"""
        return self.get_sticker(StickerType.LESSON_COMPLETE, user_id)
    
    def get_topic_complete_sticker(self, user_id: str) -> str:
        """Получить стикер за завершение темы"""
        return self.get_sticker(StickerType.TOPIC_COMPLETE, user_id)
    
    def get_lesson_failed_sticker(self, user_id: str) -> str:
        """Получить стикер за неуспешное завершение урока"""
        return self.get_sticker(StickerType.LESSON_FAILED, user_id)
    
    def get_adaptive_sticker(self, user_id: str, context: Dict[str, Any]) -> Optional[str]:
        """Получить адаптивный стикер на основе контекста"""
        try:
            score = context.get('score', 0)
            lesson_completed = context.get('lesson_completed', False)
            topic_completed = context.get('topic_completed', False)
            is_correct = context.get('is_correct', False)
            is_first_correct = context.get('is_first_correct', False)
            consecutive_wrong = context.get('consecutive_wrong', 0)
            
            # Приоритет: завершение темы > завершение урока > правильный/неправильный ответ
            if topic_completed:
                return self.get_topic_complete_sticker(user_id)
            elif lesson_completed:
                if score >= 80:  # Успешное завершение
                    return self.get_lesson_complete_sticker(user_id)
                else:  # Неуспешное завершение
                    return self.get_lesson_failed_sticker(user_id)
            elif is_correct:
                return self.get_correct_answer_sticker(user_id, is_first_correct)
            elif consecutive_wrong > 0:
                return self.get_wrong_answer_sticker(user_id, consecutive_wrong)
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения адаптивного стикера: {e}")
            return None
    
    def reset_user_history(self, user_id: str):
        """Сброс истории стикеров пользователя"""
        if user_id in self.user_sticker_history:
            del self.user_sticker_history[user_id]
            logger.info(f"История стикеров пользователя {user_id} сброшена")


# Глобальный экземпляр сервиса
sticker_service = StickerService()