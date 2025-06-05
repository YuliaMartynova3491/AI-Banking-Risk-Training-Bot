"""
Специализированные клавиатуры для уроков и обучения
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Any, Optional

from core.enums import LessonStatus, TopicStatus
from config.bot_config import LEARNING_STRUCTURE


def get_adaptive_lesson_keyboard(topic_id: str, lesson_id: int, 
                                user_performance: Dict[str, Any] = None,
                                ai_suggestions: List[str] = None) -> InlineKeyboardMarkup:
    """Адаптивная клавиатура урока на основе успеваемости пользователя"""
    keyboard = []
    
    # Основные действия урока
    keyboard.append([
        InlineKeyboardButton("🚀 Начать урок", callback_data=f"start_lesson_{topic_id}_{lesson_id}")
    ])
    
    # Адаптивные опции на основе успеваемости
    if user_performance:
        avg_score = user_performance.get("average_score", 0)
        attempts = user_performance.get("attempts", 0)
        
        # Если низкая успеваемость - предлагаем дополнительную помощь
        if avg_score < 70 and attempts > 0:
            keyboard.append([
                InlineKeyboardButton("📚 Повторить теорию", callback_data=f"review_theory_{topic_id}_{lesson_id}"),
                InlineKeyboardButton("💡 Получить подсказки", callback_data=f"get_hints_{topic_id}_{lesson_id}")
            ])
        
        # Если высокая успеваемость - предлагаем усложненные задания
        elif avg_score >= 90:
            keyboard.append([
                InlineKeyboardButton("⚡ Сложный режим", callback_data=f"hard_mode_{topic_id}_{lesson_id}"),
                InlineKeyboardButton("🎯 Дополнительные вопросы", callback_data=f"extra_questions_{topic_id}_{lesson_id}")
            ])
    
    # AI-помощник всегда доступен
    keyboard.append([
        InlineKeyboardButton("🤖 AI-помощник", callback_data=f"ask_ai_{topic_id}_{lesson_id}")
    ])
    
    # Навигация
    keyboard.append([
        InlineKeyboardButton("◀️ К урокам", callback_data=f"back_to_lessons_{topic_id}"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_study_material_keyboard(topic_id: str, lesson_id: int, 
                               material_sections: List[Dict[str, str]] = None) -> InlineKeyboardMarkup:
    """Клавиатура для изучения теоретического материала"""
    keyboard = []
    
    # Разделы материала
    if material_sections:
        for i, section in enumerate(material_sections):
            keyboard.append([
                InlineKeyboardButton(
                    f"📖 {section['title']}", 
                    callback_data=f"study_section_{topic_id}_{lesson_id}_{i}"
                )
            ])
    else:
        # Стандартные разделы
        keyboard.append([
            InlineKeyboardButton("📋 Основные понятия", callback_data=f"study_concepts_{topic_id}_{lesson_id}"),
            InlineKeyboardButton("🔍 Примеры", callback_data=f"study_examples_{topic_id}_{lesson_id}")
        ])
        keyboard.append([
            InlineKeyboardButton("⚙️ Практическое применение", callback_data=f"study_practice_{topic_id}_{lesson_id}"),
            InlineKeyboardButton("📊 Схемы и процессы", callback_data=f"study_schemes_{topic_id}_{lesson_id}")
        ])
    
    # Интерактивные элементы
    keyboard.append([
        InlineKeyboardButton("❓ Задать вопрос", callback_data=f"ask_question_{topic_id}_{lesson_id}"),
        InlineKeyboardButton("🔖 Сохранить заметку", callback_data=f"save_note_{topic_id}_{lesson_id}")
    ])
    
    # Переход к тестированию
    keyboard.append([
        InlineKeyboardButton("✅ Готов к тестированию", callback_data=f"ready_for_quiz_{topic_id}_{lesson_id}")
    ])
    
    # Навигация
    keyboard.append([
        InlineKeyboardButton("◀️ К уроку", callback_data=f"back_to_lesson_{topic_id}_{lesson_id}"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_quiz_settings_keyboard(topic_id: str, lesson_id: int, 
                              available_difficulties: List[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура настроек тестирования"""
    keyboard = []
    
    # Выбор уровня сложности
    if available_difficulties:
        keyboard.append([InlineKeyboardButton("⚙️ Настройки сложности", callback_data="quiz_settings_header")])
        
        difficulty_buttons = []
        for difficulty in available_difficulties:
            difficulty_names = {
                "beginner": "🟢 Базовый",
                "intermediate": "🟡 Средний", 
                "advanced": "🔴 Сложный"
            }
            button_text = difficulty_names.get(difficulty, difficulty)
            difficulty_buttons.append(
                InlineKeyboardButton(button_text, callback_data=f"set_difficulty_{difficulty}_{topic_id}_{lesson_id}")
            )
        
        # Размещаем кнопки сложности в ряды по 2
        for i in range(0, len(difficulty_buttons), 2):
            keyboard.append(difficulty_buttons[i:i+2])
    
    # Количество вопросов
    keyboard.append([InlineKeyboardButton("📊 Количество вопросов", callback_data="question_count_header")])
    keyboard.append([
        InlineKeyboardButton("3 вопроса", callback_data=f"set_count_3_{topic_id}_{lesson_id}"),
        InlineKeyboardButton("5 вопросов", callback_data=f"set_count_5_{topic_id}_{lesson_id}"),
        InlineKeyboardButton("10 вопросов", callback_data=f"set_count_10_{topic_id}_{lesson_id}")
    ])
    
    # Дополнительные опции
    keyboard.append([
        InlineKeyboardButton("💡 Подсказки включены", callback_data=f"toggle_hints_{topic_id}_{lesson_id}"),
        InlineKeyboardButton("⏱️ Ограничение времени", callback_data=f"toggle_timer_{topic_id}_{lesson_id}")
    ])
    
    # Запуск тестирования
    keyboard.append([
        InlineKeyboardButton("🚀 Начать тестирование", callback_data=f"start_configured_quiz_{topic_id}_{lesson_id}")
    ])
    
    # Навигация
    keyboard.append([
        InlineKeyboardButton("◀️ К уроку", callback_data=f"back_to_lesson_{topic_id}_{lesson_id}")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_lesson_completion_keyboard(topic_id: str, lesson_id: int, 
                                 next_lesson_available: bool = False,
                                 topic_completed: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура после завершения урока"""
    keyboard = []
    
    # Отзыв об уроке
    keyboard.append([
        InlineKeyboardButton("⭐ Оценить урок", callback_data=f"rate_lesson_{topic_id}_{lesson_id}")
    ])
    
    # Дальнейшие действия
    if topic_completed:
        keyboard.append([
            InlineKeyboardButton("🎉 К следующей теме", callback_data="next_topic"),
            InlineKeyboardButton("📜 Получить сертификат", callback_data=f"get_certificate_{topic_id}")
        ])
    elif next_lesson_available:
        keyboard.append([
            InlineKeyboardButton("▶️ Следующий урок", callback_data=f"next_lesson_{topic_id}"),
            InlineKeyboardButton("🔄 Повторить урок", callback_data=f"repeat_lesson_{topic_id}_{lesson_id}")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("🔄 Повторить урок", callback_data=f"repeat_lesson_{topic_id}_{lesson_id}"),
            InlineKeyboardButton("📚 К урокам темы", callback_data=f"back_to_lessons_{topic_id}")
        ])
    
    # Дополнительные материалы
    keyboard.append([
        InlineKeyboardButton("📖 Доп. материалы", callback_data=f"extra_materials_{topic_id}_{lesson_id}"),
        InlineKeyboardButton("🤖 Обсудить с AI", callback_data=f"discuss_with_ai_{topic_id}_{lesson_id}")
    ])
    
    # Навигация
    keyboard.append([
        InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_ai_interaction_keyboard(context: str, topic_id: str = None, lesson_id: int = None) -> InlineKeyboardMarkup:
    """Клавиатура для взаимодействия с AI в контексте урока"""
    keyboard = []
    
    # Быстрые действия с AI
    if context == "lesson_help":
        keyboard.append([
            InlineKeyboardButton("💡 Объясни простыми словами", callback_data=f"ai_explain_simple_{topic_id}_{lesson_id}"),
            InlineKeyboardButton("🔍 Приведи примеры", callback_data=f"ai_give_examples_{topic_id}_{lesson_id}")
        ])
        keyboard.append([
            InlineKeyboardButton("🎯 Как это применить?", callback_data=f"ai_practical_use_{topic_id}_{lesson_id}"),
            InlineKeyboardButton("🔗 Связь с другими темами", callback_data=f"ai_connections_{topic_id}_{lesson_id}")
        ])
    
    elif context == "quiz_help":
        keyboard.append([
            InlineKeyboardButton("💭 Подсказка к вопросу", callback_data=f"ai_quiz_hint_{topic_id}_{lesson_id}"),
            InlineKeyboardButton("📚 Повторить теорию", callback_data=f"ai_review_theory_{topic_id}_{lesson_id}")
        ])
    
    elif context == "general_help":
        keyboard.append([
            InlineKeyboardButton("❓ Общие вопросы", callback_data="ai_general_help"),
            InlineKeyboardButton("📊 Анализ прогресса", callback_data="ai_progress_analysis")
        ])
    
    # Ввод собственного вопроса
    keyboard.append([
        InlineKeyboardButton("✍️ Задать свой вопрос", callback_data=f"ai_custom_question_{context}")
    ])
    
    # Закрытие помощи
    if topic_id and lesson_id:
        keyboard.append([
            InlineKeyboardButton("◀️ К уроку", callback_data=f"back_to_lesson_{topic_id}_{lesson_id}")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")
        ])
    
    return InlineKeyboardMarkup(keyboard)


def get_learning_tools_keyboard(topic_id: str, lesson_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с инструментами обучения"""
    keyboard = []
    
    # Инструменты запоминания
    keyboard.append([
        InlineKeyboardButton("🎴 Карточки для запоминания", callback_data=f"flashcards_{topic_id}_{lesson_id}"),
        InlineKeyboardButton("🧩 Интерактивные схемы", callback_data=f"interactive_schemes_{topic_id}_{lesson_id}")
    ])
    
    # Практические инструменты
    keyboard.append([
        InlineKeyboardButton("📝 Конспект урока", callback_data=f"lesson_summary_{topic_id}_{lesson_id}"),
        InlineKeyboardButton("🎯 Ключевые моменты", callback_data=f"key_points_{topic_id}_{lesson_id}")
    ])
    
    # Самопроверка
    keyboard.append([
        InlineKeyboardButton("✅ Самопроверка", callback_data=f"self_check_{topic_id}_{lesson_id}"),
        InlineKeyboardButton("🔄 Быстрый повтор", callback_data=f"quick_review_{topic_id}_{lesson_id}")
    ])
    
    # Навигация
    keyboard.append([
        InlineKeyboardButton("◀️ К уроку", callback_data=f"back_to_lesson_{topic_id}_{lesson_id}")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_progress_visualization_keyboard(user_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для визуализации прогресса"""
    keyboard = []
    
    # Типы визуализации
    keyboard.append([
        InlineKeyboardButton("📊 График прогресса", callback_data=f"progress_chart_{user_id}"),
        InlineKeyboardButton("🎯 Карта навыков", callback_data=f"skills_map_{user_id}")
    ])
    
    keyboard.append([
        InlineKeyboardButton("📈 Статистика по темам", callback_data=f"topic_stats_{user_id}"),
        InlineKeyboardButton("⏱️ Время обучения", callback_data=f"time_stats_{user_id}")
    ])
    
    # Сравнения и аналитика
    keyboard.append([
        InlineKeyboardButton("🏆 Достижения", callback_data=f"achievements_{user_id}"),
        InlineKeyboardButton("📊 Сравнить с другими", callback_data=f"compare_progress_{user_id}")
    ])
    
    # AI-анализ
    keyboard.append([
        InlineKeyboardButton("🤖 AI-анализ прогресса", callback_data=f"ai_progress_analysis_{user_id}")
    ])
    
    # Навигация
    keyboard.append([
        InlineKeyboardButton("◀️ К прогрессу", callback_data="back_to_progress")
    ])
    
    return InlineKeyboardMarkup(keyboard)


# Вспомогательные функции

def add_lesson_status_indicators(buttons: List[InlineKeyboardButton], 
                                lesson_status: Dict[int, str]) -> List[InlineKeyboardButton]:
    """Добавить индикаторы статуса к кнопкам уроков"""
    status_emojis = {
        LessonStatus.COMPLETED.value: "✅",
        LessonStatus.IN_PROGRESS.value: "🔄", 
        LessonStatus.AVAILABLE.value: "📝",
        LessonStatus.LOCKED.value: "🔒",
        LessonStatus.FAILED.value: "❌"
    }
    
    updated_buttons = []
    for button in buttons:
        # Извлекаем lesson_id из callback_data
        if "lesson_" in button.callback_data:
            try:
                lesson_id = int(button.callback_data.split("_")[-1])
                status = lesson_status.get(lesson_id, LessonStatus.AVAILABLE.value)
                emoji = status_emojis.get(status, "📝")
                
                # Добавляем эмодзи к тексту
                new_text = f"{emoji} {button.text}"
                updated_buttons.append(
                    InlineKeyboardButton(new_text, callback_data=button.callback_data)
                )
            except (ValueError, IndexError):
                updated_buttons.append(button)
        else:
            updated_buttons.append(button)
    
    return updated_buttons


def create_adaptive_navigation(current_topic: str, current_lesson: int, 
                             user_progress: Dict[str, Any]) -> List[List[InlineKeyboardButton]]:
    """Создать адаптивную навигацию на основе прогресса пользователя"""
    navigation = []
    