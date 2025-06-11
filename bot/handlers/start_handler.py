# Файл: bot/handlers/start_handler.py
"""
Обработчик команд старта и инициализации
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from core.database import db_service
from config.bot_config import MESSAGES
from bot.keyboards.menu_keyboards import get_main_menu_keyboard

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    try:
        # Создаем или получаем пользователя
        user_progress = db_service.get_user_progress(user.id)
        if not user_progress:
            # Создаем нового пользователя
            initial_progress = {
                "user_id": str(user.id),
                "username": user.username,
                "first_name": user.first_name,
                "total_lessons_completed": 0,
                "total_score": 0.0,
                "current_topic": "основы_рисков",
                "current_lesson": 1,
                "topics_progress": {}
            }
            db_service.update_user_progress(user.id, initial_progress)
        
        logger.info(f"Пользователь {user.id} ({user.first_name}) запустил бота")
        
        # Персонализированное приветствие
        name = user.first_name or user.username or "пользователь"
        welcome_text = f"Привет, {name}! 👋\n\n" + MESSAGES["welcome"]
        
        # Отправляем приветствие с главным меню
        await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка в start_command: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Произошла ошибка при запуске. Попробуйте еще раз.",
            reply_markup=get_main_menu_keyboard()
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды помощи"""
    chat_id = update.effective_chat.id
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=MESSAGES["help"],
        reply_markup=get_main_menu_keyboard(),
        parse_mode='HTML'
    )

def register_start_handlers(application):
    """Регистрация обработчиков команд старта"""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))