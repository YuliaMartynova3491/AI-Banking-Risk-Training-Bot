"""
Обработчик уроков и обучающего контента
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters

from core.database import db_service
from config.bot_config import LEARNING_STRUCTURE, MESSAGES
from bot.keyboards.menu_keyboards import (
    get_lesson_start_keyboard, get_lessons_keyboard, get_ai_help_keyboard
)
from ai_agent.agent_graph import learning_agent
from services.sticker_service import sticker_service

logger = logging.getLogger(__name__)


async def handle_lesson_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора урока"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    try:
        await query.answer()
        
        if data == "lesson_locked":
            await query.edit_message_text(
                "🔒 Этот урок пока недоступен. Завершите предыдущие уроки для разблокировки.",
                reply_markup=query.message.reply_markup
            )
            return
        
        # Парсим данные callback
        _, topic_id, lesson_id = data.split("_", 2)
        lesson_id = int(lesson_id)
        
        if topic_id not in LEARNING_STRUCTURE:
            await query.edit_message_text(
                "Тема не найдена.",
                reply_markup=get_lessons_keyboard(topic_id)
            )
            return
        
        # Получаем информацию об уроке
        topic_data = LEARNING_STRUCTURE[topic_id]
        lesson_data = None
        
        for lesson in topic_data["lessons"]:
            if lesson["id"] == lesson_id:
                lesson_data = lesson
                break
        
        if not lesson_data:
            await query.edit_message_text(
                "Урок не найден.",
                reply_markup=get_lessons_keyboard(topic_id)
            )
            return
        
        # Получаем прогресс урока
        lesson_progress = db_service.get_lesson_progress(user_id, topic_id, lesson_id)
        
        # Формируем текст урока
        text = MESSAGES["lesson_intro"].format(
            lesson_title=lesson_data["title"],
            lesson_description=lesson_data["description"],
            keywords=", ".join(lesson_data["keywords"])
        )
        
        # Добавляем информацию о прогрессе если есть
        if lesson_progress and lesson_progress.attempts > 0:
            if lesson_progress.is_completed:
                text += f"\n✅ Урок завершен с результатом {lesson_progress.best_score:.0f}%"
            else:
                text += f"\n🔄 Попыток пройдено: {lesson_progress.attempts}"
                if lesson_progress.last_attempt_score > 0:
                    text += f" (лучший результат: {lesson_progress.best_score:.0f}%)"
        
        # Проверяем, отличается ли новое сообщение от текущего
        current_text = query.message.text if query.message.text else ""
        new_keyboard = get_lesson_start_keyboard(topic_id, lesson_id)
        
        if text != current_text:
            await query.edit_message_text(
                text,
                reply_markup=new_keyboard
            )
        else:
            # Если текст тот же, обновляем только клавиатуру
            await query.edit_message_reply_markup(reply_markup=new_keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка в handle_lesson_selection: {e}")
        try:
            await query.edit_message_text(
                "Ошибка загрузки урока. Попробуйте еще раз.",
                reply_markup=get_lessons_keyboard("основы_рисков")
            )
        except Exception:
            # Если не удалось отредактировать, отправляем новое сообщение
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Ошибка загрузки урока. Попробуйте еще раз.",
                reply_markup=get_lessons_keyboard("основы_рисков")
            )


async def handle_lesson_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка начала урока (переход к тестированию)"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    try:
        await query.answer()
        
        # Парсим данные
        _, _, topic_id, lesson_id = data.split("_", 3)
        lesson_id = int(lesson_id)
        
        # Создаем или получаем прогресс урока
        lesson_progress = db_service.get_or_create_lesson_progress(user_id, topic_id, lesson_id)
        
        # Переходим к тестированию
        from bot.handlers.quiz_handler import start_quiz
        await start_quiz(query, context, topic_id, lesson_id)
        
    except Exception as e:
        logger.error(f"Ошибка в handle_lesson_start: {e}")
        await query.edit_message_text(
            "Ошибка запуска урока.",
            reply_markup=get_lesson_start_keyboard(topic_id, lesson_id)
        )


async def handle_ask_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка запроса помощи у AI"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    try:
        await query.answer()
        
        # Парсим данные
        parts = data.split("_")
        if len(parts) >= 4:  # ask_ai_topic_lesson
            topic_id = parts[2]
            lesson_id = int(parts[3])
        else:
            topic_id = None
            lesson_id = None
        
        text = "🤖 AI-помощник готов ответить на ваши вопросы!\n\n"
        text += "Выберите тип вопроса или задайте свой:"
        
        await query.edit_message_text(
            text,
            reply_markup=get_ai_help_keyboard(topic_id, lesson_id)
        )
        
    except Exception as e:
        logger.error(f"Ошибка в handle_ask_ai: {e}")
        await query.edit_message_text(
            "Ошибка обращения к AI-помощнику.",
            reply_markup=get_ai_help_keyboard()
        )


async def handle_quick_ai_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка быстрых вопросов к AI"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    try:
        await query.answer("Обрабатываю ваш запрос...")
        
        # Определяем тип быстрого вопроса
        if data == "quick_explain_basics":
            question = "Объясни основные понятия риска нарушения непрерывности деятельности банка"
        elif data == "quick_examples":
            question = "Приведи примеры из банковской практики управления рисками непрерывности"
        elif data == "quick_faq":
            question = "Какие часто задаваемые вопросы есть по теме рисков непрерывности?"
        else:
            await query.edit_message_text(
                "Неизвестный тип вопроса.",
                reply_markup=get_ai_help_keyboard()
            )
            return
        
        # Показываем индикатор обработки
        await query.edit_message_text(
            "🤔 AI обрабатывает ваш вопрос...\nПожалуйста, подождите."
        )
        
        # Получаем ответ от AI
        response = learning_agent.provide_learning_assistance(
            user_id=user_id,
            question=question
        )
        
        # Форматируем ответ
        text = f"🤖 AI-помощник:\n\n{response}\n\n"
        text += "💡 Есть другие вопросы? Обращайтесь!"
        
        await query.edit_message_text(
            text,
            reply_markup=get_ai_help_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в handle_quick_ai_questions: {e}")
        await query.edit_message_text(
            "Ошибка получения ответа от AI. Попробуйте позже.",
            reply_markup=get_ai_help_keyboard()
        )


async def handle_custom_ai_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка запроса на ввод собственного вопроса"""
    query = update.callback_query
    
    try:
        await query.answer()
        
        # Сохраняем состояние ожидания вопроса
        context.user_data["waiting_for_ai_question"] = True
        
        text = "✍️ Задайте свой вопрос по теме банковских рисков:\n\n"
        text += "Напишите ваш вопрос в следующем сообщении, и AI-помощник даст развернутый ответ."
        
        await query.edit_message_text(text)
        
    except Exception as e:
        logger.error(f"Ошибка в handle_custom_ai_question: {e}")
        await query.edit_message_text(
            "Ошибка обработки запроса.",
            reply_markup=get_ai_help_keyboard()
        )


