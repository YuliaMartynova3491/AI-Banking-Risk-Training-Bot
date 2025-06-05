"""
Обработчик команд старта и инициализации
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from core.database import db_service
from core.models import UserData
from config.bot_config import START_COMMANDS, MESSAGES
from services.sticker_service import sticker_service
from bot.keyboards.menu_keyboards import get_main_menu_keyboard

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    try:
        # Создаем или получаем пользователя
        user_data = UserData(
            user_id=str(user.id),
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        db_user = db_service.get_or_create_user(user_data)
        logger.info(f"Пользователь {user.id} ({user.first_name}) запустил бота")
        
        # Отправляем приветственный стикер
        welcome_sticker = sticker_service.get_welcome_sticker(str(user.id))
        if welcome_sticker:
            try:
                await context.bot.send_sticker(
                    chat_id=chat_id,
                    sticker=welcome_sticker
                )
                logger.info(f"Отправлен приветственный стикер для пользователя {user.id}")
            except Exception as sticker_error:
                logger.error(f"Ошибка отправки стикера: {sticker_error}")
        
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


async def handle_start_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ключевых слов для запуска"""
    message_text = update.message.text.lower().strip()
    
    # Проверяем, является ли сообщение командой запуска
    if any(cmd.lower() in message_text for cmd in START_COMMANDS):
        await start_command(update, context)
    else:
        # Если это не команда запуска, пропускаем
        return


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды помощи"""
    chat_id = update.effective_chat.id
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=MESSAGES["help"],
        reply_markup=get_main_menu_keyboard(),
        parse_mode='HTML'
    )


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик неизвестных команд"""
    chat_id = update.effective_chat.id
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="Неизвестная команда. Используйте меню ниже для навигации.",
        reply_markup=get_main_menu_keyboard()
    )


# Регистрация обработчиков
def register_start_handlers(application):
    """Регистрация обработчиков команд старта"""
    
    # Команда /start
    application.add_handler(CommandHandler("start", start_command))
    
    # Команда /help
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик ключевых слов запуска (с низким приоритетом)
    start_keywords_filter = filters.TEXT & ~filters.COMMAND
    application.add_handler(
        MessageHandler(start_keywords_filter, handle_start_keywords),
        group=10  # Низкий приоритет
    )
    
    # Обработчик неизвестных команд
    application.add_handler(
        MessageHandler(filters.COMMAND, unknown_command),
        group=10  # Низкий приоритет
    )