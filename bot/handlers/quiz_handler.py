"""
Обработчик тестирования и оценки знаний
"""
import logging
from typing import List, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from core.database import db_service
from core.models import GeneratedQuestion
from config.bot_config import MESSAGES, LEARNING_STRUCTURE
from config.settings import settings
from bot.keyboards.menu_keyboards import (
    get_quiz_keyboard, get_quiz_result_keyboard, get_lesson_start_keyboard
)
from ai_agent.agent_graph import learning_agent
from services.sticker_service import sticker_service

logger = logging.getLogger(__name__)


async def start_quiz(query, context: ContextTypes.DEFAULT_TYPE, topic_id: str, lesson_id: int):
    """Начало тестирования"""
    user_id = str(query.from_user.id)
    
    try:
        # Показываем сообщение о генерации вопросов
        await query.edit_message_text(
            "🧠 AI генерирует персональные вопросы для вас...\nПожалуйста, подождите."
        )
        
        # Генерируем адаптивные вопросы с помощью AI-агента
        questions_data = learning_agent.generate_adaptive_questions(
            user_id=user_id,
            topic=topic_id,
            lesson_id=lesson_id
        )
        
        if not questions_data:
            await query.edit_message_text(
                "❌ Не удалось сгенерировать вопросы. Попробуйте позже.",
                reply_markup=get_lesson_start_keyboard(topic_id, lesson_id)
            )
            return
        
        # Создаем сессию тестирования
        quiz_session = db_service.create_quiz_session(
            user_id=user_id,
            topic_id=topic_id,
            lesson_id=lesson_id,
            questions=questions_data
        )
        
        # Сохраняем ID сессии в контексте
        context.user_data["quiz_session_id"] = quiz_session.id
        context.user_data["quiz_correct_count"] = 0
        context.user_data["quiz_consecutive_wrong"] = 0
        context.user_data["quiz_first_correct"] = True
        
        # Показываем первый вопрос
        await show_question(query, context, 0)
        
    except Exception as e:
        logger.error(f"Ошибка старта тестирования: {e}")
        await query.edit_message_text(
            "Ошибка запуска тестирования.",
            reply_markup=get_lesson_start_keyboard(topic_id, lesson_id)
        )
    """Начало тестирования"""
    user_id = str(query.from_user.id)
    
    try:
        # Показываем сообщение о генерации вопросов
        await query.edit_message_text(
            "🧠 AI генерирует персональные вопросы для вас...\nПожалуйста, подождите."
        )
        
        # Генерируем адаптивные вопросы с помощью AI-агента
        questions_data = learning_agent.generate_adaptive_questions(
            user_id=user_id,
            topic=topic_id,
            lesson_id=lesson_id
        )
        
        if not questions_data:
            await query.edit_message_text(
                "❌ Не удалось сгенерировать вопросы. Попробуйте позже.",
                reply_markup=get_lesson_start_keyboard(topic_id, lesson_id)
            )
            return
        
        # Создаем сессию тестирования
        quiz_session = db_service.create_quiz_session(
            user_id=user_id,
            topic_id=topic_id,
            lesson_id=lesson_id,
            questions=questions_data
        )
        
        # Сохраняем ID сессии в контексте
        context.user_data["quiz_session_id"] = quiz_session.id
        context.user_data["quiz_correct_count"] = 0
        context.user_data["quiz_consecutive_wrong"] = 0
        context.user_data["quiz_first_correct"] = True
        
        # Показываем первый вопрос
        await show_question(query, context, 0)
        
    except Exception as e:
        logger.error(f"Ошибка старта тестирования: {e}")
        await query.edit_message_text(
            "Ошибка запуска тестирования.",
            reply_markup=get_lesson_start_keyboard(topic_id, lesson_id)
        )


