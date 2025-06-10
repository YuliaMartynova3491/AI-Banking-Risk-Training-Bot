# Файл: bot/handlers/quiz_handler.py
"""
Обработчик тестирования и оценки знаний 
"""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler

from core.database import db_service
from config.bot_config import MESSAGES, ALIAS_TO_TOPIC
from config.settings import settings
from bot.keyboards.menu_keyboards import get_quiz_keyboard, get_quiz_result_keyboard, get_lesson_start_keyboard
from services.sticker_service import sticker_service
from services.adaptive_content_service import adaptive_content_service
from bot.utils.helpers import parse_callback_data

logger = logging.getLogger(__name__)


async def start_quiz(query: Update, context: ContextTypes.DEFAULT_TYPE, topic_id: str, lesson_id: int):
    """Начало тестирования."""
    user_id = str(query.from_user.id)
    try:
        await query.edit_message_text("🧠 AI генерирует персональные вопросы...")
        
        # ИСПРАВЛЕНО: Убираем лишние параметры
        questions_data = adaptive_content_service.generate_adaptive_questions(
            user_id=user_id, 
            topic=topic_id, 
            lesson_id=lesson_id
        )

        if not questions_data:
            await query.edit_message_text("❌ Не удалось сгенерировать вопросы. Попробуйте позже.",
                                          reply_markup=get_lesson_start_keyboard(topic_id, lesson_id))
            return

        session = db_service.create_quiz_session(user_id, topic_id, lesson_id, questions_data)
        context.user_data["quiz_session_id"] = session.id
        await show_question(query, context, 0)
    except Exception as e:
        logger.error(f"Ошибка старта квиза: {e}", exc_info=True)
        await query.edit_message_text("Ошибка запуска тестирования.")

async def show_question(query, context: ContextTypes.DEFAULT_TYPE, question_index: int):
    """Показ вопроса пользователю."""
    session_id = context.user_data.get("quiz_session_id")
    if not session_id: return
    session = db_service.get_active_quiz_session(str(query.from_user.id))
    if not session or session.id != session_id: return

    questions = session.questions
    if question_index >= len(questions):
        await show_quiz_result(query, context)
        return

    current_question = questions[question_index]
    db_service.update_quiz_session(session_id=session_id, current_question=question_index)
    
    text = f"❓ *Вопрос {question_index + 1} из {len(questions)}*\n\n{current_question['question']}"
    await query.edit_message_text(text, reply_markup=get_quiz_keyboard(current_question['options']), parse_mode='Markdown')

async def handle_quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    logger.info(f"quiz_handler: Получен callback: {query.data}")

    data = parse_callback_data(query.data)
    action = data.get("action")

    # Получаем полный topic_id из короткого алиаса `tid`
    topic_id = ALIAS_TO_TOPIC.get(data.get("tid"))

    if action == "answer":
        await handle_quiz_answer(update, context, data)
    elif action == "next_question":
        await handle_next_question(update, context)
    elif action == "retry_lesson":
        await start_quiz(query, context, topic_id, int(data.get("lesson_id")))
    elif action == "study_material":
        await query.answer("Эта функция в разработке.", show_alert=True)

async def handle_quiz_answer(update, context, data):
    """Обработка ответа на вопрос."""
    query = update.callback_query
    answer_index = int(data.get("index", -1))
    session_id = context.user_data.get("quiz_session_id")
    if session_id is None: return
    
    user_id = str(query.from_user.id)
    session = db_service.get_active_quiz_session(user_id)
    if not session: return

    q_index = session.current_question
    question = session.questions[q_index]
    is_correct = (answer_index == question['correct_answer'])

    answers = session.answers or []
    answers.append({'question_index': q_index, 'user_answer': answer_index, 'is_correct': is_correct})
    db_service.update_quiz_session(session_id=session_id, answers=answers)

    await show_answer_result(query, context, is_correct, question)

async def show_answer_result(query, context, is_correct: bool, question_data: dict):
    """Показ результата ответа на вопрос."""
    if is_correct:
        result_text = "✅ *Правильно!*\n\n"
    else:
        correct_option_text = question_data['options'][question_data['correct_answer']]
        result_text = f"❌ *Неправильно*\n\nПравильный ответ: *{correct_option_text}*\n\n"
    
    if question_data.get('explanation'):
        result_text += f"💡 *Объяснение:*\n{question_data['explanation']}"
    
    keyboard = [[InlineKeyboardButton("➡️ Продолжить", callback_data="action:next_question")]]
    await query.edit_message_text(result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переход к следующему вопросу или результатам."""
    query = update.callback_query
    session = db_service.get_active_quiz_session(str(query.from_user.id))
    if not session: return

    next_q_index = session.current_question + 1
    if next_q_index >= len(session.questions):
        await show_quiz_result(query, context)
    else:
        await show_question(query, context, next_q_index)

async def show_quiz_result(query, context: ContextTypes.DEFAULT_TYPE):
    """Показ итогового результата тестирования."""
    user_id = str(query.from_user.id)
    session = db_service.get_active_quiz_session(user_id)
    if not session: return

    correct_count = sum(1 for ans in session.answers if ans['is_correct'])
    total = len(session.questions)
    score = (correct_count / total) * 100 if total > 0 else 0
    passed = score >= settings.min_score_to_pass

    db_service.complete_quiz_session(session.id, score)
    db_service.update_lesson_progress(user_id, session.topic_id, session.lesson_id, score, passed)

    if passed:
        result_text = MESSAGES["quiz_complete_success"].format(score=int(score), correct=correct_count, total=total)
    else:
        result_text = MESSAGES["quiz_complete_failure"].format(score=int(score), correct=correct_count, total=total, min_score=settings.min_score_to_pass)
    
    try:
        sticker = sticker_service.get_adaptive_sticker(user_id, {'lesson_completed': True, 'score': score})
        if sticker: await context.bot.send_sticker(chat_id=query.message.chat_id, sticker=sticker)
    except Exception as e:
        logger.warning(f"Ошибка отправки стикера: {e}")

    await query.edit_message_text(result_text, reply_markup=get_quiz_result_keyboard(session.topic_id, session.lesson_id, passed))
    context.user_data.pop("quiz_session_id", None)
        
def register_quiz_handlers(application):
    """Регистрация обработчиков тестирования."""
    quiz_actions = [
        "answer", "next_question", "retry_lesson", "study_material"
    ]
    quiz_callback_pattern = r"^action:(" + "|".join(quiz_actions) + r").*"
    application.add_handler(CallbackQueryHandler(handle_quiz_callback, pattern=quiz_callback_pattern), group=3)