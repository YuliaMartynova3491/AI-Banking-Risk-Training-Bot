"""
Обработчик главного меню и навигации
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters

from core.database import db_service
from config.bot_config import MENU_BUTTONS, MESSAGES, LEARNING_STRUCTURE
from bot.keyboards.menu_keyboards import (
    get_main_menu_keyboard, get_topics_keyboard, get_lessons_keyboard, 
    get_progress_keyboard, get_confirmation_keyboard
)
from ai_agent.agent_graph import learning_agent

logger = logging.getLogger(__name__)


async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок главного меню"""
    message_text = update.message.text
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    
    try:
        if message_text == "📚 Обучение":
            await show_learning_menu(update, context)
        
        elif message_text == "📊 Прогресс":
            await show_progress(update, context)
        
        elif message_text == "ℹ️ Инструкция":
            await show_help(update, context)
        
        elif message_text == "🔄 Сброс прогресса":
            await show_reset_confirmation(update, context)
        
        else:
            # Неизвестная кнопка меню
            await context.bot.send_message(
                chat_id=chat_id,
                text="Выберите действие из меню ниже:",
                reply_markup=get_main_menu_keyboard()
            )
    
    except Exception as e:
        logger.error(f"Ошибка в handle_menu_buttons: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Произошла ошибка. Попробуйте еще раз.",
            reply_markup=get_main_menu_keyboard()
        )


async def show_learning_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню обучения"""
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    
    try:
        # Получаем прогресс пользователя
        progress_summary = db_service.get_user_progress_summary(user_id)
        
        text = "📚 Выберите тему для изучения:\n\n"
        
        # Добавляем описания тем
        for topic_id, topic_data in LEARNING_STRUCTURE.items():
            # Получаем прогресс по теме
            topic_progress_data = None
            if topic_id in progress_summary.topics_progress:
                topic_progress = progress_summary.topics_progress[topic_id]
                completed = topic_progress.get("completed_lessons", 0)
                total = len(topic_data["lessons"])
                
                if completed > 0:
                    topic_progress_data = f" ({completed}/{total})"
                    if completed == total:
                        topic_progress_data += " ✅"
            
            text += f"🎯 <b>{topic_data['title']}</b>"
            if topic_progress_data:
                text += topic_progress_data
            text += f"\n📝 {topic_data['description']}\n\n"
        
        text += "💡 <i>Темы открываются последовательно по мере изучения.</i>"
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=get_topics_keyboard(progress_summary.dict()),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка в show_learning_menu: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Ошибка загрузки меню обучения.",
            reply_markup=get_main_menu_keyboard()
        )


async def show_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать прогресс обучения"""
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    
    try:
        progress_summary = db_service.get_user_progress_summary(user_id)
        
        if progress_summary.total_lessons_completed == 0:
            text = MESSAGES["no_progress"]
        else:
            text = MESSAGES["progress_header"]
            text += f"📊 Общая статистика:\n"
            text += f"✅ Уроков завершено: {progress_summary.total_lessons_completed}\n"
            text += f"⭐ Средняя оценка: {progress_summary.total_score:.1f}%\n\n"
            
            # Прогресс по темам
            for topic_id, topic_data in LEARNING_STRUCTURE.items():
                topic_title = topic_data["title"]
                total_lessons = len(topic_data["lessons"])
                
                if topic_id in progress_summary.topics_progress:
                    topic_progress = progress_summary.topics_progress[topic_id]
                    completed = topic_progress.get("completed_lessons", 0)
                    avg_score = topic_progress.get("average_score", 0)
                    
                    if completed > 0:
                        text += f"{topic_title}\n"
                        text += f"   📈 Прогресс: {completed}/{total_lessons} уроков\n"
                        text += f"   ⭐ Средняя оценка: {avg_score:.1f}%\n\n"
                else:
                    text += f"{topic_title}\n"
                    text += f"   📈 Прогресс: 0/{total_lessons} уроков\n\n"
            
            # Получаем рекомендации от AI
            recommendations = learning_agent.adapt_learning_path(user_id)
            if recommendations.get("recommendations"):
                text += "🎯 Рекомендации AI:\n"
                for rec in recommendations["recommendations"][:3]:  # Первые 3 рекомендации
                    text += f"• {rec}\n"
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=get_progress_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в show_progress: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Ошибка загрузки прогресса.",
            reply_markup=get_main_menu_keyboard()
        )


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать инструкцию"""
    chat_id = update.effective_chat.id
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=MESSAGES["help"],
        reply_markup=get_main_menu_keyboard(),
        parse_mode='HTML'
    )


async def show_reset_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать подтверждение сброса прогресса"""
    chat_id = update.effective_chat.id
    
    text = "⚠️ Вы уверены, что хотите сбросить весь прогресс обучения?\n\n"
    text += "Это действие нельзя отменить. Все пройденные уроки и результаты будут удалены."
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=get_confirmation_keyboard("reset_progress")
    )


