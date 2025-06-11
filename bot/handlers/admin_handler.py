"""
Административные команды для мониторинга и отладки
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from utils.monitoring import monitoring
from utils.health_check import health_checker
from services.progress_service import progress_service
from core.database import db_service

logger = logging.getLogger(__name__)

# ID администраторов (замените на ваши)
ADMIN_IDS = [8052999265]  # Замените на ваш Telegram ID

def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /admin_status - показывает статус системы"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    try:
        # Получаем отчет о мониторинге
        status_report = monitoring.get_status_report()
        
        # Добавляем информацию о здоровье системы
        health_check = await health_checker.check_all_components()
        
        health_status = f"""
🏥 **Проверка здоровья системы:**
• Общий статус: {"🟢" if health_check["overall_status"] == "healthy" else "🟡" if health_check["overall_status"] == "degraded" else "🔴"} {health_check["overall_status"]}
• База данных: {"✅" if health_check["components"]["database"]["healthy"] else "❌"}
• AI-агент: {"✅" if health_check["components"]["ai_agent"]["healthy"] else "❌"}
• Конфигурация: {"✅" if health_check["components"]["config"]["healthy"] else "❌"}"""

        full_report = status_report + health_status
        await update.message.reply_text(full_report, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка команды admin_status: {e}")
        await update.message.reply_text(f"❌ Ошибка получения статуса: {e}")

async def admin_debug_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /debug_user <user_id> - отладка прогресса пользователя"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    try:
        if not context.args:
            await update.message.reply_text("Использование: /debug_user <user_id>")
            return
        
        user_id = int(context.args[0])
        debug_info = progress_service.debug_user_progress(user_id)
        
        await update.message.reply_text(f"```\n{debug_info}\n```", parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text("❌ Неверный ID пользователя")
    except Exception as e:
        logger.error(f"Ошибка команды debug_user: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def admin_reset_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /reset_user <user_id> - сброс прогресса пользователя"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    try:
        if not context.args:
            await update.message.reply_text("Использование: /reset_user <user_id>")
            return
        
        user_id = int(context.args[0])
        success = progress_service.reset_user_progress(user_id)
        
        if success:
            await update.message.reply_text(f"✅ Прогресс пользователя {user_id} сброшен")
        else:
            await update.message.reply_text(f"❌ Ошибка сброса прогресса пользователя {user_id}")
            
    except ValueError:
        await update.message.reply_text("❌ Неверный ID пользователя")
    except Exception as e:
        logger.error(f"Ошибка команды reset_user: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /admin_stats - детальная статистика"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    try:
        # Статистика пользователей
        all_users = db_service.get_all_users_stats()  # Нужно добавить этот метод в db_service
        
        stats_text = f"""📊 **ДЕТАЛЬНАЯ СТАТИСТИКА**

👥 **Пользователи:**
• Всего пользователей: {len(all_users) if all_users else 0}
• Активных за сегодня: [данные недоступны]
• Завершили хотя бы 1 урок: [подсчитывается...]

📚 **Обучение:**
• Всего уроков завершено: {monitoring.stats['lesson_completions']}
• Попыток тестирования: {monitoring.stats['quiz_attempts']}

🤖 **AI-агент:**
• Всего запросов: {monitoring.stats['ai_requests']}
• Таймауты: {monitoring.stats['ai_timeouts']}
• Ошибки: {monitoring.stats['errors']}"""
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка команды admin_stats: {e}")
        await update.message.reply_text(f"❌ Ошибка получения статистики: {e}")

async def admin_test_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /test_ai - тест AI-агента"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    try:
        from ai_agent.agent_nodes import AgentNodes
        import time
        
        await update.message.reply_text("🧪 Тестирую AI-агента...")
        
        # Тестовый запрос
        start_time = time.time()
        test_state = {
            "user_question": "Что такое операционный риск?",
            "topic": "основы_рисков"
        }
        
        result = AgentNodes.provide_assistance_node(test_state)
        response_time = time.time() - start_time
        
        response = result.get("assistance_response", "Нет ответа")
        
        test_result = f"""🧪 **ТЕСТ AI-АГЕНТА**

⏱️ **Время ответа:** {response_time:.2f}с
📝 **Ответ:** {response[:200]}{'...' if len(response) > 200 else ''}
✅ **Статус:** {"Успешно" if response and len(response) > 10 else "Ошибка"}"""
        
        await update.message.reply_text(test_result, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка команды test_ai: {e}")
        await update.message.reply_text(f"❌ Ошибка тестирования AI: {e}")

async def admin_clear_cache(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /clear_cache - очистка кэша"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    try:
        from utils.performance_optimizer import optimizer
        
        # Очищаем кэш
        cache_size_before = len(optimizer.cache)
        optimizer.clear_expired_cache()
        optimizer.cache.clear()  # Полная очистка
        
        await update.message.reply_text(f"🧹 Кэш очищен. Удалено записей: {cache_size_before}")
        
    except Exception as e:
        logger.error(f"Ошибка команды clear_cache: {e}")
        await update.message.reply_text(f"❌ Ошибка очистки кэша: {e}")

def register_admin_handlers(application):
    """Регистрация административных команд"""
    application.add_handler(CommandHandler("admin_status", admin_status))
    application.add_handler(CommandHandler("debug_user", admin_debug_user))
    application.add_handler(CommandHandler("reset_user", admin_reset_user))
    application.add_handler(CommandHandler("admin_stats", admin_stats))
    application.add_handler(CommandHandler("test_ai", admin_test_ai))
    application.add_handler(CommandHandler("clear_cache", admin_clear_cache))