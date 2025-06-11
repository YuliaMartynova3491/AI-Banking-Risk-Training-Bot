# Файл: bot/handlers/lesson_handler.py
"""
Обработчик уроков с AI-агентом - ПОЛНАЯ ВЕРСИЯ
"""
import logging
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.error import BadRequest

from core.database import db_service
from config.bot_config import LEARNING_STRUCTURE, MESSAGES, ALIAS_TO_TOPIC
from bot.keyboards.menu_keyboards import get_lessons_keyboard
from ai_agent.agent_graph import learning_agent

logger = logging.getLogger(__name__)

def get_lesson_start_keyboard(topic_id: str, lesson_id: int):
    """Клавиатура для начала урока"""
    from config.bot_config import TOPIC_ALIASES
    topic_alias = TOPIC_ALIASES.get(topic_id)
    
    keyboard = [
        [InlineKeyboardButton("🚀 Начать тестирование", callback_data=f"action:start_quiz;tid:{topic_alias};lesson_id:{lesson_id}")],
        [InlineKeyboardButton("📖 Изучить материал", callback_data=f"action:show_material;tid:{topic_alias};lesson_id:{lesson_id}")],
        [InlineKeyboardButton("🤖 Задать вопрос AI", callback_data=f"action:ask_ai;tid:{topic_alias};lesson_id:{lesson_id}")],
        [
            InlineKeyboardButton("◀️ К урокам", callback_data=f"action:back_to_lessons;tid:{topic_alias}"),
            InlineKeyboardButton("🏠 Меню", callback_data="action:back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_ai_help_keyboard(topic_id: str = None, lesson_id: int = None):
    """Клавиатура для помощи AI"""
    keyboard = [
        [InlineKeyboardButton("💡 Основные понятия", callback_data="action:quick_question;type:basics")],
        [InlineKeyboardButton("📖 Примеры из практики", callback_data="action:quick_question;type:examples")],
        [InlineKeyboardButton("✍️ Задать свой вопрос", callback_data="action:ask_custom_question")],
    ]
    
    if topic_id and lesson_id:
        from config.bot_config import TOPIC_ALIASES
        topic_alias = TOPIC_ALIASES.get(topic_id)
        keyboard.append([InlineKeyboardButton("◀️ К уроку", callback_data=f"action:lesson;tid:{topic_alias};lesson_id:{lesson_id}")])
    else:
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="action:back_to_topics")])
    
    return InlineKeyboardMarkup(keyboard)

def parse_callback_data(data: str) -> dict:
    """Парсит callback data"""
    result = {}
    parts = data.split(';')
    
    for part in parts:
        if ':' in part:
            key, value = part.split(':', 1)
            result[key] = value.strip()
    
    return result

