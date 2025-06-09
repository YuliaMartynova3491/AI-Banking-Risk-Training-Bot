"""
Клавиатуры для меню - ИСПРАВЛЕННАЯ ВЕРСИЯ
- Используется надежный формат callback_data "key:value;"
- Вместо полного topic_id используется короткий алиас для экономии места
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from typing import List, Dict, Any
from config.bot_config import LEARNING_STRUCTURE, TOPIC_ALIASES  # ИЗМЕНЕНО: Импортируем TOPIC_ALIASES
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
        
        # ИЗМЕНЕНО: Используем короткий алиас `tid` вместо `topic_id`
        topic_alias = TOPIC_ALIASES.get(topic_id)
        callback_data = create_callback_data("topic", tid=topic_alias) if is_available else "action:topic_locked"

        if not is_available:
            title = f"🔒 {title}"
        
        keyboard.append([InlineKeyboardButton(title, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="action:back_to_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_lesson_start_keyboard(topic_id: str, lesson_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для начала урока"""
    # ИЗМЕНЕНО: Используем короткий алиас `tid`
    topic_alias = TOPIC_ALIASES.get(topic_id)
    keyboard = [
        [InlineKeyboardButton("🚀 Начать урок", callback_data=create_callback_data("start_lesson", tid=topic_alias, lesson_id=lesson_id))],
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
    
    # Заглушка, можно будет реализовать помощь по конкретному вопросу
    # keyboard.append([InlineKeyboardButton("❓ Помощь AI", callback_data="action:quiz_help")])
    return InlineKeyboardMarkup(keyboard)

def get_quiz_result_keyboard(topic_id: str, lesson_id: int, passed: bool) -> InlineKeyboardMarkup:
    """Клавиатура результатов тестирования"""
    # ИЗМЕНЕНО: Используем короткий алиас `tid`
    topic_alias = TOPIC_ALIASES.get(topic_id)
    keyboard = []
    if passed:
        keyboard.append([InlineKeyboardButton("🎉 Продолжить обучение", callback_data=create_callback_data("continue_learning", tid=topic_alias))])
    else:
        keyboard.append([InlineKeyboardButton("🔄 Повторить урок", callback_data=create_callback_data("retry_lesson", tid=topic_alias, lesson_id=lesson_id))])
        keyboard.append([InlineKeyboardButton("📚 Изучить материал", callback_data=create_callback_data("study_material", tid=topic_alias, lesson_id=lesson_id))])
    
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
        # ИЗМЕНЕНО: Используем короткий алиас `tid`
        topic_alias = TOPIC_ALIASES.get(topic_id)
        keyboard.append([InlineKeyboardButton("◀️ К уроку", callback_data=create_callback_data("lesson", tid=topic_alias, lesson_id=lesson_id))])
    else:
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="action:back_to_topics")])
    return InlineKeyboardMarkup(keyboard)

def get_confirmation_keyboard(action_to_confirm: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действий (например, сброс)"""
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
    
    # ИЗМЕНЕНО: Используем короткий алиас `tid`
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
        
        keyboard.append([InlineKeyboardButton(title, callback_data=callback_data)])

    keyboard.append([
        InlineKeyboardButton("◀️ Назад к темам", callback_data="action:back_to_topics"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="action:back_to_menu")
    ])
    return InlineKeyboardMarkup(keyboard)

# --- Вспомогательные функции для клавиатур (без изменений) ---

def _get_available_topics(user_progress: Dict[str, Any] = None) -> List[str]:
    """Определение доступных тем на основе прогресса"""
    if not user_progress:
        return ["основы_рисков"]
    
    available_topics = ["основы_рисков"]
    topic_order = list(LEARNING_STRUCTURE.keys())
    
    for i, topic_id in enumerate(topic_order):
        if i == 0: continue
        
        prev_topic_id = topic_order[i-1]
        prev_topic_progress = user_progress.get("topics_progress", {}).get(prev_topic_id)
        if prev_topic_progress:
            total_lessons = len(LEARNING_STRUCTURE[prev_topic_id]["lessons"])
            completed_lessons = prev_topic_progress.get("completed_lessons", 0)
            if completed_lessons >= total_lessons:
                available_topics.append(topic_id)
            else:
                break
        else:
            break
    return available_topics

def _get_available_lessons(topic_id: str, user_progress: Dict[str, Any] = None) -> List[int]:
    """Определение доступных уроков в теме"""
    if not user_progress: return [1]
    
    topic_progress = user_progress.get("topics_progress", {}).get(topic_id)
    if not topic_progress: return [1]
    
    lessons_data = topic_progress.get("lessons", {})
    available = [1]
    total_lessons = len(LEARNING_STRUCTURE[topic_id]["lessons"])

    for i in range(1, total_lessons + 1):
        lesson_data = lessons_data.get(str(i)) # Ключи в JSON могут быть строками
        if lesson_data and lesson_data.get("is_completed"):
            next_lesson = i + 1
            if next_lesson <= total_lessons and next_lesson not in available:
                available.append(next_lesson)
    return available

def _get_lesson_status(topic_id: str, lesson_id: int, user_progress: Dict[str, Any]) -> Dict[str, Any]:
    """Получение статуса конкретного урока"""
    default_status = {"is_completed": False, "attempts": 0, "best_score": 0}
    lesson_data = user_progress.get("topics_progress", {}).get(topic_id, {}).get("lessons", {}).get(str(lesson_id))
    return lesson_data or default_status