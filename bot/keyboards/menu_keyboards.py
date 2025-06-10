"""
Клавиатуры для меню
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from typing import List, Dict, Any
from config.bot_config import LEARNING_STRUCTURE, TOPIC_ALIASES
import logging

logger = logging.getLogger(__name__)

# --- Вспомогательная функция для создания callback_data ---
def create_callback_data(action: str, **kwargs) -> str:
    """Создает строку callback_data в формате key:value;key2:value2;"""
    parts = [f"action:{action}"]
    for key, value in kwargs.items():
        if value is not None:
            parts.append(f"{key}:{value}")
    return ";".join(parts)

# --- Основные клавиатуры ---

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню бота"""
    keyboard = [
        [KeyboardButton("📚 Обучение")],
        [KeyboardButton("📊 Прогресс"), KeyboardButton("ℹ️ Инструкция")],
        [KeyboardButton("🔄 Сброс прогресса")]
    ]
    return ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=False,
        input_field_placeholder="Выберите действие..."
    )

def get_topics_keyboard(user_progress: Dict[str, Any] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора тем обучения"""
    keyboard = []
    available_topics = _get_available_topics(user_progress)
    
    for topic_id, topic_data in LEARNING_STRUCTURE.items():
        title = topic_data["title"]
        if user_progress and topic_id in user_progress.get("topics_progress", {}):
            topic_progress = user_progress["topics_progress"][topic_id]
            completed = topic_progress.get("completed_lessons", 0)
            total = len(topic_data["lessons"])
            if completed == total:
                title += " ✅"
            elif completed > 0:
                title += f" ({completed}/{total})"

        is_available = topic_id in available_topics
        
        topic_alias = TOPIC_ALIASES.get(topic_id)
        callback_data = create_callback_data("topic", tid=topic_alias) if is_available else "action:topic_locked"

        if not is_available:
            title = f"🔒 {title}"
        
        keyboard.append([InlineKeyboardButton(title, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="action:back_to_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_lesson_start_keyboard(topic_id: str, lesson_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для начала урока"""
    topic_alias = TOPIC_ALIASES.get(topic_id)
    keyboard = [
        [InlineKeyboardButton("🚀 Начать тестирование", callback_data=create_callback_data("start_lesson", tid=topic_alias, lesson_id=lesson_id))],
        [InlineKeyboardButton("📖 Изучить материал", callback_data=create_callback_data("show_material", tid=topic_alias, lesson_id=lesson_id))],
        [InlineKeyboardButton("❓ Задать вопрос AI", callback_data=create_callback_data("ask_ai", tid=topic_alias, lesson_id=lesson_id))],
        [
            InlineKeyboardButton("◀️ К урокам", callback_data=create_callback_data("back_to_lessons", tid=topic_alias)),
            InlineKeyboardButton("🏠 Меню", callback_data="action:back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_quiz_keyboard(options: List[str]) -> InlineKeyboardMarkup:
    """Клавиатура для вопросов тестирования"""
    keyboard = []
    for i, option in enumerate(options):
        button_text = option if len(option) <= 60 else option[:57] + "..."
        keyboard.append([InlineKeyboardButton(button_text, callback_data=create_callback_data("answer", index=i))])
    return InlineKeyboardMarkup(keyboard)

def get_quiz_result_keyboard(topic_id: str, lesson_id: int, passed: bool) -> InlineKeyboardMarkup:
    """Клавиатура результатов тестирования"""
    topic_alias = TOPIC_ALIASES.get(topic_id)
    keyboard = []
    if passed:
        keyboard.append([InlineKeyboardButton("🎉 Продолжить обучение", callback_data=create_callback_data("continue_learning", tid=topic_alias))])
    else:
        keyboard.append([InlineKeyboardButton("🔄 Повторить урок", callback_data=create_callback_data("retry_lesson", tid=topic_alias, lesson_id=lesson_id))])
        keyboard.append([InlineKeyboardButton("📚 Изучить материал", callback_data=create_callback_data("show_material", tid=topic_alias, lesson_id=lesson_id))])
    
    keyboard.append([
        InlineKeyboardButton("◀️ К урокам", callback_data=create_callback_data("back_to_lessons", tid=topic_alias)),
        InlineKeyboardButton("🏠 Главное меню", callback_data="action:back_to_menu")
    ])
    return InlineKeyboardMarkup(keyboard)

def get_progress_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для страницы прогресса"""
    keyboard = [
        [InlineKeyboardButton("🎯 Персональные рекомендации", callback_data="action:ai_recommendations")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="action:back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_ai_help_keyboard(topic_id: str = None, lesson_id: int = None) -> InlineKeyboardMarkup:
    """Клавиатура для помощи AI"""
    keyboard = [
        [InlineKeyboardButton("💡 Объясни основные понятия", callback_data="action:quick_question;type:basics")],
        [InlineKeyboardButton("📖 Примеры из практики", callback_data="action:quick_question;type:examples")],
        [InlineKeyboardButton("✍️ Задать свой вопрос", callback_data="action:ask_custom_question")],
    ]
    if topic_id and lesson_id:
        topic_alias = TOPIC_ALIASES.get(topic_id)
        keyboard.append([InlineKeyboardButton("◀️ К уроку", callback_data=create_callback_data("lesson", tid=topic_alias, lesson_id=lesson_id))])
    else:
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="action:back_to_topics")])
    return InlineKeyboardMarkup(keyboard)

def get_confirmation_keyboard(action_to_confirm: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действий"""
    keyboard = [[
        InlineKeyboardButton("✅ Да, подтверждаю", callback_data=create_callback_data(f"confirm_{action_to_confirm}")),
        InlineKeyboardButton("❌ Отмена", callback_data=create_callback_data(f"cancel_{action_to_confirm}"))
    ]]
    return InlineKeyboardMarkup(keyboard)

def get_lessons_keyboard(topic_id: str, user_progress: Dict[str, Any] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора уроков в теме"""
    keyboard = []
    topic_data = LEARNING_STRUCTURE.get(topic_id)
    if not topic_data:
        return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад к темам", callback_data="action:back_to_topics")]])

    available_lessons = _get_available_lessons(topic_id, user_progress)
    
    logger.info(f"[get_lessons_keyboard] topic_id: {topic_id}")
    logger.info(f"[get_lessons_keyboard] available_lessons: {available_lessons}")
    
    topic_alias = TOPIC_ALIASES.get(topic_id)

    for lesson in topic_data["lessons"]:
        lesson_id = lesson["id"]
        title = f"{lesson_id}. {lesson['title']}"
        
        is_available = lesson_id in available_lessons
        
        if user_progress:
            lesson_status = _get_lesson_status(topic_id, lesson_id, user_progress)
            if lesson_status["is_completed"]:
                title = f"✅ {title}"
            elif lesson_status["attempts"] > 0:
                title = f"🔄 {title}"
        
        callback_data = create_callback_data("lesson", tid=topic_alias, lesson_id=lesson_id) if is_available else "action:lesson_locked"
        if not is_available:
            title = f"🔒 {title}"
        
        logger.info(f"[get_lessons_keyboard] Урок {lesson_id}: доступен={is_available}, callback={callback_data}")
        
        keyboard.append([InlineKeyboardButton(title, callback_data=callback_data)])

    keyboard.append([
        InlineKeyboardButton("◀️ Назад к темам", callback_data="action:back_to_topics"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="action:back_to_menu")
    ])
    return InlineKeyboardMarkup(keyboard)

# --- Вспомогательные функции ---

def _get_available_topics(user_progress: Dict[str, Any] = None) -> List[str]:
    """ИСПРАВЛЕНО: Более мягкая логика разблокировки тем"""
    if not user_progress:
        logger.info("[_get_available_topics] Нет прогресса - доступна только первая тема")
        return ["основы_рисков"]
    
    available_topics = ["основы_рисков"]
    topic_order = list(LEARNING_STRUCTURE.keys())
    
    for i, topic_id in enumerate(topic_order):
        if i == 0: 
            continue
        
        prev_topic_id = topic_order[i-1]
        prev_topic_progress = user_progress.get("topics_progress", {}).get(prev_topic_id)
        
        if prev_topic_progress:
            total_lessons = len(LEARNING_STRUCTURE[prev_topic_id]["lessons"])
            completed_lessons = prev_topic_progress.get("completed_lessons", 0)
            
            # ИСПРАВЛЕНО: Разблокируем следующую тему после завершения 2-х уроков из 3-х
            required_lessons = min(2, total_lessons)  # Требуем минимум 2 урока или все если их меньше 2
            
            if completed_lessons >= required_lessons:
                available_topics.append(topic_id)
                logger.info(f"[_get_available_topics] Тема {topic_id} разблокирована: завершено {completed_lessons}/{total_lessons} уроков")
            else:
                logger.info(f"[_get_available_topics] Тема {topic_id} заблокирована: завершено только {completed_lessons}/{total_lessons} уроков")
                break
        else:
            logger.info(f"[_get_available_topics] Тема {topic_id} заблокирована: нет прогресса по предыдущей теме")
            break
    
    logger.info(f"[_get_available_topics] Доступные темы: {available_topics}")
    return available_topics

def _get_available_lessons(topic_id: str, user_progress: Dict[str, Any] = None) -> List[int]:
    """ИСПРАВЛЕНО: Правильная логика разблокировки уроков"""
    logger.info(f"[_get_available_lessons] Начало для темы {topic_id}")
    
    if not user_progress: 
        logger.info(f"[_get_available_lessons] Нет прогресса - доступен только урок 1")
        return [1]
    
    topic_progress = user_progress.get("topics_progress", {}).get(topic_id)
    if not topic_progress: 
        logger.info(f"[_get_available_lessons] Нет прогресса по теме - доступен только урок 1")
        return [1]
    
    lessons_data = topic_progress.get("lessons", {})
    logger.info(f"[_get_available_lessons] lessons_data: {lessons_data}")
    
    available = [1]  # Первый урок всегда доступен
    total_lessons = len(LEARNING_STRUCTURE[topic_id]["lessons"])
    logger.info(f"[_get_available_lessons] total_lessons: {total_lessons}")

    # ИСПРАВЛЕНО: Проверяем каждый урок по порядку и используем правильные ключи
    for lesson_id in range(1, total_lessons + 1):
        # ВАЖНО: Используем lesson_id как ключ напрямую (число), а не строку
        lesson_data = lessons_data.get(lesson_id)  # Без str()!
        logger.info(f"[_get_available_lessons] Проверяем урок {lesson_id}: {lesson_data}")
        
        if lesson_data and lesson_data.get("is_completed"):
            next_lesson = lesson_id + 1
            if next_lesson <= total_lessons and next_lesson not in available:
                available.append(next_lesson)
                logger.info(f"[_get_available_lessons] ✅ Урок {next_lesson} разблокирован после завершения урока {lesson_id}")
    
    logger.info(f"[_get_available_lessons] ✅ Итоговый результат: {available}")
    return available

def _get_lesson_status(topic_id: str, lesson_id: int, user_progress: Dict[str, Any]) -> Dict[str, Any]:
    """Получение статуса конкретного урока"""
    default_status = {"is_completed": False, "attempts": 0, "best_score": 0}
    
    try:
        topics_progress = user_progress.get("topics_progress", {})
        topic_progress = topics_progress.get(topic_id, {})
        lessons_progress = topic_progress.get("lessons", {})
        # ВАЖНО: Используем lesson_id как число, НЕ как строку
        lesson_data = lessons_progress.get(lesson_id)  # Без str()!
        
        if lesson_data:
            return {
                "is_completed": lesson_data.get("is_completed", False),
                "attempts": lesson_data.get("attempts", 0),
                "best_score": lesson_data.get("best_score", 0)
            }
        else:
            return default_status
            
    except (KeyError, AttributeError) as e:
        logger.warning(f"Ошибка получения статуса урока {lesson_id} темы {topic_id}: {e}")
        return default_status