async def handle_lesson_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает все callback-запросы, связанные с уроками"""
    query = update.callback_query
    await query.answer()

    logger.info(f"lesson_handler: Получен callback: {query.data}")

    data = parse_callback_data(query.data)
    action = data.get("action")
    
    topic_id = ALIAS_TO_TOPIC.get(data.get("tid"))
    lesson_id = int(data.get("lesson_id", 0)) if data.get("lesson_id") else None

    try:
        if action == "lesson":
            await show_lesson_intro(query, context, topic_id, lesson_id)
        elif action == "show_material":
            await show_lesson_material(query, context, topic_id, lesson_id)
        elif action == "ask_ai":
            await handle_ask_ai(query, context, topic_id, lesson_id)
        elif action == "quick_question":
            await handle_quick_ai_question(query, context, data.get("type"))
        elif action == "ask_custom_question":
            await handle_custom_ai_question(query, context)
        elif action == "back_to_lessons":
            await handle_back_to_lessons(query, context, topic_id)
        elif action == "start_quiz":
            await start_simple_quiz(query, context, topic_id, lesson_id)
        elif action == "lesson_locked":
            await query.answer("🔒 Этот урок пока недоступен. Завершите предыдущие.", show_alert=True)
        elif action == "quiz_answer":
            await handle_quiz_answer(query, context, data)
        else:
            await query.edit_message_text("❌ Неизвестная команда.")
            
    except Exception as e:
        logger.error(f"Ошибка в handle_lesson_callback: {e}")
        try:
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте еще раз.")
        except:
            pass

async def show_lesson_intro(query, context, topic_id: str, lesson_id: int):
    """Показывает введение к уроку"""
    try:
        topic_data = LEARNING_STRUCTURE.get(topic_id)
        if not topic_data:
            await query.edit_message_text("❌ Тема не найдена.")
            return
            
        lesson_data = None
        for lesson in topic_data["lessons"]:
            if lesson["id"] == lesson_id:
                lesson_data = lesson
                break
        
        if not lesson_data:
            await query.edit_message_text("❌ Урок не найден.")
            return
        
        # Проверяем статус урока
        user_progress = db_service.get_user_progress(query.from_user.id)
        lesson_status = ""
        
        if user_progress and "topics_progress" in user_progress:
            topic_progress = user_progress["topics_progress"].get(topic_id, {})
            lessons_data = topic_progress.get("lessons", {})
            lesson_data_progress = lessons_data.get(lesson_id, {})
            
            if lesson_data_progress.get("is_completed"):
                lesson_status = "✅ Урок завершен\n"
            elif lesson_data_progress.get("attempts", 0) > 0:
                lesson_status = f"🔄 Попыток: {lesson_data_progress['attempts']}, лучший результат: {lesson_data_progress.get('best_score', 0)}%\n"
        
        message = f"""📚 **{lesson_data['title']}**

{lesson_status}📖 **Описание:**
{lesson_data['description']}

🎯 **Цели урока:**
{lesson_data.get('objectives', 'Изучить основные понятия и применить знания на практике.')}

⏱️ **Время изучения:** ~{lesson_data.get('duration', 15)} минут

Выберите действие:"""
        
        keyboard = get_lesson_start_keyboard(topic_id, lesson_id)
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка в show_lesson_intro: {e}")
        await query.edit_message_text("❌ Ошибка загрузки урока.")

async def show_lesson_material(query, context, topic_id: str, lesson_id: int):
    """Показывает материалы урока"""
    try:
        topic_data = LEARNING_STRUCTURE.get(topic_id)
        if not topic_data:
            await query.edit_message_text("❌ Тема не найдена.")
            return
            
        lesson_data = None
        for lesson in topic_data["lessons"]:
            if lesson["id"] == lesson_id:
                lesson_data = lesson
                break
        
        if not lesson_data:
            await query.edit_message_text("❌ Урок не найден.")
            return
        
        # Получаем контент урока
        content = lesson_data.get('content', 'Материал временно недоступен.')
        
        # Разбиваем длинный текст на части
        if len(content) > 3500:
            content = content[:3500] + "\n\n... *Материал сокращен для удобства чтения*"
        
        message = f"""📖 **Материалы урока: {lesson_data['title']}**

{content}

💡 После изучения материала вы можете:
• Пройти тестирование
• Задать вопрос AI-помощнику
• Перейти к следующему уроку"""
        
        keyboard = get_lesson_start_keyboard(topic_id, lesson_id)
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка показа материала: {e}")
        await query.edit_message_text("❌ Ошибка загрузки материала.")

async def handle_ask_ai(query, context, topic_id: str = None, lesson_id: int = None):
    """Обработчик запроса помощи AI"""
    try:
        keyboard = get_ai_help_keyboard(topic_id, lesson_id)
        message = """🤖 **AI-Помощник по банковским рискам**

Я могу помочь вам:
• Объяснить основные понятия
• Привести примеры из российской практики
• Ответить на ваши вопросы

