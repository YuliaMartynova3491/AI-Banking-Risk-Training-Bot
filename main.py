"""
Главный файл AI-агента для обучения рискам нарушения непрерывности деятельности банка
"""
import asyncio
import logging
import sys
import signal
from pathlib import Path

from telegram.ext import Application

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent))

from config.settings import settings
from bot.handlers.start_handler import register_start_handlers
from bot.handlers.menu_handler import register_menu_handlers
from bot.handlers.lesson_handler import register_lesson_handlers
from bot.handlers.quiz_handler import register_quiz_handlers

# Настройка логирования
def setup_logging():
    """Настройка системы логирования"""
    
    # Создаем директорию для логов если её нет
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Настройка форматирования
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Основной логгер
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=log_format,
        handlers=[
            logging.FileHandler(settings.log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Настройка логгеров telegram библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("Система логирования настроена")
    return logger


def create_application() -> Application:
    """Создание и настройка Telegram приложения"""
    
    # Создаем приложение
    application = Application.builder().token(settings.telegram_bot_token).build()
    
    # Регистрируем обработчики в правильном порядке (группы по приоритету)
    logger.info("🤖 Инициализация Telegram бота...")
    
    register_start_handlers(application)    # Группа 0 - команды старта
    logger.info("Start handlers зарегистрированы")
    
    register_menu_handlers(application)     # Группа 1 - основное меню
    logger.info("Menu handlers зарегистрированы")
    
    register_lesson_handlers(application)   # Группа 2 - уроки
    logger.info("Lesson handlers зарегистрированы")
    
    register_quiz_handlers(application)     # Группа 3 - тестирование
    logger.info("Quiz handlers зарегистрированы")
    
    logger.info("Обработчики зарегистрированы")
    
    return application


async def startup_checks():
    """Проверки при запуске приложения"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔧 Проверка системных компонентов...")
        
        # Проверяем подключение к базе данных
        from core.database import db_service
        stats = db_service.get_learning_statistics()
        logger.info(f"База данных доступна. Пользователей: {stats['total_users']}")
        logger.info("База данных работает корректно")
        
        # Проверяем RAG сервис
        from services.rag_service import rag_service
        collection_count = rag_service.collection.count()
        logger.info(f"RAG система готова. Элементов в базе знаний: {collection_count}")
        
        # Проверяем AI-агент
        from ai_agent.agent_graph import learning_agent
        logger.info("AI агент (LearningAIAgent) готов к работе")
        
        # Проверяем сервис стикеров
        from services.sticker_service import sticker_service
        test_sticker = sticker_service.get_welcome_sticker()
        logger.info(f"Сервис стикеров готов. Тестовый стикер получен: {test_sticker[:20]}...")
        
        logger.info("✅ Все системы проверены и готовы к работе")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке систем: {e}")
        raise


# Глобальная переменная для приложения
app = None

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    logger = logging.getLogger(__name__)
    logger.info("🔄 Получен сигнал завершения...")
    
    if app:
        logger.info("🔄 Остановка AI-агента...")
        asyncio.create_task(app.stop())


async def main():
    """Главная функция приложения"""
    global app
    logger = setup_logging()
    logger.info("🚀 Запуск AI-агента Risk Continuity Training Bot")
    
    # Настройка обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Выполняем проверки при запуске
        await startup_checks()
        
        # Создаем приложение
        app = create_application()
        
        # Красивый баннер
        print("\n" + "="*60)
        print("🤖 AI-АГЕНТ RISK CONTINUITY TRAINING BOT")
        print("="*60)
        print("🚀 Система запущена и готова к работе!")
        print("📚 Обучение непрерывности бизнеса с ИИ")
        print("💬 Telegram бот активен")
        print("🧠 OpenAI LLM подключен")
        print("="*60)
        
        logger.info("🚀 Система полностью инициализирована")
        logger.info("🔄 Запуск polling...")
        
        # Запускаем бота
        await app.run_polling(
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query'],
            close_loop=False
        )
        
        logger.info("✅ AI-агент успешно запущен и работает")
        logger.info("⏳ Нажмите Ctrl+C для завершения...")
        
    except KeyboardInterrupt:
        logger.info("🔄 Остановка AI-агента...")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        raise
    finally:
        if app:
            try:
                logger.info("Updater остановлен")
                await app.stop()
                logger.info("Application остановлено")
                await app.shutdown()
                logger.info("Application завершено")
            except Exception as e:
                logger.error(f"Ошибка при завершении: {e}")
        
        logger.info("👋 AI-агент завершил работу")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Приложение остановлено пользователем")
    except Exception as e:
        print(f"💥 Ошибка запуска: {e}")
        sys.exit(1)