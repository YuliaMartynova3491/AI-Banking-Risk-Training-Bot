"""
Узлы (nodes) для AI-агента на LangGraph - ИСПРАВЛЕННАЯ ВЕРСИЯ
- Использует новые централизованные сервисы
- Логика узлов стала чище и проще
"""
import logging
from typing import Dict, Any
from langchain_core.messages import AIMessage

from services.user_analysis_service import user_analysis_service
from services.adaptive_content_service import adaptive_content_service
from ai_agent.prompts import AGENT_PROMPTS

logger = logging.getLogger(__name__)


class AgentNodes:
    """Класс, содержащий все узлы AI-агента."""
    llm = None # Сюда будет передана LLM при инициализации

    @staticmethod
    def analyze_user_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел анализа пользователя. Получает данные из сервиса."""
        user_id = state.get("user_id")
        if not user_id:
            return {**state, "error": "User ID not provided"}
        
        try:
            logger.info(f"Анализирую пользователя {user_id}...")
            # ИСПОЛЬЗУЕМ НОВЫЙ СЕРВИС
            user_analysis = user_analysis_service.get_full_user_analysis(user_id)

            return {
                **state,
                "user_analysis": user_analysis,
                "messages": state.get("messages", []) + [AIMessage(content="Анализ профиля завершен.")]
            }
        except Exception as e:
            logger.error(f"Ошибка анализа пользователя {user_id}: {e}", exc_info=True)
            return {**state, "error": f"Analysis failed: {e}"}

    @staticmethod
    def provide_assistance_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел предоставления персонализированной помощи."""
        if not AgentNodes.llm:
            return {**state, "assistance_response": "AI-помощник временно недоступен."}
            
        try:
            user_question = state.get("user_question", "")
            user_analysis = state.get("user_analysis", {})
            user_profile = user_analysis.get("user_profile", {})
            topic = state.get("topic")

            # ИСПОЛЬЗУЕМ НОВЫЙ СЕРВИС для поиска
            relevant_content = adaptive_content_service.search_relevant_content(
                query=user_question, topic_filter=topic, n_results=3
            )
            context_text = "\n\n".join([item['document'] for item in relevant_content])

            prompt = AGENT_PROMPTS["personalized_help"].format(
                question=user_question,
                experience_level=user_profile.get("experience_level", "beginner"),
                learning_style=user_profile.get("support_needs", "medium"), # Упрощено
                relevant_content=context_text
            )
            
            response = AgentNodes.llm.invoke(prompt)
            
            return {**state, "assistance_response": response.content}
        except Exception as e:
            logger.error(f"Ошибка предоставления помощи: {e}", exc_info=True)
            return {**state, "assistance_response": "Не удалось обработать запрос."}

    @staticmethod
    def adapt_path_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел адаптации пути обучения."""
        if not AgentNodes.llm:
            return {**state, "adaptation_message": "Рекомендации временно недоступны."}
        
        try:
            user_analysis = state.get("user_analysis", {})
            prompt = AGENT_PROMPTS["progress_analysis"].format(
                progress_data=user_analysis.get("user_progress", {}),
                learning_patterns=user_analysis.get("learning_patterns", {})
            )
            
            response = AgentNodes.llm.invoke(prompt)

            return {
                **state,
                "adaptation_message": response.content,
                "adapted_difficulty": user_analysis.get("content_settings", {}).get("difficulty", "intermediate")
            }
        except Exception as e:
            logger.error(f"Ошибка адаптации пути: {e}", exc_info=True)
            return {**state, "adaptation_message": "Не удалось сгенерировать рекомендации."}