Выберите, что вас интересует:"""
        
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка handle_ask_ai: {e}")
        await query.edit_message_text("❌ Ошибка загрузки AI-помощника.")

async def handle_quick_ai_question(query, context, question_type: str):
    """Обработчик быстрых вопросов AI"""
    try:
        await query.edit_message_text("🤖 AI обрабатывает ваш вопрос...")
        
        # Формируем вопрос
        questions = {
            "basics": "Объясни основные понятия риска нарушения непрерывности простыми словами",
            "examples": "Приведи конкретные примеры из российской банковской практики"
        }
        
        question = questions.get(question_type, "Помоги разобраться с банковскими рисками")
        
        # Получаем ответ от AI-агента
        try:
            response = await asyncio.wait_for(
                get_ai_response(query.from_user.id, question),
                timeout=20.0
            )
        except asyncio.TimeoutError:
            response = "⏰ Превышено время ожидания ответа. Попробуйте еще раз."
        
        # Обрезаем слишком длинный ответ
        if len(response) > 3500:
            response = response[:3500] + "..."
        
        message = f"""🤖 **AI-Помощник**

{response}

❓ Есть дополнительные вопросы? Нажмите "Задать свой вопрос"."""
        
        keyboard = get_ai_help_keyboard()
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка handle_quick_ai_question: {e}")
        await query.edit_message_text("❌ Ошибка получения ответа.")

async def handle_custom_ai_question(query, context):
    """Обработчик пользовательских вопросов AI"""
    try:
        message = """✍️ **Задайте свой вопрос**

Напишите ваш вопрос по банковским рискам, и я постараюсь дать развернутый ответ.

Например:
• "Что такое операционный риск?"
• "Как банки оценивают риски?"
• "Какие бывают виды рисков?"

