# Файл: services/adaptive_content_service.py

"""
НОВЫЙ ФАЙЛ
Сервис для работы с базой знаний и адаптивной генерации контента (вопросов, объяснений).
Объединяет логику RAG и генерации вопросов.
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
from core.knowledge_base import get_knowledge_base  # <-- ВОТ ЭТА СТРОКА ИСПРАВЛЕНА

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
        Основной метод для генерации адаптивных вопросов для квиза.
        """
        try:
            analysis = user_analysis_service.get_full_user_analysis(user_id)
            content_settings = analysis.get("content_settings", {})
            difficulty = content_settings.get("difficulty", "intermediate")
            count = content_settings.get("question_count", settings.questions_per_lesson)

            logger.info(f"Генерация {count} вопросов для {user_id} по теме {topic}, сложность: {difficulty}")

            self._initialize_llm()
            if self.llm:
                questions = self._generate_questions_with_llm(topic, lesson_id, difficulty, count)
                if questions:
                    return [q.dict() for q in questions]

            # Fallback к статическим вопросам, если LLM не сработал
            logger.warning(f"Используется fallback-метод генерации вопросов для {user_id}")
            return [q.dict() for q in self._get_fallback_questions(topic, lesson_id, count)]

        except Exception as e:
            logger.error(f"Критическая ошибка генерации вопросов: {e}")
            return [q.dict() for q in self._get_fallback_questions(topic, lesson_id, 3)]

    def _generate_questions_with_llm(self, topic: str, lesson_id: int, difficulty: str, count: int) -> Optional[List[GeneratedQuestion]]:
        """Генерация вопросов с помощью LLM и RAG."""
        try:
            relevant_docs = self.knowledge_base.search(f"{topic} урок {lesson_id}", n_results=5, topic_filter=topic)
            if not relevant_docs:
                logger.warning("Не найдены релевантные документы для генерации вопросов с LLM.")
                return None
            
            context_text = "\n\n".join([doc['document'] for doc in relevant_docs])

            prompt = ChatPromptTemplate.from_template(
                """На основе предоставленного контекста сгенерируй {count} вопросов.
                
                Контекст:
                {context}
                
                Требования:
                - Сложность: {difficulty}
                - Формат: JSON-массив объектов.
                - Каждый объект: {{"question": "...", "options": ["...", "...", "..."], "correct_answer": 0, "explanation": "..."}}
                - Вопросы должны быть на русском языке.
                """
            )
            # В pydantic_object нужно передавать саму модель, а не ее экземпляр
            parser = JsonOutputParser(pydantic_object=GeneratedQuestion)
            chain = prompt | self.llm | parser

            # В новых версиях chain.invoke может вернуть один объект, а не список
            response = chain.invoke({
                "context": context_text,
                "difficulty": difficulty,
                "count": count
            })

            if not isinstance(response, list):
                response = [response]

            return response
        except Exception as e:
            logger.error(f"Ошибка при генерации вопросов с LLM: {e}")
            return None

    def _get_fallback_questions(self, topic: str, lesson_id: int, count: int) -> List[GeneratedQuestion]:
        """Получение статических вопросов из базы знаний."""
        all_docs = self.knowledge_base.get_documents_by_topic(topic)
        # Учтем, что lesson_id в метаданных может быть строкой
        lesson_docs = [doc for doc in all_docs if doc.get('metadata', {}).get('lesson') == str(lesson_id)]
        
        questions = []
        for doc in lesson_docs:
            try:
                prompt_text = doc['metadata'].get('prompt')
                correct_answer_text = doc['document'].split("Ответ:")[1].strip()
                
                other_docs = [d for d in all_docs if d['document'] != doc['document']]
                options = [correct_answer_text]
                
                if len(other_docs) >= 3:
                    wrong_options = [d['document'].split("Ответ:")[1].strip() for d in random.sample(other_docs, 3)]
                    options.extend(wrong_options)
                
                random.shuffle(options)
                correct_index = options.index(correct_answer_text)

                questions.append(GeneratedQuestion(
                    question=prompt_text,
                    options=options,
                    correct_answer=correct_index,
                    explanation=correct_answer_text,
                    source_context=doc['document'][:200],
                    difficulty=doc['metadata'].get('difficulty', 'intermediate'),
                    confidence_score=0.95
                ))
            except (KeyError, IndexError) as e:
                logger.warning(f"Не удалось сформировать fallback-вопрос из документа: {e}")
                continue
        
        return questions[:count] if questions else []


adaptive_content_service = AdaptiveContentService()