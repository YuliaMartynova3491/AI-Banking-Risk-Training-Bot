"""
Узлы (nodes) для AI-агента на LangGraph
"""
import logging
import traceback
from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

class AgentNodes:
    llm = None
    knowledge_base = None
    
    @classmethod
    def initialize_llm(cls):
        """Инициализация LLM с детальным логированием"""
        if cls.llm is None:
            try:
                from config.settings import settings
                from langchain_openai import ChatOpenAI
                
                logger.info("🤖 Инициализация LLM агента...")
                
                # Проверяем наличие API ключа
                if not settings.openai_api_key:
                    logger.error("❌ OPENAI_API_KEY не найден в настройках!")
                    return False
                
                # Создаем LLM с timeout и retry
                cls.llm = ChatOpenAI(
                    model=settings.openai_model,
                    api_key=settings.openai_api_key,
                    temperature=0.3,
                    max_tokens=1000,
                    timeout=30,  # 30 секунд timeout
                    max_retries=3  # 3 попытки
                )
                
                # Тестируем LLM
                test_response = cls.llm.invoke([HumanMessage(content="Тест")])
                logger.info(f"✅ LLM агент инициализирован успешно: {test_response.content[:50]}...")
                return True
                
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации LLM агента: {e}")
                logger.error(f"Трейс: {traceback.format_exc()}")
                cls.llm = None
                return False
    
    @staticmethod
    def provide_assistance_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """ИСПРАВЛЕНО: Детальная отладка помощника агента"""
        logger.info("🎯 [AgentNodes] Узел помощника начал работу")
        logger.info(f"🔍 [AgentNodes] Входящее состояние: {list(state.keys())}")
        
        user_question = state.get("user_question", "")
        if not user_question:
            logger.warning("⚠️ [AgentNodes] Пустой вопрос пользователя")
            return {**state, "assistance_response": "Задайте конкретный вопрос для получения помощи."}
        
        logger.info(f"❓ [AgentNodes] Вопрос пользователя: '{user_question}'")
        
        try:
            # Инициализируем LLM если нужно
            if not AgentNodes.llm:
                logger.info("🔄 [AgentNodes] Инициализация LLM...")
                if not AgentNodes.initialize_llm():
                    logger.error("❌ [AgentNodes] LLM недоступен")
                    return {**state, "assistance_response": "Сервис временно недоступен. Попробуйте позже."}
            
            # Получаем анализ пользователя и контекст
            user_analysis = state.get("user_analysis", {})
            topic = state.get("topic")
            lesson_id = state.get("lesson_id")
            
            logger.info(f"👤 [AgentNodes] Анализ пользователя: {user_analysis}")
            logger.info(f"📚 [AgentNodes] Контекст: тема={topic}, урок={lesson_id}")
            
            # Поиск релевантного контента
            relevant_content = AgentNodes._search_knowledge_base(user_question, topic)
            
            if not relevant_content:
                logger.warning("⚠️ [AgentNodes] Релевантный контент не найден")
                return {**state, "assistance_response": "Не удалось найти релевантную информацию. Обратитесь к материалам урока."}
            
            logger.info(f"📖 [AgentNodes] Найдено {len(relevant_content)} релевантных документов")
            
            # Формируем расширенный промпт для агента
            system_prompt = AgentNodes._build_agent_system_prompt(user_analysis, topic, lesson_id)
            context_prompt = AgentNodes._build_context_prompt(relevant_content, user_question)
            
            logger.info("🧠 [AgentNodes] Отправляем запрос к LLM агенту...")
            
            # Вызываем LLM агент
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=context_prompt)
            ]
            
            response = AgentNodes.llm.invoke(messages)
            
            if not response or not response.content:
                logger.error("❌ [AgentNodes] Пустой ответ от LLM")
                return {**state, "assistance_response": "Не удалось получить ответ. Попробуйте переформулировать вопрос."}
            
            clean_response = AgentNodes._clean_agent_response(response.content)
            logger.info(f"✅ [AgentNodes] Получен ответ агента: {clean_response[:100]}...")
            
            return {**state, "assistance_response": clean_response}
            
        except Exception as e:
            logger.error(f"❌ [AgentNodes] Критическая ошибка в узле помощника: {e}")
            logger.error(f"Трейс: {traceback.format_exc()}")
            return {**state, "assistance_response": "Произошла ошибка при обработке запроса. Попробуйте еще раз."}
    
    @staticmethod
    def _search_knowledge_base(query: str, topic_filter: str = None) -> list:
        """Поиск в базе знаний с отладкой"""
        try:
            logger.info(f"🔍 [Knowledge] Поиск в базе знаний: '{query}', фильтр={topic_filter}")
            
            from services.adaptive_content_service import adaptive_content_service
            
            results = adaptive_content_service.search_relevant_content(
                query=query,
                topic_filter=topic_filter,
                n_results=3  # Больше контекста для агента
            )
            
            logger.info(f"📚 [Knowledge] Найдено {len(results)} результатов")
            return results
            
        except Exception as e:
            logger.error(f"❌ [Knowledge] Ошибка поиска: {e}")
            return []
    
    @staticmethod
    def _build_agent_system_prompt(user_analysis: dict, topic: str, lesson_id: int) -> str:
        """УЛУЧШЕННЫЙ системный промпт для агента"""
        
        # Анализ уровня пользователя
        user_level = user_analysis.get('knowledge_level', 'beginner')
        weak_areas = user_analysis.get('weak_knowledge_areas', [])
        learning_style = user_analysis.get('learning_style', 'visual')
        
        prompt = f"""Ты - экспертный AI-агент по банковским рискам и обеспечению непрерывности деятельности.

КОНТЕКСТ ОБУЧЕНИЯ:
- Текущая тема: {topic}
- Урок: {lesson_id}
- Уровень пользователя: {user_level}
- Слабые области: {', '.join(weak_areas) if weak_areas else 'не выявлены'}
- Стиль обучения: {learning_style}

ТВОЯ РОЛЬ:
1. Анализируй вопрос в контексте банковских рисков
2. Давай экспертные ответы с примерами из банковской практики
3. Адаптируй сложность под уровень пользователя
4. Учитывай слабые области при объяснении
5. Используй терминологию из области управления рисками

ПРИНЦИПЫ ОТВЕТОВ:
- Точность и профессионализм
- Практические примеры из банковской сферы
- Связь с нормативными требованиями (если применимо)
- Структурированность (используй нумерацию, разделение на пункты)
- Мотивация к дальнейшему изучению

Отвечай ТОЛЬКО на русском языке. Максимум 500 слов."""

        return prompt
    
    @staticmethod
    def _build_context_prompt(relevant_content: list, user_question: str) -> str:
        """Построение контекстного промпта с релевантной информацией"""
        
        context_parts = []
        for i, content in enumerate(relevant_content[:3], 1):
            doc_text = content.get('document', '')[:500]  # Ограничиваем размер
            context_parts.append(f"Источник {i}:\n{doc_text}")
        
        context_text = "\n\n".join(context_parts)
        
        prompt = f"""РЕЛЕВАНТНАЯ ИНФОРМАЦИЯ ИЗ БАЗЫ ЗНАНИЙ:
{context_text}

ВОПРОС ПОЛЬЗОВАТЕЛЯ: {user_question}

Проанализируй вопрос и дай экспертный ответ, используя информацию из базы знаний. Если информации недостаточно, дополни своими знаниями о банковских рисках."""

        return prompt
    
    @staticmethod
    def _clean_agent_response(response: str) -> str:
        """Очистка ответа агента"""
        if not response:
            return "Не удалось сформировать ответ."
        
        # Убираем лишние переносы и пробелы
        cleaned = response.strip()
        
        # Ограничиваем длину
        if len(cleaned) > 1000:
            cleaned = cleaned[:1000] + "..."
        
        return cleaned

    @staticmethod
    def generate_questions_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """ИСПРАВЛЕНО: Детальная отладка генерации вопросов агентом"""
        logger.info("📝 [AgentNodes] Узел генерации вопросов начал работу")
        
        try:
            user_id = state.get("user_id")
            topic = state.get("topic")
            lesson_id = state.get("lesson_id")
            
            if not all([user_id, topic, lesson_id]):
                logger.error(f"❌ [AgentNodes] Недостаточно данных: user_id={user_id}, topic={topic}, lesson_id={lesson_id}")
                return {**state, "questions": []}
            
            logger.info(f"📚 [AgentNodes] Генерация вопросов для: пользователь={user_id}, тема={topic}, урок={lesson_id}")
            
            from services.adaptive_content_service import adaptive_content_service
            
            # Генерируем адаптивные вопросы через сервис
            questions = adaptive_content_service.generate_adaptive_questions(
                user_id=user_id,
                topic=topic,
                lesson_id=lesson_id
            )
            
            if not questions:
                logger.warning("⚠️ [AgentNodes] Не удалось сгенерировать вопросы")
                return {**state, "questions": []}
            
            logger.info(f"✅ [AgentNodes] Сгенерировано {len(questions)} вопросов")
            return {**state, "questions": questions}
            
        except Exception as e:
            logger.error(f"❌ [AgentNodes] Ошибка генерации вопросов: {e}")
            logger.error(f"Трейс: {traceback.format_exc()}")
            return {**state, "questions": []}