💬 Отправьте ваш вопрос следующим сообщением:"""
        
        # Сохраняем состояние ожидания вопроса
        context.user_data['waiting_for_ai_question'] = True
        
        keyboard = get_ai_help_keyboard()
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка handle_custom_ai_question: {e}")
        await query.edit_message_text("❌ Ошибка.")

async def handle_user_ai_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых вопросов к AI"""
    if not context.user_data.get('waiting_for_ai_question'):
        return
    
    # Сбрасываем флаг ожидания
    context.user_data['waiting_for_ai_question'] = False
    
    user_question = update.message.text
    user_id = update.effective_user.id
    
    # Отправляем уведомление о обработке
    processing_message = await update.message.reply_text("🤖 Обрабатываю ваш вопрос...")
    
    try:
        # Получаем ответ от AI с таймаутом
        try:
            response = await asyncio.wait_for(
                get_ai_response(user_id, user_question),
                timeout=25.0
            )
        except asyncio.TimeoutError:
            response = "⏰ Превышено время ожидания ответа. Попробуйте переформулировать вопрос."
        
        # Удаляем сообщение о обработке
        try:
            await processing_message.delete()
        except:
            pass
        
        # Обрезаем слишком длинный ответ
        if len(response) > 3500:
            response = response[:3500] + "..."
        
        # Отправляем ответ
        final_message = f"""🤖 **Ответ AI-помощника**

**Ваш вопрос:** {user_question}

**Ответ:** {response}

💡 *Для получения более подробной информации изучите материалы уроков*"""
        
        keyboard = get_ai_help_keyboard()
        await update.message.reply_text(final_message, reply_markup=keyboard, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка обработки AI-вопроса: {e}")
        try:
            await processing_message.delete()
        except:
            pass
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")

async def get_ai_response(user_id: int, question: str) -> str:
    """Получение ответа от AI-агента"""
    try:
        # Используем AI-агента для получения ответа
        response = learning_agent.provide_learning_assistance(
            user_id=str(user_id),
            question=question,
            topic="банковские риски"
        )
        
        # Проверяем качество ответа
        if len(response.strip()) < 10:
            return "Рекомендую изучить материалы урока для получения подробной информации по этому вопросу."
        
        return response
        
    except Exception as e:
        logger.error(f"Ошибка получения AI-ответа: {e}")
        return "Произошла ошибка при получении ответа. Попробуйте переформулировать вопрос."

async def handle_back_to_lessons(query, context, topic_id: str):
    """Возврат к списку уроков темы"""
    try:
        user_id = query.from_user.id
        user_progress = db_service.get_user_progress(user_id)
        
        topic_data = LEARNING_STRUCTURE.get(topic_id)
        if not topic_data:
            await query.edit_message_text("❌ Тема не найдена.")
            return
        
        message = f"""📚 **{topic_data['title']}**

Выберите урок для изучения:

{topic_data.get('description', '')}"""
        
        # Используем функцию из menu_keyboards
        keyboard = get_lessons_keyboard(topic_id, user_progress)
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка handle_back_to_lessons: {e}")
        await query.edit_message_text("❌ Ошибка загрузки уроков.")

# Простое тестирование
async def start_simple_quiz(query, context, topic_id: str, lesson_id: int):
    """Простое тестирование урока"""
    try:
        # Простые вопросы для тестирования
        questions = [
            {
                "question": "Что такое риск нарушения непрерывности деятельности?",
                "options": [
                    "Риск нарушения способности банка выполнять критически важные функции",
                    "Риск потери денег",
                    "Риск увольнения сотрудников",
                    "Риск закрытия банка"
                ],
                "correct": 0,
                "explanation": "Риск нарушения непрерывности - это риск событий, которые могут нарушить способность банка выполнять критически важные функции."
            },
            {
                "question": "Какие факторы могут привести к нарушению непрерывности?",
                "options": [
                    "Только технические сбои",
                    "Только стихийные бедствия",
                    "Технические сбои, стихийные бедствия, кибератаки, человеческий фактор",
                    "Только человеческий фактор"
                ],
                "correct": 2,
                "explanation": "Нарушение непрерывности может быть вызвано различными факторами: техническими сбоями, стихийными бедствиями, кибератаками и человеческим фактором."
            }
        ]
        
        # Сохраняем данные квиза в контексте
        context.user_data['quiz_data'] = {
            'topic_id': topic_id,
            'lesson_id': lesson_id,
            'questions': questions,
            'current_question': 0,
            'correct_answers': 0
        }
        
        await show_quiz_question(query, context)
        
    except Exception as e:
        logger.error(f"Ошибка start_simple_quiz: {e}")
        await query.edit_message_text("❌ Ошибка запуска тестирования.")

async def show_quiz_question(query, context):
    """Показ вопроса тестирования"""
    try:
        quiz_data = context.user_data.get('quiz_data')
        if not quiz_data:
            await query.edit_message_text("❌ Данные тестирования не найдены.")
            return
        
        current_q = quiz_data['current_question']
        questions = quiz_data['questions']
        
        if current_q >= len(questions):
            await show_quiz_results(query, context)
            return
        
        question = questions[current_q]
        
        text = f"❓ **Вопрос {current_q + 1} из {len(questions)}**\n\n{question['question']}"
        
        # Создаем клавиатуру с вариантами ответов
        keyboard = []
        for i, option in enumerate(question['options']):
            keyboard.append([InlineKeyboardButton(f"{i+1}. {option}", callback_data=f"action:quiz_answer;answer:{i}")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка show_quiz_question: {e}")

async def handle_quiz_answer(query, context, data):
    """Обработка ответа на вопрос"""
    try:
        quiz_data = context.user_data.get('quiz_data')
        if not quiz_data:
            return
        
        answer = int(data.get('answer', -1))
        current_q = quiz_data['current_question']
        question = quiz_data['questions'][current_q]
        
        is_correct = (answer == question['correct'])
        if is_correct:
            quiz_data['correct_answers'] += 1
        
        # Показываем результат ответа
        result_text = "✅ Правильно!" if is_correct else f"❌ Неправильно. Правильный ответ: {question['options'][question['correct']]}"
        result_text += f"\n\n💡 {question['explanation']}\n\n"
        
        quiz_data['current_question'] += 1
        
        if quiz_data['current_question'] >= len(quiz_data['questions']):
            result_text += "Нажмите 'Завершить тест' для просмотра результатов."
            keyboard = [[InlineKeyboardButton("🏁 Завершить тест", callback_data="action:finish_quiz")]]
        else:
            result_text += "Нажмите 'Следующий вопрос' для продолжения."
            keyboard = [[InlineKeyboardButton("➡️ Следующий вопрос", callback_data="action:next_question")]]
        
        await query.edit_message_text(result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка handle_quiz_answer: {e}")

async def show_quiz_results(query, context):
    """Показ результатов тестирования"""
    try:
        quiz_data = context.user_data.get('quiz_data')
        if not quiz_data:
            return
        
        correct = quiz_data['correct_answers']
        total = len(quiz_data['questions'])
        score = (correct / total) * 100
        passed = score >= 70  # 70% для прохождения
        
        # Обновляем прогресс
        user_id = query.from_user.id
        topic_id = quiz_data['topic_id']
        lesson_id = quiz_data['lesson_id']
        
        # Обновляем прогресс урока
        user_progress = db_service.get_user_progress(user_id) or {}
        
        if "topics_progress" not in user_progress:
            user_progress["topics_progress"] = {}
        
        if topic_id not in user_progress["topics_progress"]:
            user_progress["topics_progress"][topic_id] = {
                "lessons": {},
                "completed_lessons": 0,
                "total_attempts": 0,
                "average_score": 0
            }
        
        topic_progress = user_progress["topics_progress"][topic_id]
        
        if "lessons" not in topic_progress:
            topic_progress["lessons"] = {}
        
        if lesson_id not in topic_progress["lessons"]:
            topic_progress["lessons"][lesson_id] = {
                "attempts": 0,
                "best_score": 0,
                "is_completed": False
            }
        
        lesson_progress = topic_progress["lessons"][lesson_id]
        lesson_progress["attempts"] += 1
        lesson_progress["best_score"] = max(lesson_progress["best_score"], score)
        
        if passed and not lesson_progress["is_completed"]:
            lesson_progress["is_completed"] = True
            topic_progress["completed_lessons"] += 1
            user_progress["total_lessons_completed"] = user_progress.get("total_lessons_completed", 0) + 1
        
        # Сохраняем прогресс
        db_service.update_user_progress(user_id, user_progress)
        
        # Формируем сообщение с результатами
        if passed:
            result_text = f"""🎉 **Поздравляем! Урок пройден!**

📊 Ваш результат: {score:.0f}% ({correct}/{total})
✅ Следующий урок разблокирован!"""
        else:
            result_text = f"""😔 **Урок не пройден**

📊 Ваш результат: {score:.0f}% ({correct}/{total})
📝 Для прохождения нужно набрать 70%

💡 Изучите материал и попробуйте снова!"""
        
        # Клавиатура для дальнейших действий
        from config.bot_config import TOPIC_ALIASES
        topic_alias = TOPIC_ALIASES.get(topic_id)
        
        keyboard = [
            [InlineKeyboardButton("◀️ К урокам", callback_data=f"action:back_to_lessons;tid:{topic_alias}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="action:back_to_menu")]
        ]
        
        if not passed:
            keyboard.insert(0, [InlineKeyboardButton("🔄 Повторить тест", callback_data=f"action:start_quiz;tid:{topic_alias};lesson_id:{lesson_id}")])
        
        await query.edit_message_text(result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        # Очищаем данные квиза
        context.user_data.pop('quiz_data', None)
        
    except Exception as e:
        logger.error(f"Ошибка show_quiz_results: {e}")

async def handle_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переход к следующему вопросу"""
    query = update.callback_query
    await query.answer()
    await show_quiz_question(query, context)

async def handle_finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение квиза"""
    query = update.callback_query
    await query.answer()
    await show_quiz_results(query, context)

def register_lesson_handlers(application):
    """Регистрация обработчиков уроков"""
    
    # Основные обработчики уроков
    application.add_handler(CallbackQueryHandler(
        handle_lesson_callback, 
        pattern=r'^action:(lesson|show_material|ask_ai|quick_question|ask_custom_question|back_to_lessons|start_quiz|lesson_locked|quiz_answer).*'
    ))
    
    # Обработчики для квиза
    application.add_handler(CallbackQueryHandler(handle_next_question, pattern=r'^action:next_question'))
    application.add_handler(CallbackQueryHandler(handle_finish_quiz, pattern=r'^action:finish_quiz'))
    
    # Обработчик текстовых сообщений для AI-вопросов
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_user_ai_question
    ))