async def show_question(query, context: ContextTypes.DEFAULT_TYPE, question_index: int):
    """Показ вопроса пользователю"""
    session_id = context.user_data.get("quiz_session_id")
    
    if not session_id:
        await query.edit_message_text("Ошибка: сессия тестирования не найдена.")
        return
    
    try:
        # Получаем сессию
        quiz_session = db_service.get_active_quiz_session(str(query.from_user.id))
        
        if not quiz_session or quiz_session.id != session_id:
            await query.edit_message_text("Ошибка: недействительная сессия тестирования.")
            return
        
        questions = quiz_session.questions
        
        if question_index >= len(questions):
            # Все вопросы отвечены, показываем результат
            await show_quiz_result(query, context)
            return
        
        current_question = questions[question_index]
        
        # Обновляем текущий вопрос в сессии
        db_service.update_quiz_session(
            session_id=session_id,
            current_question=question_index
        )
        
        # Формируем текст вопроса
        question_text = f"❓ <b>Вопрос {question_index + 1} из {len(questions)}</b>\n\n"
        question_text += f"{current_question['question']}"
        
        await query.edit_message_text(
            question_text,
            reply_markup=get_quiz_keyboard(
                question_index + 1,
                len(questions),
                current_question['options']
            ),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка показа вопроса: {e}")
        await query.edit_message_text("Ошибка показа вопроса.")


async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответа на вопрос"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    
    try:
        await query.answer()
        
        # Получаем индекс ответа
        answer_index = int(query.data.split("_")[1])
        session_id = context.user_data.get("quiz_session_id")
        
        if not session_id:
            await query.edit_message_text("Ошибка: сессия тестирования не найдена.")
            return
        
        # Получаем сессию
        quiz_session = db_service.get_active_quiz_session(user_id)
        
        if not quiz_session or quiz_session.id != session_id:
            await query.edit_message_text("Ошибка: недействительная сессия тестирования.")
            return
        
        current_question_index = quiz_session.current_question
        questions = quiz_session.questions
        current_question = questions[current_question_index]
        
        # Проверяем правильность ответа
        correct_answer_index = current_question['correct_answer']
        is_correct = answer_index == correct_answer_index
        
        # Обновляем статистику
        current_answers = quiz_session.answers or []
        current_answers.append({
            'question_index': current_question_index,
            'user_answer': answer_index,
            'correct_answer': correct_answer_index,
            'is_correct': is_correct
        })
        
        # Обновляем сессию
        db_service.update_quiz_session(
            session_id=session_id,
            answers=current_answers
        )
        
        # Обновляем счетчики в контексте
        if is_correct:
            context.user_data["quiz_correct_count"] += 1
            context.user_data["quiz_consecutive_wrong"] = 0
        else:
            context.user_data["quiz_consecutive_wrong"] += 1
        
        # Показываем результат ответа
        await show_answer_result(query, context, is_correct, current_question)
        
    except Exception as e:
        logger.error(f"Ошибка обработки ответа: {e}")
        await query.edit_message_text("Ошибка обработки ответа.")


async def show_answer_result(query, context: ContextTypes.DEFAULT_TYPE, 
                           is_correct: bool, question_data: Dict[str, Any]):
    """Показ результата ответа на вопрос"""
    user_id = str(query.from_user.id)
    
    try:
        # Определяем подходящий стикер
        sticker_context = {
            'is_correct': is_correct,
            'is_first_correct': context.user_data.get("quiz_first_correct", True) and is_correct,
            'consecutive_wrong': context.user_data.get("quiz_consecutive_wrong", 0)
        }
        
        # Отправляем стикер
        sticker = sticker_service.get_adaptive_sticker(user_id, sticker_context)
        if sticker:
            await context.bot.send_sticker(
                chat_id=query.message.chat_id,
                sticker=sticker
            )
        
        # Сбрасываем флаг первого правильного ответа
        if is_correct and context.user_data.get("quiz_first_correct"):
            context.user_data["quiz_first_correct"] = False
        
        # Формируем текст результата
        if is_correct:
            result_text = "✅ <b>Правильно!</b>\n\n"
            encouragement = learning_agent.get_personalized_encouragement(
                user_id=user_id,
                score=100,  # За правильный ответ
                is_improvement=context.user_data.get("quiz_consecutive_wrong", 0) > 0
            )
            result_text += f"💬 {encouragement}\n\n"
        else:
            result_text = "❌ <b>Неправильно</b>\n\n"
            correct_option = question_data['options'][question_data['correct_answer']]
            result_text += f"Правильный ответ: <b>{correct_option}</b>\n\n"
        
        # Добавляем объяснение
        if 'explanation' in question_data:
            result_text += f"💡 <b>Объяснение:</b>\n{question_data['explanation']}\n\n"
        
        # Кнопка продолжения
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [[
            InlineKeyboardButton("➡️ Следующий вопрос", callback_data="next_question")
        ]]
        
        await query.edit_message_text(
            result_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка показа результата ответа: {e}")
        await query.edit_message_text("Ошибка показа результата.")


async def handle_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переход к следующему вопросу"""
    query = update.callback_query
    
    try:
        await query.answer()
        
        session_id = context.user_data.get("quiz_session_id")
        quiz_session = db_service.get_active_quiz_session(str(query.from_user.id))
        
        if not quiz_session or quiz_session.id != session_id:
            await query.edit_message_text("Ошибка: сессия тестирования не найдена.")
            return
        
        next_question_index = quiz_session.current_question + 1
        
        if next_question_index >= len(quiz_session.questions):
            # Это был последний вопрос
            await show_quiz_result(query, context)
        else:
            # Показываем следующий вопрос
            await show_question(query, context, next_question_index)
        
    except Exception as e:
        logger.error(f"Ошибка перехода к следующему вопросу: {e}")
        await query.edit_message_text("Ошибка перехода к следующему вопросу.")


async def show_quiz_result(query, context: ContextTypes.DEFAULT_TYPE):
    """Показ итогового результата тестирования"""
    user_id = str(query.from_user.id)
    session_id = context.user_data.get("quiz_session_id")
    
    try:
        # Получаем сессию
        quiz_session = db_service.get_active_quiz_session(user_id)
        
        if not quiz_session or quiz_session.id != session_id:
            await query.edit_message_text("Ошибка: сессия тестирования не найдена.")
            return
        
        # Подсчитываем результаты
        correct_count = context.user_data.get("quiz_correct_count", 0)
        total_questions = len(quiz_session.questions)
        score = (correct_count / total_questions) * 100 if total_questions > 0 else 0
        passed = score >= settings.min_score_to_pass
        
        # Завершаем сессию тестирования
        db_service.complete_quiz_session(session_id, score)
        
        # Обновляем прогресс урока
        db_service.update_lesson_progress(
            user_id=user_id,
            topic_id=quiz_session.topic_id,
            lesson_id=quiz_session.lesson_id,
            score=score,
            is_completed=passed
        )
        
        # Определяем подходящий стикер
        sticker_context = {
            'lesson_completed': True,
            'score': score,
            'topic_completed': False  # Будет обновлено ниже
        }
        
        # Проверяем, завершена ли тема
        topic_completed = _check_topic_completion(user_id, quiz_session.topic_id)
        sticker_context['topic_completed'] = topic_completed
        
        # Отправляем соответствующий стикер
        sticker = sticker_service.get_adaptive_sticker(user_id, sticker_context)
        if sticker:
            await context.bot.send_sticker(
                chat_id=query.message.chat_id,
                sticker=sticker
            )
        
        # Формируем текст результата
        if passed:
            result_text = MESSAGES["quiz_complete_success"].format(
                score=int(score),
                correct=correct_count,
                total=total_questions
            )
            
            # Персонализированное поощрение
            encouragement = learning_agent.get_personalized_encouragement(
                user_id=user_id,
                score=score,
                is_improvement=True
            )
            result_text += f"\n💬 {encouragement}"
            
            # Если тема завершена
            if topic_completed:
                topic_data = LEARNING_STRUCTURE[quiz_session.topic_id]
                result_text += f"\n\n{MESSAGES['topic_complete'].format(topic_title=topic_data['title'])}"
                
                # Обновляем текущую позицию пользователя
                _update_user_current_position(user_id, quiz_session.topic_id, quiz_session.lesson_id)
        else:
            result_text = MESSAGES["quiz_complete_failure"].format(
                score=int(score),
                correct=correct_count,
                total=total_questions,
                min_score=settings.min_score_to_pass
            )
            
            # Получаем объяснение от AI для неуспешного прохождения
            ai_help = learning_agent.provide_learning_assistance(
                user_id=user_id,
                question=f"Помоги улучшить результат по теме {quiz_session.topic_id}, урок {quiz_session.lesson_id}",
                topic=quiz_session.topic_id,
                lesson_id=quiz_session.lesson_id
            )
            
            if ai_help and len(ai_help) < 200:  # Краткий совет
                result_text += f"\n\n💡 Совет AI: {ai_help}"
        
        # Очищаем данные сессии из контекста
        _clear_quiz_context(context)
        
        await query.edit_message_text(
            result_text,
            reply_markup=get_quiz_result_keyboard(
                quiz_session.topic_id,
                quiz_session.lesson_id,
                passed
            )
        )
        
    except Exception as e:
        logger.error(f"Ошибка показа результата тестирования: {e}")
        await query.edit_message_text("Ошибка обработки результата тестирования.")


async def handle_retry_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка повторного прохождения урока"""
    query = update.callback_query
    data = query.data
    
    try:
        await query.answer()
        
        # Парсим данные
        _, _, topic_id, lesson_id = data.split("_", 3)
        lesson_id = int(lesson_id)
        
        # Перезапускаем тестирование
        await start_quiz(query, context, topic_id, lesson_id)
        
    except Exception as e:
        logger.error(f"Ошибка повторного прохождения урока: {e}")
        await query.edit_message_text("Ошибка повторного прохождения урока.")


async def handle_study_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка изучения материала"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    try:
        await query.answer()
        
        # Парсим данные
        _, _, topic_id, lesson_id = data.split("_", 3)
        lesson_id = int(lesson_id)
        
        # Получаем материалы от AI
        study_material = learning_agent.provide_learning_assistance(
            user_id=user_id,
            question=f"Предоставь учебный материал для изучения темы {topic_id}, урок {lesson_id}",
            topic=topic_id,
            lesson_id=int(lesson_id)
        )
        
        text = f"📚 Учебный материал\n\n{study_material}\n\n"
        text += "После изучения материала вы можете повторить тестирование."
        
        await query.edit_message_text(
            text,
            reply_markup=get_quiz_result_keyboard(topic_id, int(lesson_id), False)
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения учебного материала: {e}")
        await query.edit_message_text(
            "Ошибка получения учебного материала.",
            reply_markup=get_quiz_result_keyboard(topic_id, int(lesson_id), False)
        )


async def handle_quiz_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка запроса помощи во время тестирования"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    
    try:
        await query.answer("Получаю помощь от AI...")
        
        session_id = context.user_data.get("quiz_session_id")
        quiz_session = db_service.get_active_quiz_session(user_id)
        
        if not quiz_session or quiz_session.id != session_id:
            await query.answer("Ошибка: сессия не найдена", show_alert=True)
            return
        
        current_question_index = quiz_session.current_question
        current_question = quiz_session.questions[current_question_index]
        
        # Получаем подсказку от AI (без прямого ответа)
        hint = learning_agent.provide_learning_assistance(
            user_id=user_id,
            question=f"Дай подсказку для вопроса: {current_question['question']}. Не давай прямой ответ, только направление для размышления.",
            topic=quiz_session.topic_id,
            lesson_id=quiz_session.lesson_id
        )
        
        # Показываем подсказку в alert
        hint_text = hint[:180] + "..." if len(hint) > 180 else hint
        await query.answer(f"💡 Подсказка: {hint_text}", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка получения помощи в тестировании: {e}")
        await query.answer("Ошибка получения помощи", show_alert=True)


async def handle_quiz_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ прогресса тестирования"""
    query = update.callback_query
    
    try:
        session_id = context.user_data.get("quiz_session_id")
        quiz_session = db_service.get_active_quiz_session(str(query.from_user.id))
        
        if not quiz_session or quiz_session.id != session_id:
            await query.answer("Ошибка: сессия не найдена", show_alert=True)
            return
        
        current_question = quiz_session.current_question + 1
        total_questions = len(quiz_session.questions)
        correct_count = context.user_data.get("quiz_correct_count", 0)
        
        progress_text = f"Вопрос {current_question}/{total_questions}\n"
        progress_text += f"Правильных ответов: {correct_count}"
        
        if current_question > 1:
            current_score = (correct_count / (current_question - 1)) * 100
            progress_text += f"\nТекущий результат: {current_score:.0f}%"
        
        await query.answer(progress_text, show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка показа прогресса тестирования: {e}")
        await query.answer("Ошибка получения прогресса", show_alert=True)


# Вспомогательные функции

def _check_topic_completion(user_id: str, topic_id: str) -> bool:
    """Проверка завершения темы"""
    try:
        if topic_id not in LEARNING_STRUCTURE:
            return False
        
        total_lessons = len(LEARNING_STRUCTURE[topic_id]["lessons"])
        progress_summary = db_service.get_user_progress_summary(user_id)
        
        if topic_id in progress_summary.topics_progress:
            completed_lessons = progress_summary.topics_progress[topic_id].get("completed_lessons", 0)
            return completed_lessons >= total_lessons
        
        return False
        
    except Exception as e:
        logger.error(f"Ошибка проверки завершения темы: {e}")
        return False


def _update_user_current_position(user_id: str, completed_topic_id: str, completed_lesson_id: int):
    """Обновление текущей позиции пользователя"""
    try:
        # Определяем следующую позицию
        topic_order = ["основы_рисков", "критичность_процессов", "оценка_рисков"]
        
        if completed_topic_id in LEARNING_STRUCTURE:
            total_lessons_in_topic = len(LEARNING_STRUCTURE[completed_topic_id]["lessons"])
            
            if completed_lesson_id < total_lessons_in_topic:
                # Переходим к следующему уроку в той же теме
                next_topic = completed_topic_id
                next_lesson = completed_lesson_id + 1
            else:
                # Переходим к следующей теме
                current_topic_index = topic_order.index(completed_topic_id)
                if current_topic_index + 1 < len(topic_order):
                    next_topic = topic_order[current_topic_index + 1]
                    next_lesson = 1
                else:
                    # Все темы завершены
                    return
            
            # Обновляем позицию пользователя
            db_service.update_user_progress(
                user_id=user_id,
                current_topic=next_topic,
                current_lesson=next_lesson
            )
            
    except Exception as e:
        logger.error(f"Ошибка обновления позиции пользователя: {e}")


def _clear_quiz_context(context: ContextTypes.DEFAULT_TYPE):
    """Очистка контекста тестирования"""
    keys_to_remove = [
        "quiz_session_id",
        "quiz_correct_count", 
        "quiz_consecutive_wrong",
        "quiz_first_correct"
    ]
    
    for key in keys_to_remove:
        context.user_data.pop(key, None)


# Регистрация обработчиков
def register_quiz_handlers(application):
    """Регистрация обработчиков тестирования"""
    
    # Ответы на вопросы
    application.add_handler(
        CallbackQueryHandler(
            handle_quiz_answer,
            pattern=r"^answer_\d+$"
        ),
        group=3
    )
    
    # Переход к следующему вопросу
    application.add_handler(
        CallbackQueryHandler(
            handle_next_question,
            pattern=r"^next_question$"
        ),
        group=3
    )
    
    # Повторное прохождение урока
    application.add_handler(
        CallbackQueryHandler(
            handle_retry_lesson,
            pattern=r"^retry_lesson_.*"
        ),
        group=3
    )
    
    # Изучение материала
    application.add_handler(
        CallbackQueryHandler(
            handle_study_material,
            pattern=r"^study_material_.*"
        ),
        group=3
    )
    
    # Помощь во время тестирования
    application.add_handler(
        CallbackQueryHandler(
            handle_quiz_help,
            pattern=r"^quiz_help$"
        ),
        group=3
    )
    
    # Прогресс тестирования
    application.add_handler(
        CallbackQueryHandler(
            handle_quiz_progress,
            pattern=r"^quiz_progress$"
        ),
        group=3
    )