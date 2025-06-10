# Файл: bot/handlers/menu_handler.py
"""
Обработчик главного меню и навигации - ИСПРАВЛЕННАЯ ВЕРСИЯ
- Исправлена логика обновления после сброса прогресса
- Добавлено логирование для отладки
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
from telegram.error import BadRequest

from core.database import db_service
from config.bot_config import LEARNING_STRUCTURE, MESSAGES, ALIAS_TO_TOPIC
from bot.keyboards.menu_keyboards import (
    get_main_menu_keyboard, get_topics_keyboard, get_lessons_keyboard,
    get_progress_keyboard, get_confirmation_keyboard
)
from ai_agent.agent_graph import learning_agent
from bot.utils.helpers import parse_callback_data

logger = logging.getLogger(__name__)

# --- Обработчики кнопок меню ---

async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок главного меню."""
    message_text = update.message.text
    if message_text == "📚 Обучение":
        await show_learning_topics(update.message.chat_id, context)
    elif message_text == "📊 Прогресс":
        await show_progress(update, context)
    elif message_text == "ℹ️ Инструкция":
        await show_help(update, context)
    elif message_text == "🔄 Сброс прогресса":
        await show_reset_confirmation(update, context)

async def show_learning_topics(chat_id: int, context: ContextTypes.DEFAULT_TYPE, message_id: int = None):
    """Показывает меню выбора тем."""
    user_id = str(chat_id)
    progress_summary = db_service.get_user_progress_summary(user_id)
    text = "📚 Выберите тему для изучения:"
    reply_markup = get_topics_keyboard(progress_summary.dict())
    
    logger.info(f"[show_learning_topics] Показываем темы для пользователя {user_id}")
    
    try:
        if message_id:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            logger.warning("Сообщение не было изменено (идентично старому).")
        else:
            logger.error(f"Ошибка Telegram API при показе тем: {e}", exc_info=True)

async def show_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    progress_summary = db_service.get_user_progress_summary(user_id)
    text = f"📊 *Общий прогресс*\n- Завершено уроков: {progress_summary.total_lessons_completed}\n- Средняя оценка: {progress_summary.total_score:.1f}%\n\n"
    for topic_id, topic_data in LEARNING_STRUCTURE.items():
        topic_progress = progress_summary.topics_progress.get(topic_id, {})
        completed = topic_progress.get("completed_lessons", 0)
        total = len(topic_data["lessons"])
        avg_score = topic_progress.get("average_score", 0)
        status = "✅" if completed == total else "🔄" if completed > 0 else "⏳"
        text += f"*{topic_data['title']}*\n{status} Прогресс: {completed}/{total}, Оценка: {avg_score:.1f}%\n\n"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=get_progress_keyboard(), parse_mode='Markdown')

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=MESSAGES["help"], parse_mode='HTML')

async def show_reset_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "⚠️ Вы уверены, что хотите сбросить весь прогресс? Это действие необратимо."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=get_confirmation_keyboard("reset_progress"))


# --- Главный обработчик Callback-запросов ---

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    logger.info(f"menu_handler: Получен callback: {query.data}")

    data = parse_callback_data(query.data)
    action = data.get("action")
    user_id = str(query.from_user.id)
    
    topic_id = ALIAS_TO_TOPIC.get(data.get("tid"))

    try:
        if action == "back_to_menu":
            await query.message.delete()
            await context.bot.send_message(chat_id=user_id, text="🏠 Главное меню", reply_markup=get_main_menu_keyboard())
        elif action == "back_to_topics":
            await show_learning_topics(user_id, context, query.message.message_id)
        elif action == "topic":
            await handle_topic_selection(query, context, topic_id)
        elif action == "topic_locked":
            await query.answer("🔒 Эта тема пока недоступна. Завершите предыдущие.", show_alert=True)
        elif action == "ai_recommendations":
            await show_ai_recommendations(query, context)
        elif action == "confirm_reset_progress":
            await confirm_reset_progress(query, context)
        elif action == "cancel_reset_progress":
            await query.edit_message_text(text="Сброс прогресса отменен.")
    except BadRequest as e:
        if "Message is not modified" in str(e):
            logger.warning(f"Сообщение для action '{action}' не было изменено.")
            await query.answer()
        else:
            logger.error(f"Ошибка Telegram API для action '{action}': {e}", exc_info=True)
            await query.answer("Произошла ошибка.", show_alert=True)
    except Exception as e:
        logger.error(f"Критическая ошибка в handle_callback_query для action '{action}': {e}", exc_info=True)

