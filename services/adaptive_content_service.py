"""
Сервис для работы с базой знаний и адаптивной генерации контента 
"""
import json
import logging
import random
from typing import List, Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI

from config.settings import settings
from core.models import GeneratedQuestion
from services.user_analysis_service import user_analysis_service
from core.knowledge_base import get_knowledge_base

logger = logging.getLogger(__name__)


class AdaptiveContentService:
    """Сервис для RAG и генерации адаптивного контента."""

    def __init__(self):
        self.knowledge_base = get_knowledge_base()
        self.llm = None
        self._initialized_llm = False

    def _initialize_llm(self):
        """Ленивая инициализация LLM."""
        if self._initialized_llm:
            return
        try:
            self.llm = ChatOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_api_base,
                model=settings.openai_model,
                temperature=0.7,
            )
            self._initialized_llm = True
            logger.info("LLM для генерации контента успешно инициализирован.")
        except Exception as e:
            logger.error(f"Не удалось инициализировать LLM: {e}")
            self.llm = None

    def search_relevant_content(self, query: str, n_results: int = 5, topic_filter: str = None) -> List[Dict[str, Any]]:
        """Поиск релевантного контента в базе знаний."""
        return self.knowledge_base.search(query, n_results, topic_filter)

    def generate_adaptive_questions(self, user_id: str, topic: str, lesson_id: int) -> List[Dict[str, Any]]:
        """
        ИСПРАВЛЕНО: Приоритет AI генерации над статическими вопросами
        """
        try:
            analysis = user_analysis_service.get_full_user_analysis(user_id)
            content_settings = analysis.get("content_settings", {})
            difficulty = content_settings.get("difficulty", "intermediate")
            count = content_settings.get("question_count", settings.questions_per_lesson)

            logger.info(f"Генерация {count} вопросов для {user_id} по теме {topic}, сложность: {difficulty}")

            self._initialize_llm()
            
            # ИСПРАВЛЕНО: Сначала пытаемся LLM, потом fallback
            if self.llm:
                logger.info("Попытка генерации с LLM...")
                questions = self._generate_questions_with_llm(topic, lesson_id, difficulty, count)
                if questions and len(questions) >= count:
                    logger.info(f"✅ Успешно сгенерировано {len(questions)} вопросов с LLM")
                    return [q.dict() for q in questions]
                else:
                    logger.warning("LLM генерация не удалась, используем fallback")

            # Fallback к статическим вопросам
            logger.warning(f"Используется fallback-метод генерации вопросов для {user_id}")
            return [q.dict() for q in self._get_fallback_questions(topic, lesson_id, count)]

        except Exception as e:
            logger.error(f"Критическая ошибка генерации вопросов: {e}")
            return [q.dict() for q in self._get_fallback_questions(topic, lesson_id, 3)]

    def _generate_questions_with_llm(self, topic: str, lesson_id: int, difficulty: str, count: int) -> Optional[List[GeneratedQuestion]]:
        """ИСПРАВЛЕНО: Улучшенная генерация с LLM"""
        try:
            relevant_docs = self.knowledge_base.search(f"{topic} урок {lesson_id}", n_results=5, topic_filter=topic)
            if not relevant_docs:
                logger.warning("Не найдены релевантные документы для генерации вопросов с LLM.")
                return None
            
            context_text = "\n\n".join([doc['document'] for doc in relevant_docs])

            # ИСПРАВЛЕНО: Более четкий промпт для русского языка
            prompt_text = f"""Ты - эксперт по банковским рискам. Создай {count} тестовых вопросов ТОЛЬКО на русском языке.

Тема: {topic}
Урок: {lesson_id}
Сложность: {difficulty}

Контекст из базы знаний:
{context_text}

Требования:
- Каждый вопрос имеет 4 варианта ответа
- Только один правильный ответ
- Краткое объяснение
- Примеры из российских банков
- Разные по сложности

JSON формат:
[
  {{
    "question": "текст вопроса",
    "options": ["вариант 1", "вариант 2", "вариант 3", "вариант 4"],
    "correct_answer": 0,
    "explanation": "объяснение"
  }}
]

ВАЖНО: Отвечай ТОЛЬКО JSON массивом, без дополнительного текста."""

            response = self.llm.invoke(prompt_text)
            
            # Парсим JSON ответ
            try:
                # Очищаем ответ от лишнего текста
                content = response.content.strip()
                
                # Ищем JSON массив в ответе
                start_idx = content.find('[')
                end_idx = content.rfind(']') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_content = content[start_idx:end_idx]
                else:
                    json_content = content
                
                questions_data = json.loads(json_content)
                
                if not isinstance(questions_data, list):
                    questions_data = [questions_data]
                    
                questions = []
                for q_data in questions_data:
                    if isinstance(q_data, dict) and all(key in q_data for key in ["question", "options", "correct_answer", "explanation"]):
                        question = GeneratedQuestion(
                            question=q_data["question"],
                            options=q_data["options"],
                            correct_answer=q_data["correct_answer"],
                            explanation=q_data["explanation"],
                            source_context=context_text[:200],
                            difficulty=difficulty,
                            confidence_score=0.9
                        )
                        questions.append(question)
                        
                return questions if len(questions) >= count else None
                
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга JSON ответа от LLM: {e}")
                logger.error(f"Ответ LLM: {response.content}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при генерации вопросов с LLM: {e}")
            return None

    def _get_fallback_questions(self, topic: str, lesson_id: int, count: int) -> List[GeneratedQuestion]:
        """Получение статических вопросов как запасной вариант."""
        fallback_questions = {
            "основы_рисков": {
                1: [
                    GeneratedQuestion(
                        question="Что является основной целью оценки риска нарушения непрерывности деятельности?",
                        options=[
                            "Выявление и анализ угроз непрерывности",
                            "Увеличение прибыли банка", 
                            "Сокращение персонала",
                            "Расширение филиальной сети"
                        ],
                        correct_answer=0,
                        explanation="Основная цель - выявление, анализ и оценка угроз, которые могут нарушить операционную устойчивость банка.",
                        source_context="Базовые знания",
                        difficulty="beginner",
                        confidence_score=0.9
                    ),
                    GeneratedQuestion(
                        question="Кто является инициатором проведения оценки риска нарушения непрерывности?",
                        options=[
                            "Владельцы процессов",
                            "УОР (Управление операционных рисков)",
                            "Специализированные подразделения", 
                            "Руководство банка"
                        ],
                        correct_answer=1,
                        explanation="УОР выступает инициатором проведения оценки, подготавливает данные и верифицирует результаты.",
                        source_context="Базовые знания",
                        difficulty="beginner",
                        confidence_score=0.9
                    ),
                    GeneratedQuestion(
                        question="Какие источники информации используются для оценки риска?",
                        options=[
                            "Только внутренние данные банка",
                            "Только внешние источники информации",
                            "Внутренние и внешние источники информации",
                            "Только данные СМИ"
                        ],
                        correct_answer=2,
                        explanation="Для оценки используются как внутренние данные банка, так и внешние источники информации.",
                        source_context="Базовые знания",
                        difficulty="intermediate",
                        confidence_score=0.9
                    )
                ],
                2: [
                    GeneratedQuestion(
                        question="Что включают в себя внутренние источники информации для оценки рисков?",
                        options=[
                            "Только данные о понесенных убытках",
                            "Данные о убытках, сценарии угроз и информацию об окружении процессов",
                            "Только информацию СМИ",
                            "Только геополитическую обстановку"
                        ],
                        correct_answer=1,
                        explanation="Внутренние источники включают данные о понесенных убытках от инцидентов, сценарии угроз от специализированных подразделений и информацию об окружении критически важных процессов.",
                        source_context="Базовые знания",
                        difficulty="intermediate",
                        confidence_score=0.9
                    ),
                    GeneratedQuestion(
                        question="Какие внешние источники используются для оценки рисков?",
                        options=[
                            "Только данные СМИ",
                            "СМИ, геополитическая обстановка и информация о реализации угроз в других организациях",
                            "Только геополитическая обстановка",
                            "Только внутренние отчеты банка"
                        ],
                        correct_answer=1,
                        explanation="Внешние источники включают данные СМИ о реализации угроз, геополитическую и эпидемиологическую обстановку, а также информацию о реализации угроз в других организациях.",
                        source_context="Базовые знания",
                        difficulty="intermediate",
                        confidence_score=0.9
                    )
                ],
                3: [
                    GeneratedQuestion(
                        question="Что такое инцидент нарушения непрерывности деятельности?",
                        options=[
                            "Любое событие в банке",
                            "Инцидент, который вызывает нарушение выполнения бизнес-процессов",
                            "Плановые технические работы",
                            "Обновление программного обеспечения"
                        ],
                        correct_answer=1,
                        explanation="Инцидент нарушения непрерывности - это инцидент, который вызывает или может вызвать нарушение/прекращение выполнения и взаимодействие бизнес-процессов.",
                        source_context="Базовые знания",
                        difficulty="intermediate",
                        confidence_score=0.9
                    )
                ]
            },
            "критичность_процессов": {
                1: [
                    GeneratedQuestion(
                        question="Что является объектом риска нарушения непрерывности деятельности?",
                        options=[
                            "Процесс категории 'Критически важный'",
                            "Любой бизнес-процесс банка",
                            "Только ИТ-процессы",
                            "Процессы обслуживания клиентов"
                        ],
                        correct_answer=0,
                        explanation="Объектом риска является процесс, категорированный как 'Критически важный'.",
                        source_context="Базовые знания",
                        difficulty="intermediate",
                        confidence_score=0.9
                    )
                ],
                2: [
                    GeneratedQuestion(
                        question="Что означает аббревиатура RTO?",
                        options=[
                            "Recovery Time Objective",
                            "Risk Transfer Operation",
                            "Rapid Technical Operation",
                            "Resource Time Optimization"
                        ],
                        correct_answer=0,
                        explanation="RTO (Recovery Time Objective) - целевое время восстановления процесса.",
                        source_context="Базовые знания",
                        difficulty="intermediate",
                        confidence_score=0.9
                    )
                ]
            }
        }
        
        questions = fallback_questions.get(topic, {}).get(lesson_id, [])
        
        # Если нет достаточно вопросов, генерируем базовые
        while len(questions) < count:
            if questions:
                # Дублируем существующий вопрос с небольшими изменениями
                base_question = questions[len(questions) % len(questions)]
                new_question = GeneratedQuestion(
                    question=f"Дополнительный вопрос: {base_question.question}",
                    options=base_question.options,
                    correct_answer=base_question.correct_answer,
                    explanation=base_question.explanation,
                    source_context=base_question.source_context,
                    difficulty=base_question.difficulty,
                    confidence_score=0.8
                )
                questions.append(new_question)
            else:
                # Создаем базовый вопрос
                questions.append(GeneratedQuestion(
                    question=f"Базовый вопрос {len(questions) + 1} по теме {topic}",
                    options=["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
                    correct_answer=0,
                    explanation="Базовое объяснение",
                    source_context="Автогенерация",
                    difficulty="beginner",
                    confidence_score=0.5
                ))
        
        return questions[:count]


# Глобальный экземпляр сервиса
adaptive_content_service = AdaptiveContentService()