# Файл: bot/handlers/menu_handler.py
"""
Обработчик главного меню и навигации - ИСПРАВЛЕННАЯ ВЕРСИЯ
"""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
from telegram.error import BadRequest

from core.database import db_service
from config.bot_config import LEARNING_STRUCTURE, MESSAGES, ALIAS_TO_TOPIC
from bot.keyboards.menu_keyboards import get_topics_keyboard, get_lessons_keyboard

logger = logging.getLogger(__name__)

def parse_callback_data(data: str) -> dict:
    """Парсит callback data"""
    result = {}
    parts = data.split(';')
    
    for part in parts:
        if ':' in part:
            key, value = part.split(':', 1)
            result[key] = value.strip()
    
    return result

async def handle_learning_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Обучение'"""
    if update.message.text != "📚 Обучение":
        return
    
    await show_learning_topics(update.message.chat_id, context)

async def show_learning_topics(chat_id: int, context: ContextTypes.DEFAULT_TYPE, message_id: int = None):
    """Показывает меню выбора тем"""
    user_id = str(chat_id)
    user_progress = db_service.get_user_progress(user_id)
    text = "📚 Выберите тему для изучения:"
    reply_markup = get_topics_keyboard(user_progress)
    
    logger.info(f"[show_learning_topics] Показываем темы для пользователя {user_id}")
    
    try:
        if message_id:
            await context.bot.edit_message_text(
                chat_id=chat_id, 
                message_id=message_id, 
                text=text, 
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id, 
                text=text, 
                reply_markup=reply_markup
            )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            logger.warning("Сообщение не было изменено (идентично старому).")
        else:
            logger.error(f"Ошибка Telegram API при показе тем: {e}")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главный обработчик Callback-запросов"""
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
            from bot.keyboards.menu_keyboards import get_main_menu_keyboard
            await context.bot.send_message(
                chat_id=user_id, 
                text="🏠 Главное меню", 
                reply_markup=get_main_menu_keyboard()
            )
        elif action == "back_to_topics":
            await show_learning_topics(user_id, context, query.message.message_id)
        elif action == "topic":
            await handle_topic_selection(query, context, topic_id)
        elif action == "topic_locked":
            await query.answer("🔒 Эта тема пока недоступна. Завершите предыдущие.", show_alert=True)
        elif action == "confirm_reset":
            await confirm_reset_progress(query, context)
        elif action == "cancel_reset":
            await query.edit_message_text(text="Сброс прогресса отменен.")
    except BadRequest as e:
        if "Message is not modified" in str(e):
            logger.warning(f"Сообщение для action '{action}' не было изменено.")
            await query.answer()
        else:
            logger.error(f"Ошибка Telegram API для action '{action}': {e}")
            await query.answer("Произошла ошибка.", show_alert=True)
    except Exception as e:
        logger.error(f"Критическая ошибка в handle_callback_query для action '{action}': {e}")

async def handle_topic_selection(query, context, topic_id: str):
    """Обработка выбора темы -> показывает уроки"""
    try:
        logger.info(f"[handle_topic_selection] Начало для topic_id: {topic_id}")

        if not topic_id or topic_id not in LEARNING_STRUCTURE:
            logger.warning(f"[handle_topic_selection] Неверный topic_id '{topic_id}'")
            return

        # Получаем свежие данные после возможного сброса
        user_progress = db_service.get_user_progress(str(query.from_user.id))
        logger.info(f"[handle_topic_selection] Получен прогресс")

        topic_data = LEARNING_STRUCTURE[topic_id]
        text = f"*{topic_data['title']}*\n_{topic_data['description']}_\n\nВыберите урок:"
        
        # Передаем актуальные данные в get_lessons_keyboard
        reply_markup = get_lessons_keyboard(topic_id, user_progress)
        logger.info(f"[handle_topic_selection] Клавиатура сформирована")

        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        logger.info(f"[handle_topic_selection] Сообщение успешно отредактировано!")

    except Exception as e:
        logger.error(f"[handle_topic_selection] КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)

async def confirm_reset_progress(query, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение сброса прогресса"""
    user_id = str(query.from_user.id)
    
    try:
        # Сбрасываем прогресс
        user_progress = {
            "topics_progress": {},
            "total_lessons_completed": 0,
            "total_score": 0.0,
            "current_topic": "основы_рисков",
            "current_lesson": 1
        }
        
        db_service.update_user_progress(user_id, user_progress)
        
        logger.info(f"[confirm_reset_progress] Прогресс пользователя {user_id} успешно сброшен")
        
        await query.edit_message_text(text="✅ Ваш прогресс сброшен. Возвращаемся к выбору тем...")
        
        # Показываем свежие темы
        await show_learning_topics(int(user_id), context, query.message.message_id)
        
    except Exception as e:
        logger.error(f"[confirm_reset_progress] Ошибка сброса прогресса для {user_id}: {e}")
        await query.edit_message_text(text="❌ Произошла ошибка при сбросе прогресса.")

def register_menu_handlers(application):
    """Регистрация обработчиков меню"""
    
    # Обработчик кнопки "Обучение"
    application.add_handler(MessageHandler(
        filters.Regex(r"^📚 Обучение$"), 
        handle_learning_button
    ))
    
    # Callback-обработчики для меню
    menu_actions = [
        "back_to_menu", "back_to_topics", "topic", "topic_locked",
        "confirm_reset", "cancel_reset"
    ]
    menu_callback_pattern = r"^action:(" + "|".join(menu_actions) + r").*"
    application.add_handler(CallbackQueryHandler(handle_callback_query, pattern=menu_callback_pattern))