# --- Вспомогательные функции ---

async def handle_topic_selection(query, context, topic_id: str):
    """Обработка выбора темы -> показывает уроки - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        logger.info(f"[handle_topic_selection] Начало для topic_id: {topic_id}")

        if not topic_id or topic_id not in LEARNING_STRUCTURE:
            logger.warning(f"[handle_topic_selection] Неверный topic_id '{topic_id}'")
            return

        # ИСПРАВЛЕНИЕ: Получаем СВЕЖИЕ данные после возможного сброса
        progress_summary = db_service.get_user_progress_summary(str(query.from_user.id))
        logger.info(f"[handle_topic_selection] Получен прогресс: {progress_summary.dict()}")

        topic_data = LEARNING_STRUCTURE[topic_id]
        text = f"*{topic_data['title']}*\n_{topic_data['description']}_\n\nВыберите урок:"
        
        # ИСПРАВЛЕНИЕ: Передаем актуальные данные в get_lessons_keyboard
        reply_markup = get_lessons_keyboard(topic_id, progress_summary.dict())
        logger.info(f"[handle_topic_selection] Клавиатура сформирована")

        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        logger.info(f"[handle_topic_selection] Сообщение успешно отредактировано!")

    except Exception as e:
        logger.error(f"[handle_topic_selection] КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)

async def show_ai_recommendations(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает рекомендации от AI."""
    await query.edit_message_text("⏳ AI анализирует ваш прогресс...")
    recs = learning_agent.adapt_learning_path(str(query.from_user.id))
    text = "🎯 *Персональные рекомендации*\n\n"
    if recs.get("message"): text += f"_{recs['message']}_\n\n"
    if recs.get("recommendations"):
        for rec in recs["recommendations"]: text += f"• {rec}\n"
    else:
        text += "Продолжайте обучение в текущем темпе! 🎓"
    await query.edit_message_text(text, reply_markup=get_progress_keyboard(), parse_mode='Markdown')

async def confirm_reset_progress(query, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение сброса прогресса - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    user_id = str(query.from_user.id)
    
    # Сбрасываем прогресс
    success = db_service.reset_user_progress(user_id)
    
    if success:
        logger.info(f"[confirm_reset_progress] Прогресс пользователя {user_id} успешно сброшен")
        
        # ИСПРАВЛЕНИЕ: Показываем обновленное меню тем с новыми данными
        await query.edit_message_text(text="✅ Ваш прогресс сброшен. Возвращаемся к выбору тем...")
        
        # Показываем свежие темы
        await show_learning_topics(int(user_id), context, query.message.message_id)
    else:
        logger.error(f"[confirm_reset_progress] Ошибка сброса прогресса для {user_id}")
        await query.edit_message_text(text="❌ Произошла ошибка при сбросе прогресса.")


# --- Регистрация обработчиков ---
def register_menu_handlers(application):
    """Регистрация обработчиков меню."""
    menu_buttons_filter = filters.Regex(r"^(📚 Обучение|📊 Прогресс|ℹ️ Инструкция|🔄 Сброс прогресса)$")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & menu_buttons_filter, handle_menu_buttons), group=1)
    
    menu_actions = [
        "back_to_menu", "back_to_topics", "topic", "topic_locked",
        "ai_recommendations", "confirm_reset_progress", "cancel_reset_progress"
    ]
    menu_callback_pattern = r"^action:(" + "|".join(menu_actions) + r").*"
    application.add_handler(CallbackQueryHandler(handle_callback_query, pattern=menu_callback_pattern), group=1)