async def handle_user_ai_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка пользовательского вопроса к AI"""
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    question = update.message.text
    
    try:
        # Проверяем, ожидаем ли мы вопрос
        if not context.user_data.get("waiting_for_ai_question"):
            return  # Не обрабатываем, если не ожидаем вопрос
        
        # Сбрасываем флаг ожидания
        context.user_data["waiting_for_ai_question"] = False
        
        # Показываем индикатор обработки
        processing_msg = await context.bot.send_message(
            chat_id=chat_id,
            text="🤔 AI обрабатывает ваш вопрос...\nПожалуйста, подождите."
        )
        
        # Получаем ответ от AI
        response = learning_agent.provide_learning_assistance(
            user_id=user_id,
            question=question
        )
        
        # Удаляем сообщение об обработке
        await processing_msg.delete()
        
        # Отправляем ответ
        text = f"❓ Ваш вопрос: {question}\n\n"
        text += f"🤖 AI-помощник:\n{response}\n\n"
        text += "💡 Есть другие вопросы? Обращайтесь!"
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=get_ai_help_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в handle_user_ai_question: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Ошибка получения ответа от AI. Попробуйте позже."
        )


async def handle_continue_learning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка продолжения обучения после успешного урока"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    try:
        await query.answer()
        
        # Парсим данные
        topic_id = data.split("_")[-1]
        
        # Получаем прогресс пользователя
        progress_summary = db_service.get_user_progress_summary(user_id)
        
        # Определяем следующий доступный урок или тему
        current_topic = progress_summary.current_topic
        current_lesson = progress_summary.current_lesson
        
        # Проверяем, есть ли еще уроки в текущей теме
        if current_topic in LEARNING_STRUCTURE:
            total_lessons = len(LEARNING_STRUCTURE[current_topic]["lessons"])
            
            if current_lesson <= total_lessons:
                # Переходим к следующему уроку в теме
                topic_data = LEARNING_STRUCTURE[current_topic]
                text = f"{topic_data['title']}\n\n"
                text += "📚 Выберите следующий урок для изучения:"
                
                await query.edit_message_text(
                    text,
                    reply_markup=get_lessons_keyboard(current_topic, progress_summary.dict())
                )
            else:
                # Тема завершена, показываем список тем
                await query.edit_message_text(
                    "🎉 Тема завершена! Выберите следующую тему для изучения:",
                    reply_markup=get_lessons_keyboard(current_topic, progress_summary.dict())
                )
        
    except Exception as e:
        logger.error(f"Ошибка в handle_continue_learning: {e}")
        await query.edit_message_text(
            "Ошибка продолжения обучения.",
            reply_markup=get_lessons_keyboard("основы_рисков")
        )


# Регистрация обработчиков
def register_lesson_handlers(application):
    """Регистрация обработчиков уроков"""
    
    # Выбор урока
    application.add_handler(
        CallbackQueryHandler(
            handle_lesson_selection,
            pattern=r"^lesson_.*"
        ),
        group=2
    )
    
    # Начало урока
    application.add_handler(
        CallbackQueryHandler(
            handle_lesson_start,
            pattern=r"^start_lesson_.*"
        ),
        group=2
    )
    
    # Помощь AI
    application.add_handler(
        CallbackQueryHandler(
            handle_ask_ai,
            pattern=r"^ask_ai.*"
        ),
        group=2
    )
    
    # Быстрые вопросы AI
    application.add_handler(
        CallbackQueryHandler(
            handle_quick_ai_questions,
            pattern=r"^quick_.*"
        ),
        group=2
    )
    
    # Запрос собственного вопроса
    application.add_handler(
        CallbackQueryHandler(
            handle_custom_ai_question,
            pattern=r"^ask_custom_question$"
        ),
        group=2
    )
    
    # Продолжение обучения
    application.add_handler(
        CallbackQueryHandler(
            handle_continue_learning,
            pattern=r"^continue_learning_.*"
        ),
        group=2
    )
    
    # Обработчик текстовых сообщений для AI вопросов
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_user_ai_question
        ),
        group=5  # Низкий приоритет
    )