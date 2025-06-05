"""
Клавиатуры для меню
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from typing import List, Dict, Any
from config.bot_config import MENU_BUTTONS, LEARNING_STRUCTURE


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню бота"""
    keyboard = [
        [KeyboardButton("📚 Обучение")],
        [
            KeyboardButton("📊 Прогресс"),
            KeyboardButton("ℹ️ Инструкция")
        ],
        [KeyboardButton("🔄 Сброс прогресса")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите действие..."
    )


def get_topics_keyboard(user_progress: Dict[str, Any] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора тем обучения"""
    keyboard = []
    
    # Определяем доступные темы на основе прогресса
    available_topics = _get_available_topics(user_progress)
    
    for topic_id, topic_data in LEARNING_STRUCTURE.items():
        title = topic_data["title"]
        
        # Добавляем индикаторы прогресса
        if user_progress and topic_id in user_progress.get("topics_progress", {}):
            topic_progress = user_progress["topics_progress"][topic_id]
            completed_lessons = topic_progress.get("completed_lessons", 0)
            total_lessons = len(topic_data["lessons"])
            
            if completed_lessons == total_lessons:
                title += " ✅"
            elif completed_lessons > 0:
                title += f" ({completed_lessons}/{total_lessons})"
        
        # Проверяем доступность темы
        is_available = topic_id in available_topics
        callback_data = f"topic_{topic_id}" if is_available else "topic_locked"
        
        if not is_available:
            title += " 🔒"
        
        keyboard.append([
            InlineKeyboardButton(title, callback_data=callback_data)
        ])
    
    # Кнопка возврата
    keyboard.append([
        InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_lesson_start_keyboard(topic_id: str, lesson_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для начала урока"""
    keyboard = [
        [InlineKeyboardButton("🚀 Начать урок", callback_data=f"start_lesson_{topic_id}_{lesson_id}")],
        [InlineKeyboardButton("❓ Задать вопрос AI", callback_data=f"ask_ai_{topic_id}_{lesson_id}")],
        [
            InlineKeyboardButton("◀️ Назад", callback_data=f"back_to_lessons_{topic_id}"),
            InlineKeyboardButton("🏠 Меню", callback_data="back_to_menu")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def get_quiz_keyboard(question_num: int, total_questions: int, options: List[str]) -> InlineKeyboardMarkup:
    """Клавиатура для вопросов тестирования"""
    keyboard = []
    
    # Варианты ответов
    for i, option in enumerate(options):
        # Ограничиваем длину текста кнопки
        button_text = option if len(option) <= 50 else option[:47] + "..."
        keyboard.append([
            InlineKeyboardButton(f"{chr(65+i)}. {button_text}", callback_data=f"answer_{i}")
        ])
    
    # Информация о прогрессе и кнопка помощи
    progress_text = f"Вопрос {question_num}/{total_questions}"
    keyboard.append([
        InlineKeyboardButton(f"📊 {progress_text}", callback_data="quiz_progress"),
        InlineKeyboardButton("❓ Помощь", callback_data="quiz_help")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_quiz_result_keyboard(topic_id: str, lesson_id: int, passed: bool) -> InlineKeyboardMarkup:
    """Клавиатура результатов тестирования"""
    keyboard = []
    
    if passed:
        # Если урок пройден успешно
        keyboard.append([
            InlineKeyboardButton("🎉 Продолжить обучение", callback_data=f"continue_learning_{topic_id}")
        ])
    else:
        # Если урок не пройден
        keyboard.append([
            InlineKeyboardButton("🔄 Повторить урок", callback_data=f"retry_lesson_{topic_id}_{lesson_id}"),
            InlineKeyboardButton("📚 Изучить материал", callback_data=f"study_material_{topic_id}_{lesson_id}")
        ])
    
    # Общие кнопки
    keyboard.append([
        InlineKeyboardButton("❓ Задать вопрос AI", callback_data=f"ask_ai_{topic_id}_{lesson_id}")
    ])
    
    keyboard.append([
        InlineKeyboardButton("◀️ К урокам", callback_data=f"back_to_lessons_{topic_id}"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_progress_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для страницы прогресса"""
    keyboard = [
        [
            InlineKeyboardButton("📈 Детальная статистика", callback_data="detailed_stats"),
            InlineKeyboardButton("🎯 Рекомендации", callback_data="ai_recommendations")
        ],
        [InlineKeyboardButton("◀️ Главное меню", callback_data="back_to_menu")]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def get_ai_help_keyboard(topic_id: str = None, lesson_id: int = None) -> InlineKeyboardMarkup:
    """Клавиатура для помощи AI"""
    keyboard = []
    
    # Быстрые вопросы
    quick_questions = [
        ("💡 Объясни основные понятия", "quick_explain_basics"),
        ("📖 Примеры из практики", "quick_examples"),
        ("❓ Часто задаваемые вопросы", "quick_faq"),
    ]
    
    for text, callback in quick_questions:
        keyboard.append([InlineKeyboardButton(text, callback_data=callback)])
    
    # Кнопка для свободного вопроса
    keyboard.append([
        InlineKeyboardButton("✍️ Задать свой вопрос", callback_data="ask_custom_question")
    ])
    
    # Навигация
    if topic_id and lesson_id:
        keyboard.append([
            InlineKeyboardButton("◀️ К уроку", callback_data=f"back_to_lesson_{topic_id}_{lesson_id}")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")
        ])
    
    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard(action: str, **kwargs) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действий"""
    if action == "reset_progress":
        keyboard = [
            [
                InlineKeyboardButton("✅ Да, сбросить", callback_data="confirm_reset"),
                InlineKeyboardButton("❌ Отмена", callback_data="cancel_reset")
            ]
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{action}"),
                InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_{action}")
            ]
        ]
    
    return InlineKeyboardMarkup(keyboard)


# Вспомогательные функции

def _get_available_topics(user_progress: Dict[str, Any] = None) -> List[str]:
    """Определение доступных тем на основе прогресса"""
    if not user_progress:
        return ["основы_рисков"]  # Только первая тема доступна
    
    available_topics = ["основы_рисков"]
    topics_progress = user_progress.get("topics_progress", {})
    
    # Логика последовательного открытия тем
    topic_order = ["основы_рисков", "критичность_процессов", "оценка_рисков"]
    
    for i, topic_id in enumerate(topic_order):
        if i == 0:
            continue  # Первая тема всегда доступна
        
        # Проверяем, завершена ли предыдущая тема
        prev_topic = topic_order[i - 1]
        if prev_topic in topics_progress:
            prev_topic_data = topics_progress[prev_topic]
            total_lessons = len(LEARNING_STRUCTURE[prev_topic]["lessons"])
            completed_lessons = prev_topic_data.get("completed_lessons", 0)
            
            if completed_lessons >= total_lessons:
                available_topics.append(topic_id)
            else:
                break  # Если предыдущая тема не завершена, останавливаемся
        else:
            break
    
    return available_topics


def _get_available_lessons(topic_id: str, user_progress: Dict[str, Any] = None) -> List[int]:
    """Определение доступных уроков в теме"""
    if not user_progress:
        return [1]  # Только первый урок доступен
    
    topics_progress = user_progress.get("topics_progress", {})
    
    if topic_id not in topics_progress:
        return [1]  # Если тема не начата, доступен только первый урок
    
    topic_progress = topics_progress[topic_id]
    lessons_data = topic_progress.get("lessons", {})
    
    available_lessons = [1]  # Первый урок всегда доступен
    
    # Последовательно проверяем завершенность уроков
    total_lessons = len(LEARNING_STRUCTURE[topic_id]["lessons"])
    
    for lesson_id in range(1, total_lessons + 1):
        if str(lesson_id) in lessons_data:
            lesson_data = lessons_data[str(lesson_id)]
            if lesson_data.get("is_completed", False):
                # Если урок завершен, следующий становится доступным
                next_lesson = lesson_id + 1
                if next_lesson <= total_lessons and next_lesson not in available_lessons:
                    available_lessons.append(next_lesson)
        else:
            break  # Если урок не начат, останавливаемся
    
    return available_lessons


def _get_lesson_status(topic_id: str, lesson_id: int, user_progress: Dict[str, Any]) -> Dict[str, Any]:
    """Получение статуса урока"""
    topics_progress = user_progress.get("topics_progress", {})
    
    if topic_id not in topics_progress:
        return {"is_completed": False, "attempts": 0, "best_score": 0}
    
    lessons_data = topics_progress[topic_id].get("lessons", {})
    lesson_key = str(lesson_id)
    
    if lesson_key not in lessons_data:
        return {"is_completed": False, "attempts": 0, "best_score": 0}
    
    return lessons_data[lesson_key]


def get_lessons_keyboard(topic_id: str, user_progress: Dict[str, Any] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора уроков в теме"""
    keyboard = []
    
    if topic_id not in LEARNING_STRUCTURE:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад к темам", callback_data="back_to_topics")]
        ])
    
    topic_data = LEARNING_STRUCTURE[topic_id]
    available_lessons = _get_available_lessons(topic_id, user_progress)
    
    # Логгирование для отладки
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Доступные уроки для темы {topic_id}: {available_lessons}")
    logger.info(f"Прогресс пользователя: {user_progress}")
    
    for lesson in topic_data["lessons"]:
        lesson_id = lesson["id"]
        title = f"{lesson_id}. {lesson['title']}"
        
        # Добавляем индикаторы статуса
        if user_progress:
            lesson_progress = _get_lesson_status(topic_id, lesson_id, user_progress)
            if lesson_progress["is_completed"]:
                title += " ✅"
                score = lesson_progress.get("best_score", 0)
                title += f" ({score:.0f}%)"
            elif lesson_progress["attempts"] > 0:
                title += " 🔄"
        
        # Проверяем доступность урока
        is_available = lesson_id in available_lessons
        callback_data = f"start_lesson_{topic_id}_{lesson_id}" if is_available else "lesson_locked"
        
        if not is_available:
            title += " 🔒"
        
        keyboard.append([
            InlineKeyboardButton(title, callback_data=callback_data)
        ])
    
    # Кнопки навигации
    keyboard.append([
        InlineKeyboardButton("◀️ Назад к темам", callback_data="back_to_topics"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)