# Обработчики callback queries

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик inline кнопок"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    try:
        await query.answer()  # Подтверждаем получение callback
        
        if data == "back_to_menu":
            await back_to_main_menu(query, context)
        
        elif data == "back_to_topics":
            await back_to_topics(query, context)
        
        elif data.startswith("topic_"):
            await handle_topic_selection(query, context)
        
        elif data.startswith("back_to_lessons_"):
            await handle_back_to_lessons(query, context)
        
        elif data.startswith("lesson_"):
            # Перенаправляем к обработчику уроков
            from bot.handlers.lesson_handler import handle_lesson_selection
            await handle_lesson_selection(update, context)
            return
        
        elif data.startswith("start_lesson_"):
            # Перенаправляем к обработчику начала урока
            from bot.handlers.lesson_handler import handle_lesson_start
            await handle_lesson_start(update, context)
            return
        
        elif data.startswith("ask_ai"):
            # Перенаправляем к обработчику AI
            from bot.handlers.lesson_handler import handle_ask_ai
            await handle_ask_ai(update, context)
            return
        
        elif data.startswith("quick_"):
            # Перенаправляем к обработчику быстрых AI вопросов
            from bot.handlers.lesson_handler import handle_quick_ai_questions
            await handle_quick_ai_questions(update, context)
            return
        
        elif data == "ask_custom_question":
            # Перенаправляем к обработчику собственного вопроса
            from bot.handlers.lesson_handler import handle_custom_ai_question
            await handle_custom_ai_question(update, context)
            return
        
        elif data == "lesson_locked":
            await query.answer(
                "🔒 Этот урок пока недоступен. Завершите предыдущие уроки для разблокировки.",
                show_alert=True
            )
        
        elif data == "topic_locked":
            await query.answer(
                "🔒 Эта тема пока недоступна. Завершите предыдущие темы для разблокировки.",
                show_alert=True
            )
        
        elif data == "detailed_stats":
            await show_detailed_statistics(query, context)
        
        elif data == "ai_recommendations":
            await show_ai_recommendations(query, context)
        
        elif data == "confirm_reset":
            await confirm_reset_progress(query, context)
        
        elif data == "cancel_reset":
            await cancel_reset_progress(query, context)
        
        else:
            logger.warning(f"Неизвестный callback: {data}")
            # Для неизвестных callback просто показываем alert
            await query.answer("Команда не распознана", show_alert=True)
    
    except Exception as e:
        logger.error(f"Ошибка в handle_callback_query: {e}")
        try:
            await query.answer("Произошла ошибка. Попробуйте еще раз.", show_alert=True)
        except Exception:
            pass


async def back_to_main_menu(query, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    welcome_text = "🏠 Главное меню\n\nВыберите действие из меню ниже 👇"
    
    # Отправляем новое сообщение вместо редактирования
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=welcome_text,
        reply_markup=get_main_menu_keyboard()
    )
    
    # Удаляем старое сообщение с inline клавиатурой
    try:
        await query.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")


async def back_to_topics(query, context: ContextTypes.DEFAULT_TYPE):
    """Возврат к выбору тем"""
    user_id = str(query.from_user.id)
    progress_summary = db_service.get_user_progress_summary(user_id)
    
    text = "📚 Выберите тему для изучения:"
    
    await query.edit_message_text(
        text,
        reply_markup=get_topics_keyboard(progress_summary.dict())
    )


