# Файл: bot/handlers/lesson_handler.py
"""
Обработчик уроков и обучающего контента - ИСПРАВЛЕННАЯ ВЕРСИЯ 4.0
- Используются короткие алиасы для callback_data
- Вынесена функция parse_callback_data в утилиты
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.error import BadRequest

from core.database import db_service
from config.bot_config import LEARNING_STRUCTURE, MESSAGES, ALIAS_TO_TOPIC # ИЗМЕНЕНО: Импорт ALIAS_TO_TOPIC
from bot.keyboards.menu_keyboards import get_lesson_start_keyboard, get_lessons_keyboard, get_ai_help_keyboard
from ai_agent.agent_graph import learning_agent
from bot.handlers.quiz_handler import start_quiz
from bot.handlers.menu_handler import show_learning_topics
from bot.utils.helpers import parse_callback_data # ИЗМЕНЕНО: Импорт из утилит

logger = logging.getLogger(__name__)


# --- Главный обработчик Callback-запросов ---
async def handle_lesson_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает все callback-запросы, связанные с уроками."""
    query = update.callback_query
    await query.answer()

    logger.info(f"lesson_handler: Получен callback: {query.data}")

    data = parse_callback_data(query.data)
    action = data.get("action")
    
    # ИЗМЕНЕНО: Получаем полный topic_id из короткого алиаса `tid`
    topic_id = ALIAS_TO_TOPIC.get(data.get("tid"))
    lesson_id = int(data.get("lesson_id", 0))

    try:
        if action == "lesson":
            await show_lesson_intro(query, context, topic_id, lesson_id)
        elif action == "start_lesson":
            await start_quiz_wrapper(query, context, topic_id, lesson_id)
        elif action == "ask_ai":
            await handle_ask_ai(query, context, topic_id, lesson_id)
        elif action == "quick_question":
            await handle_quick_ai_question(query, context, data.get("type"))
        elif action == "ask_custom_question":
            await handle_custom_ai_question(query, context)
        elif action == "continue_learning":
            # Используем topic_id для возврата к списку уроков нужной темы
            await handle_back_to_lessons(query, context, topic_id)
        elif action == "back_to_lessons":
            await handle_back_to_lessons(query, context, topic_id)
        elif action == "lesson_locked":
             await query.answer("🔒 Этот урок пока недоступен. Завершите предыдущие.", show_alert=True)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            logger.warning(f"Сообщение для action '{action}' не было изменено.")
        else:
            logger.error(f"Ошибка Telegram API для action '{action}': {e}", exc_info=True)
            await query.answer("Произошла ошибка.", show_alert=True)
    except Exception as e:
        logger.error(f"Критическая ошибка в handle_lesson_callback для action '{action}': {e}", exc_info=True)


# --- Логика обработчиков ---

async def show_lesson_intro(query, context, topic_id: str, lesson_id: int):
    """Показывает введение к уроку."""
    if not topic_id or not lesson_id: return
    topic_data = LEARNING_STRUCTURE.get(topic_id)
    if not topic_data: return
    
    lesson_data = next((l for l in topic_data["lessons"] if l["id"] == lesson_id), None)
    if not lesson_data: return
    
    text = MESSAGES["lesson_intro"].format(
        lesson_title=lesson_data["title"],
        lesson_description=lesson_data["description"],
        keywords=", ".join(lesson_data["keywords"])
    )
    reply_markup = get_lesson_start_keyboard(topic_id, lesson_id)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def start_quiz_wrapper(query, context, topic_id: str, lesson_id: int):
    """Обёртка для запуска квиза."""
    if not topic_id or not lesson_id: return
    db_service.get_or_create_lesson_progress(str(query.from_user.id), topic_id, lesson_id)
    await start_quiz(query, context, topic_id, lesson_id)

async def handle_ask_ai(query, context, topic_id: str, lesson_id: int):
    """Обработка запроса помощи у AI."""
    text = "🤖 AI-помощник готов ответить на ваши вопросы!"
    reply_markup = get_ai_help_keyboard(topic_id, lesson_id)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def handle_quick_ai_question(query, context, question_type: str):
    """Обработка быстрых вопросов к AI."""
    question_map = {
        "basics": "Объясни основные понятия риска нарушения непрерывности",
        "examples": "Приведи примеры из банковской практики управления рисками"
    }
    question = question_map.get(question_type)
    if not question: return

    await query.edit_message_text("🤔 AI обрабатывает ваш вопрос, подождите...")
    response = learning_agent.provide_learning_assistance(user_id=str(query.from_user.id), question=question)
    text = f"🤖 *AI-помощник:*\n\n{response}\n\n💡 Есть другие вопросы?"
    await query.edit_message_text(text, reply_markup=get_ai_help_keyboard(), parse_mode='Markdown')

async def handle_custom_ai_question(query, context: ContextTypes.DEFAULT_TYPE):
    """Обработка запроса на ввод собственного вопроса."""
    context.user_data["waiting_for_ai_question"] = True
    text = "✍️ Задайте свой вопрос по теме банковских рисков в следующем сообщении."
    await query.edit_message_text(text)

async def handle_user_ai_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка пользовательского вопроса к AI, введенного текстом."""
    if not context.user_data.get("waiting_for_ai_question"):
        return
    context.user_data["waiting_for_ai_question"] = False
    
    user_id = str(update.effective_user.id)
    question = update.message.text
    
    processing_msg = await update.message.reply_text("🤔 AI обрабатывает ваш вопрос...")
    response = learning_agent.provide_learning_assistance(user_id=user_id, question=question)
    await processing_msg.delete()

    text = f"❓ *Ваш вопрос:*\n{question}\n\n🤖 *AI-помощник:*\n{response}"
    await update.message.reply_text(text, reply_markup=get_ai_help_keyboard(), parse_mode='Markdown')

async def handle_back_to_lessons(query, context, topic_id: str):
    """Возврат к списку уроков темы."""
    if not topic_id:
        await show_learning_topics(query.message.chat_id, context, query.message.message_id)
        return

    progress_summary = db_service.get_user_progress_summary(str(query.from_user.id))
    topic_data = LEARNING_STRUCTURE[topic_id]
    text = f"*{topic_data['title']}*\n_{topic_data['description']}_\n\nВыберите урок:"
    reply_markup = get_lessons_keyboard(topic_id, progress_summary.dict())
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# --- Регистрация обработчиков ---
def register_lesson_handlers(application):
    """Регистрация обработчиков уроков."""
    lesson_actions = [
        "lesson", "start_lesson", "ask_ai", "quick_question",
        "ask_custom_question", "continue_learning", "back_to_lessons", "lesson_locked"
    ]
    lesson_callback_pattern = r"^action:(" + "|".join(lesson_actions) + r").*"
    application.add_handler(CallbackQueryHandler(handle_lesson_callback, pattern=lesson_callback_pattern), group=2)

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_ai_question), group=5)