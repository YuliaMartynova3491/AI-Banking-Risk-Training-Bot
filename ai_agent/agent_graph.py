"""
AI-агент на LangGraph для персонализированного обучения (ИСПРАВЛЕННАЯ ВЕРСИЯ)
- Убрана дублирующаяся логика анализа (теперь в user_analysis_service)
- Упрощено создание state для запуска графа
- Убраны неиспользуемые методы
"""
import logging
from typing import Dict, Any, List, Optional, Annotated

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, AIMessage
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict

from config.settings import settings
from services.adaptive_content_service import adaptive_content_service
from ai_agent.agent_nodes import AgentNodes

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Состояние агента с правильной типизацией."""
    user_id: str
    messages: Annotated[List[BaseMessage], "Сообщения в истории"]
    intent: Optional[str]
    user_question: Optional[str]
    topic: Optional[str]
    lesson_id: Optional[int]
    # Результаты работы узлов
    user_analysis: Optional[Dict[str, Any]]
    assistance_response: Optional[str]
    adapted_difficulty: Optional[str]
    adaptation_message: Optional[str]
    error: Optional[str]


class LearningAIAgent:
    """AI-агент для персонализированного обучения."""

    def __init__(self):
        self.llm = None
        self.graph = None
        self._initialize()

    def _initialize(self):
        """Инициализация агента."""
        try:
            self.llm = ChatOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_api_base,
                model=settings.openai_model,
                temperature=0.7
            )
            AgentNodes.llm = self.llm # Передаем LLM в класс с узлами
            self.graph = self._create_agent_graph()
            logger.info("AI-агент успешно инициализирован.")
        except Exception as e:
            logger.error(f"Ошибка инициализации AI-агента: {e}")
            self.graph = None # Не создаем граф, если нет LLM

    def _create_agent_graph(self) -> StateGraph:
        """Создание графа AI-агента."""
        workflow = StateGraph(AgentState)
        workflow.add_node("analyze_user", AgentNodes.analyze_user_node)
        workflow.add_node("provide_assistance", AgentNodes.provide_assistance_node)
        workflow.add_node("adapt_path", AgentNodes.adapt_path_node)
        
        workflow.set_entry_point("analyze_user")
        
        workflow.add_conditional_edges(
            "analyze_user",
            self._route_after_analysis,
            {
                "assist": "provide_assistance",
                "adapt": "adapt_path",
                "end": END
            }
        )
        workflow.add_edge("provide_assistance", END)
        workflow.add_edge("adapt_path", END)
        
        return workflow.compile()

    def _route_after_analysis(self, state: AgentState) -> str:
        """Определяет следующий узел после анализа пользователя."""
        intent = state.get("intent", "assist")
        if intent == "assistance":
            return "assist"
        elif intent == "adapt_path":
            return "adapt"
        return "end"

    def _invoke_graph(self, initial_data: dict) -> dict:
        """Упрощенный запуск графа с начальными данными."""
        if not self.graph:
            return {"error": "AI-агент не инициализирован."}

        # Создаем состояние с полями по умолчанию
        state: AgentState = {
            "messages": [],
            "user_analysis": None,
            "assistance_response": None,
            "adapted_difficulty": None,
            "adaptation_message": None,
            "error": None,
            **initial_data # Перезаписываем поля из initial_data
        }
        
        try:
            return self.graph.invoke(state)
        except Exception as e:
            logger.error(f"Ошибка выполнения графа: {e}", exc_info=True)
            return {"error": str(e)}

    # --- Публичные методы для взаимодействия ---

    def provide_learning_assistance(self, user_id: str, question: str, topic: str = None, lesson_id: int = None) -> str:
        """Предоставление помощи и объяснений."""
        result = self._invoke_graph({
            "user_id": user_id,
            "user_question": question,
            "topic": topic,
            "lesson_id": lesson_id,
            "intent": "assistance"
        })
        return result.get("assistance_response", "Извините, произошла ошибка при обработке вашего вопроса.")

    def adapt_learning_path(self, user_id: str) -> Dict[str, Any]:
        """Адаптация пути обучения на основе прогресса."""
        result = self._invoke_graph({
            "user_id": user_id,
            "intent": "adapt_path"
        })
        return {
            "difficulty": result.get("adapted_difficulty", "intermediate"),
            "message": result.get("adaptation_message", ""),
            "recommendations": result.get("user_analysis", {}).get("recommendations", [])
        }
    
    def get_personalized_encouragement(self, user_id: str, score: float, is_improvement: bool = False) -> str:
        """Получение персонализированного поощрения (упрощено)."""
        if score >= 90:
            return "🌟 Превосходно! Вы демонстрируете отличное понимание материала!"
        elif score >= 80:
            return "🎉 Отличный результат! Вы хорошо усвоили материал!"
        elif is_improvement:
            return "📈 Заметен прогресс! Продолжайте в том же духе!"
        else:
            return "💪 Неплохо! Еще немного усилий и результат будет отличным!"

learning_agent = LearningAIAgent()