async def handle_topic_selection(query, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора темы"""
    user_id = str(query.from_user.id)
    topic_id = query.data.split("_", 1)[1]
    
    if topic_id not in LEARNING_STRUCTURE:
        await query.edit_message_text(
            "Тема не найдена.",
            reply_markup=get_topics_keyboard()
        )
        return
    
    progress_summary = db_service.get_user_progress_summary(user_id)
    topic_data = LEARNING_STRUCTURE[topic_id]
    
    text = f"{topic_data['title']}\n\n"
    text += f"📝 {topic_data['description']}\n\n"
    text += "📚 Выберите урок для изучения:"
    
    await query.edit_message_text(
        text,
        reply_markup=get_lessons_keyboard(topic_id, progress_summary.dict())
    )


async def handle_back_to_lessons(query, context: ContextTypes.DEFAULT_TYPE):
    """Возврат к урокам темы"""
    user_id = str(query.from_user.id)
    topic_id = query.data.split("_")[-1]
    
    progress_summary = db_service.get_user_progress_summary(user_id)
    topic_data = LEARNING_STRUCTURE[topic_id]
    
    text = f"{topic_data['title']}\n\n"
    text += "📚 Выберите урок для изучения:"
    
    await query.edit_message_text(
        text,
        reply_markup=get_lessons_keyboard(topic_id, progress_summary.dict())
    )


async def show_detailed_statistics(query, context: ContextTypes.DEFAULT_TYPE):
    """Показать детальную статистику"""
    user_id = str(query.from_user.id)
    progress_summary = db_service.get_user_progress_summary(user_id)
    
    text = "📈 Детальная статистика обучения\n\n"
    
    for topic_id, topic_data in LEARNING_STRUCTURE.items():
        topic_title = topic_data["title"]
        text += f"{topic_title}\n"
        
        if topic_id in progress_summary.topics_progress:
            topic_progress = progress_summary.topics_progress[topic_id]
            lessons_data = topic_progress.get("lessons", {})
            
            for lesson in topic_data["lessons"]:
                lesson_id = str(lesson["id"])
                lesson_title = lesson["title"]
                
                if lesson_id in lessons_data:
                    lesson_data = lessons_data[lesson_id]
                    if lesson_data.get("is_completed"):
                        score = lesson_data.get("best_score", 0)
                        attempts = lesson_data.get("attempts", 0)
                        text += f"  ✅ {lesson_title}: {score:.0f}% ({attempts} попыток)\n"
                    else:
                        attempts = lesson_data.get("attempts", 0)
                        text += f"  🔄 {lesson_title}: в процессе ({attempts} попыток)\n"
                else:
                    text += f"  ⏳ {lesson_title}: не начат\n"
        else:
            for lesson in topic_data["lessons"]:
                text += f"  ⏳ {lesson['title']}: не начат\n"
        
        text += "\n"
    
    await query.edit_message_text(
        text,
        reply_markup=get_progress_keyboard()
    )


async def show_ai_recommendations(query, context: ContextTypes.DEFAULT_TYPE):
    """Показать рекомендации AI"""
    user_id = str(query.from_user.id)
    
    try:
        recommendations = learning_agent.adapt_learning_path(user_id)
        
        text = "🎯 Персональные рекомендации от AI\n\n"
        
        if recommendations.get("message"):
            text += f"💬 {recommendations['message']}\n\n"
        
        if recommendations.get("recommendations"):
            text += "📋 Рекомендации:\n"
            for i, rec in enumerate(recommendations["recommendations"], 1):
                text += f"{i}. {rec}\n"
        else:
            text += "Продолжайте обучение в текущем темпе! 🎓"
        
        await query.edit_message_text(
            text,
            reply_markup=get_progress_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения рекомендаций AI: {e}")
        await query.edit_message_text(
            "Не удалось получить рекомендации. Попробуйте позже.",
            reply_markup=get_progress_keyboard()
        )


async def confirm_reset_progress(query, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение сброса прогресса"""
    user_id = str(query.from_user.id)
    
    try:
        success = db_service.reset_user_progress(user_id)
        
        if success:
            text = "✅ Прогресс обучения успешно сброшен.\n\n"
            text += "Вы можете начать обучение заново."
        else:
            text = "❌ Ошибка при сбросе прогресса. Попробуйте позже."
        
        await query.edit_message_text(
            text,
            reply_markup=get_main_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка сброса прогресса: {e}")
        await query.edit_message_text(
            "❌ Ошибка при сбросе прогресса.",
            reply_markup=get_main_menu_keyboard()
        )


async def cancel_reset_progress(query, context: ContextTypes.DEFAULT_TYPE):
    """Отмена сброса прогресса"""
    await query.edit_message_text(
        "Сброс прогресса отменен.",
        reply_markup=get_main_menu_keyboard()
    )


# Регистрация обработчиков
def register_menu_handlers(application):
    """Регистрация обработчиков меню"""
    
    # Обработчик кнопок главного меню
    menu_filter = filters.TEXT & filters.Regex(
        r"^(📚 Обучение|📊 Прогресс|ℹ️ Инструкция|🔄 Сброс прогресса)$"
    )
    application.add_handler(
        MessageHandler(menu_filter, handle_menu_buttons),
        group=1
    )
    
    # Обработчик inline кнопок
    application.add_handler(
        CallbackQueryHandler(handle_callback_query),
        group=1
    )