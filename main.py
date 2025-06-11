"""
Главный файл AI-агента для обучения рискам непрерывности
"""
import logging
import sys
import asyncio
import signal
import traceback
from pathlib import Path
from logging.handlers import RotatingFileHandler

from telegram.ext import Application
from telegram import Update
from telegram.ext import ContextTypes

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent))

from config.settings import settings

# Глобальные переменные для graceful shutdown
shutdown_event = asyncio.Event()

def setup_logging():
    """Настройка системы логирования"""
    try:
        # Создаем директорию для логов
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Формат логов
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Настраиваем корневой логгер
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
        
        # Удаляем существующие обработчики
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Обработчик для файла с ротацией
        file_handler = RotatingFileHandler(
            settings.log_file_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))
        
        # Обработчик для консоли
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(log_format))
        
        # Добавляем обработчики
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        # Настраиваем уровни для внешних библиотек
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("telegram").setLevel(logging.WARNING)
        
        logger = logging.getLogger(__name__)
        logger.info("✅ [Logging] Система логирования настроена успешно")
        logger.info(f"📝 [Logging] Логи записываются в: {settings.log_file_path}")
        
        return logger
        
    except Exception as e:
        print(f"❌ [Logging] Ошибка настройки логирования: {e}")
        # Базовая настройка как fallback
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        return logging.getLogger(__name__)

async def initialize_agent_systems():
    """Инициализация всех систем агента"""
    logger = logging.getLogger(__name__)
    logger.info("🚀 [Startup] Инициализация систем AI-агента...")
    
    initialization_steps = [
        ("База данных", initialize_database),
        ("База знаний", initialize_knowledge_base),
        ("AI-агент LangGraph", initialize_ai_agent),
        ("Сервисы", initialize_services)
    ]
    
    for step_name, init_func in initialization_steps:
        try:
            logger.info(f"⚙️ [Startup] Инициализация: {step_name}")
            await init_func()
            logger.info(f"✅ [Startup] {step_name}: готов")
        except Exception as e:
            logger.error(f"❌ [Startup] Ошибка инициализации {step_name}: {e}")
            logger.error(f"Трейс: {traceback.format_exc()}")
            raise SystemExit(f"Критическая ошибка при инициализации {step_name}")
    
    logger.info("🎉 [Startup] Все системы агента готовы к работе!")

async def initialize_database():
    """Инициализация базы данных"""
    logger = logging.getLogger(__name__)
    
    try:
        from core.database import db_service
        
        if not db_service.health_check():
            raise Exception("База данных недоступна")
        
        users_count = db_service.get_users_count()
        logger.info(f"👥 [Database] Пользователей в БД: {users_count}")
        
    except Exception as e:
        logger.error(f"❌ [Database] Ошибка инициализации БД: {e}")
        raise

async def initialize_knowledge_base():
    """Инициализация базы знаний"""
    logger = logging.getLogger(__name__)
    
    try:
        from core.knowledge_base import get_knowledge_base
        
        kb = get_knowledge_base()
        if kb.collection.count() == 0:
            logger.warning("⚠️ [Knowledge] База знаний пуста!")
        else:
            logger.info(f"📚 [Knowledge] База знаний: {kb.collection.count()} документов")
            
    except Exception as e:
        logger.error(f"❌ [Knowledge] Ошибка инициализации базы знаний: {e}")
        raise

async def initialize_ai_agent():
    """Инициализация AI-агента"""
    logger = logging.getLogger(__name__)
    
    try:
        from ai_agent.agent_graph import learning_agent
        
        # Проверяем готовность агента
        if not learning_agent.graph:
            logger.warning("⚠️ [Agent] Граф агента недоступен")
        else:
            logger.info("🤖 [Agent] LangGraph агент готов")
            
        # Простой тест агента
        test_response = learning_agent.provide_learning_assistance(
            user_id="test_user",
            question="Тест"
        )
        
        if test_response and len(test_response) > 5:
            logger.info("✅ [Agent] Тест агента прошел успешно")
        else:
            logger.warning("⚠️ [Agent] Тест агента показал проблемы")
            
    except Exception as e:
        logger.error(f"❌ [Agent] Ошибка инициализации агента: {e}")
        logger.warning("⚠️ [Agent] Агент будет работать в ограниченном режиме")

async def initialize_services():
    """Инициализация сервисов"""
    logger = logging.getLogger(__name__)
    
    try:
        from services.adaptive_content_service import adaptive_content_service
        from services.user_analysis_service import user_analysis_service
        from services.sticker_service import sticker_service
        
        # Инициализируем сервисы
        adaptive_content_service._initialize_llm()
        
        logger.info("🔧 [Services] Сервисы инициализированы")
        
    except Exception as e:
        logger.error(f"❌ [Services] Ошибка инициализации сервисов: {e}")
        raise

