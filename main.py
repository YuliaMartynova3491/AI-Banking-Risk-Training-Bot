"""
Главный файл AI-агента для обучения - ИСПРАВЛЕННАЯ ВЕРСИЯ
- Исправлен путь импорта knowledge_base
"""
import logging
import sys
from pathlib import Path

from telegram.ext import Application
from telegram import Update, Bot
from telegram.ext import ContextTypes

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent))

from config.settings import settings
from bot.handlers.start_handler import register_start_handlers
from bot.handlers.menu_handler import register_menu_handlers
from bot.handlers.lesson_handler import register_lesson_handlers
from bot.handlers.quiz_handler import register_quiz_handlers

# --- Настройка логирования ---
def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format=log_format,
        handlers=[logging.FileHandler(settings.log_file, encoding='utf-8'), logging.StreamHandler(sys.stdout)]
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return logging.getLogger(__name__)

# --- Обработчик ошибок ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger = logging.getLogger(__name__)
    logger.error(f"Исключение при обработке апдейта: {context.error}", exc_info=context.error)
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="😕 Произошла непредвиденная ошибка. Пожалуйста, попробуйте еще раз."
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение об ошибке пользователю: {e}")

# --- Проверка систем ---
def run_startup_checks():
    """Выполняет проверки всех ключевых систем при запуске."""
    logger = logging.getLogger(__name__)
    logger.info("🔧 Проверка системных компонентов...")
    
    from core.database import db_service
    if not db_service.health_check():
        logger.critical("❌ Проверка БД провалена!")
        raise ConnectionError("Не удалось подключиться к базе данных.")
    logger.info(f"✅ База данных доступна. Пользователей: {db_service.get_users_count()}")

    from core.knowledge_base import get_knowledge_base # <-- ИСПРАВЛЕННЫЙ ИМПОРТ
    kb = get_knowledge_base()
    if kb.collection.count() == 0:
         logger.warning("⚠️ База знаний пуста!")
    else:
        logger.info(f"✅ База знаний готова. Документов: {kb.collection.count()}")

    from ai_agent.agent_graph import learning_agent
    if learning_agent.graph is None:
        logger.warning("⚠️ AI агент работает в ограниченном режиме (LLM недоступен).")
    else:
        logger.info("✅ AI агент (LearningAIAgent) готов к работе.")

    logger.info("✅ Все системы проверены и готовы к работе.")

# --- Основная функция ---
def main():
    """Главная функция приложения."""
    logger = setup_logging()
    logger.info("🚀 Запуск AI-агента Risk Continuity Training Bot")
    
    try:
        run_startup_checks()
        
        application = Application.builder().token(settings.telegram_bot_token).build()
        
        register_start_handlers(application)
        register_menu_handlers(application)
        register_lesson_handlers(application)
        register_quiz_handlers(application)
        
        application.add_error_handler(error_handler)
        
        logger.info("🚀 Система полностью инициализирована. Запуск polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.critical(f"💥 Критическая ошибка при запуске: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()