def setup_signal_handlers():
    """Настройка обработчиков сигналов для graceful shutdown"""
    logger = logging.getLogger(__name__)
    
    def signal_handler(signum, frame):
        logger.info(f"🛑 [Shutdown] Получен сигнал {signum}, начинаю graceful shutdown...")
        shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

async def graceful_shutdown(application=None):
    """Graceful shutdown всех систем"""
    logger = logging.getLogger(__name__)
    logger.info("🛑 [Shutdown] Начинаю остановку всех систем...")
    
    try:
        # Останавливаем телеграм бота
        if application:
            logger.info("📱 [Shutdown] Остановка Telegram бота...")
            await application.stop()
            await application.shutdown()
        
        # Закрываем соединения с БД
        try:
            from core.database import db_service
            db_service.close()
            logger.info("🗄️ [Shutdown] База данных отключена")
        except Exception as e:
            logger.error(f"❌ [Shutdown] Ошибка отключения БД: {e}")
        
        logger.info("✅ [Shutdown] Все системы остановлены корректно")
        
    except Exception as e:
        logger.error(f"❌ [Shutdown] Ошибка при остановке: {e}")

async def main():
    """Главная функция с полной инициализацией агента"""
    logger = logging.getLogger(__name__)
    logger.info("🤖 [Main] Запуск AI-агента для обучения банковским рискам")
    
    application = None
    
    try:
        # Настраиваем обработчики сигналов
        setup_signal_handlers()
        
        # Инициализируем все системы агента
        await initialize_agent_systems()
        
        # Создаем Telegram приложение
        application = Application.builder().token(settings.telegram_bot_token).build()
        
        # Регистрируем обработчики
        register_all_handlers(application)
        
        # Запускаем бота
        logger.info("🚀 [Main] Запуск Telegram бота...")
        
        # Инициализируем приложение
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        
        logger.info("✅ [Main] AI-агент полностью запущен и готов к работе!")
        logger.info("📱 [Main] Бот ожидает сообщений в Telegram...")
        
        # Ждем сигнала завершения
        await shutdown_event.wait()
        
    except Exception as e:
        logger.error(f"❌ [Main] Критическая ошибка: {e}")
        logger.error(f"Трейс: {traceback.format_exc()}")
        return 1
    
    finally:
        # Graceful shutdown
        await graceful_shutdown(application)
    
    return 0

def register_all_handlers(application):
    """Регистрация всех обработчиков"""
    logger = logging.getLogger(__name__)
    
    try:
        from bot.handlers.start_handler import register_start_handlers
        from bot.handlers.menu_handler import register_menu_handlers
        from bot.handlers.lesson_handler import register_lesson_handlers
        from bot.handlers.quiz_handler import register_quiz_handlers
        
        # Регистрируем основные обработчики
        register_start_handlers(application)
        register_menu_handlers(application)
        register_lesson_handlers(application)
        register_quiz_handlers(application)
        
        # Добавляем обработчик ошибок агента
        application.add_error_handler(agent_error_handler)
        
        # Пытаемся зарегистрировать админ-обработчики
        try:
            from bot.handlers.admin_handler import register_admin_handlers
            register_admin_handlers(application)
            logger.info("🔧 [Handlers] Админ-обработчики зарегистрированы")
        except ImportError:
            logger.info("ℹ️ [Handlers] Админ-обработчики не найдены (пропускаем)")
        
        logger.info("✅ [Handlers] Все обработчики зарегистрированы")
        
    except Exception as e:
        logger.error(f"❌ [Handlers] Ошибка регистрации обработчиков: {e}")
        raise

async def agent_error_handler(update, context):
    """Специальный обработчик ошибок для агента"""
    logger = logging.getLogger(__name__)
    logger.error(f"🚨 [AgentError] Ошибка в агенте: {context.error}")
    logger.error(f"Трейс: {traceback.format_exc()}")
    
    if update and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🤖 AI-агент временно недоступен. Попробуйте позже или обратитесь к материалам урока."
            )
        except Exception as e:
            logger.error(f"❌ [AgentError] Не удалось отправить сообщение об ошибке: {e}")

if __name__ == "__main__":
    # Настраиваем логирование первым делом
    logger = setup_logging()
    
    try:
        logger.info("🎬 [Main] Старт приложения AI-агента")
        
        # Выводим информацию о конфигурации
        from config.settings import print_config_summary
        print_config_summary()
        
        # Запускаем главную функцию
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("👋 [Main] Получен сигнал прерывания от пользователя")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 [Main] Необработанная ошибка: {e}")
        logger.error(f"Трейс: {traceback.format_exc()}")
        sys.exit(1)