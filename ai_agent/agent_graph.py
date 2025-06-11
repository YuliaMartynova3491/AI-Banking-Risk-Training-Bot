"""
AI-агент на LangGraph для персонализированного обучения
"""
import logging
import traceback
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from ai_agent.agent_nodes import AgentNodes

logger = logging.getLogger(__name__)

# ИСПРАВЛЕНО: Правильная схема состояния для LangGraph
class AgentState(TypedDict):
    """Состояние агента для LangGraph"""
    # Входные данные
    user_id: str
    user_question: Optional[str]
    action_type: Optional[str]  # "assistance" или "generate_questions"
    topic: Optional[str]
    lesson_id: Optional[int]
    
    # Промежуточные данные
    user_analysis: Optional[Dict[str, Any]]
    
    # Выходные данные
    assistance_response: Optional[str]
    questions: Optional[List[Dict[str, Any]]]
    
    # Метаданные для отладки
    processing_steps: List[str]
    errors: List[str]
    execution_time: float

class LearningAIAgent:
    """AI-агент для персонализированного обучения - УПРОЩЕННАЯ ВЕРСИЯ"""
    
    def __init__(self):
        self.graph = None
        self.app = None
        self._build_graph()
    
    def _build_graph(self):
        """Построение графа агента с отладкой"""
        try:
            logger.info("🏗️ [AgentGraph] Начало построения графа агента...")
            
            # ИСПРАВЛЕНО: Используем TypedDict вместо dict
            workflow = StateGraph(AgentState)
            
            # Добавляем узлы агента
            workflow.add_node("analyze_user", AgentNodes.analyze_user_node)
            workflow.add_node("provide_assistance", AgentNodes.provide_assistance_node)
            
            # Определяем маршруты с логированием
            workflow.set_entry_point("analyze_user")
            
            # Условная логика маршрутизации
            workflow.add_conditional_edges(
                "analyze_user",
                self._route_after_analysis,
                {
                    "assistance": "provide_assistance",
                    "end": END
                }
            )
            
            workflow.add_edge("provide_assistance", END)
            
            # Компилируем граф
            self.app = workflow.compile()
            self.graph = workflow
            
            logger.info("✅ [AgentGraph] Граф агента успешно построен")
            
        except Exception as e:
            logger.error(f"❌ [AgentGraph] Ошибка построения графа: {e}")
            logger.error(f"Трейс: {traceback.format_exc()}")
            # НЕ поднимаем исключение, чтобы бот мог работать без агента
            self.graph = None
            self.app = None
    
    def _route_after_analysis(self, state: AgentState) -> str:
        """Маршрутизация после анализа пользователя"""
        action_type = state.get("action_type", "assistance")
        
        logger.info(f"🔀 [AgentGraph] Маршрутизация: action_type={action_type}")
        
        # Добавляем шаг в лог
        steps = state.get("processing_steps", [])
        steps.append(f"Анализ завершен, выбрано действие: {action_type}")
        state["processing_steps"] = steps
        
        if action_type == "assistance":
            return "assistance"
        else:
            logger.warning(f"⚠️ [AgentGraph] Неизвестный тип действия: {action_type}")
            return "end"
    
    def provide_learning_assistance(self, user_id: str, user_question: str, 
                                   topic: str = None, lesson_id: int = None) -> str:
        """УПРОЩЕННЫЙ МЕТОД: Обработка запроса помощи через агента"""
        logger.info(f"🎯 [AgentGraph] Запрос помощи от {user_id}: {user_question}")
        
        try:
            # Проверяем готовность агента
            if not self.app:
                logger.warning("⚠️ [AgentGraph] Граф агента недоступен, используем fallback")
                return self._get_fallback_response(user_question)
            
            # Подготавливаем входное состояние
            initial_state: AgentState = {
                "user_id": user_id,
                "user_question": user_question,
                "action_type": "assistance",
                "topic": topic,
                "lesson_id": lesson_id,
                "user_analysis": None,
                "assistance_response": None,
                "questions": None,
                "processing_steps": ["Запрос получен"],
                "errors": [],
                "execution_time": 0.0
            }
            
            # Выполняем граф агента
            final_state = self.app.invoke(initial_state)
            
            # Анализируем результат
            response = final_state.get("assistance_response")
            errors = final_state.get("errors", [])
            
            if response and len(response) > 10:
                logger.info(f"✅ [AgentGraph] Получен ответ агента: {response[:100]}...")
                return response
            else:
                logger.warning(f"⚠️ [AgentGraph] Агент не сгенерировал хороший ответ. Ошибки: {errors}")
                return self._get_fallback_response(user_question)
                
        except Exception as e:
            logger.error(f"❌ [AgentGraph] Ошибка выполнения агента: {e}")
            logger.error(f"Трейс: {traceback.format_exc()}")
            return self._get_fallback_response(user_question)
    
    def _get_fallback_response(self, user_question: str) -> str:
        """Запасной ответ когда агент недоступен"""
        question_lower = user_question.lower()
        
        # Простые ответы на основе ключевых слов
        if any(word in question_lower for word in ["риск", "risk"]):
            return "Риск нарушения непрерывности - это вероятность событий, которые могут прервать критически важные процессы банка. Изучите материалы урока для более подробной информации."
        
        elif any(word in question_lower for word in ["rto", "время восстановления"]):
            return "RTO (Recovery Time Objective) - это целевое время восстановления процесса после инцидента. Обычно измеряется в часах или днях."
        
        elif any(word in question_lower for word in ["mtpd", "период прерывания"]):
            return "MTPD (Maximum Tolerable Period of Disruption) - максимально допустимый период прерывания, после которого ущерб становится критическим."
        
        elif any(word in question_lower for word in ["угроза", "угрозы"]):
            return "Основные типы угроз: техногенные, природные, социальные, геополитические, экономические и биолого-социальные. Каждый тип требует своего подхода к оценке."
        
        elif any(word in question_lower for word in ["уор", "управление"]):
            return "УОР (Управление операционных рисков) - подразделение, которое инициирует и координирует оценку рисков нарушения непрерывности в банке."
        
        else:
            return "Изучите материалы урока для получения подробной информации по вашему вопросу. Если нужна дополнительная помощь, обратитесь к инструкции."
    
    def adapt_learning_path(self, user_id: str) -> Dict[str, Any]:
        """УПРОЩЕННАЯ ВЕРСИЯ: Адаптация пути обучения"""
        logger.info(f"🎯 [AgentGraph] Адаптация пути обучения для {user_id}")
        
        try:
            from core.database import db_service
            progress = db_service.get_user_progress_summary(user_id)
            
            total_completed = progress.total_lessons_completed
            avg_score = progress.total_score
            
            # Простая логика адаптации
            if total_completed == 0:
                message = "🎯 Начните с изучения основ рисков нарушения непрерывности. Это фундамент для понимания всей методики."
                difficulty = "beginner"
            elif avg_score >= 90:
                message = "🌟 Отличные результаты! Вы демонстрируете глубокое понимание материала. Продолжайте в том же духе!"
                difficulty = "advanced"
            elif avg_score >= 80:
                message = "✅ Хорошая работа! Вы успешно осваиваете материал. Рекомендуем закрепить знания на практических примерах."
                difficulty = "intermediate"
            elif avg_score >= 60:
                message = "📚 Рекомендуем уделить больше внимания изучению материалов перед тестированием. Используйте помощь AI-агента."
                difficulty = "beginner"
            else:
                message = "💪 Не сдавайтесь! Повторите пройденные уроки и обязательно изучите материалы. Обращайтесь за помощью к AI."
                difficulty = "beginner"
            
            return {
                "difficulty": difficulty,
                "message": message,
                "recommendations": [
                    "Изучайте материалы внимательно",
                    "Используйте помощь AI-агента при затруднениях",
                    "Повторяйте сложные темы"
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ [AgentGraph] Ошибка адаптации пути: {e}")
            return {
                "difficulty": "intermediate",
                "message": "Продолжайте изучение в текущем темпе!",
                "recommendations": ["Используйте все доступные материалы"]
            }
    
    def get_personalized_encouragement(self, user_id: str, score: float, is_improvement: bool = False) -> str:
        """Получение персонализированного поощрения"""
        if score >= 90:
            return "🌟 Превосходно! Вы демонстрируете отличное понимание материала!"
        elif score >= 80:
            return "🎉 Отличный результат! Вы хорошо усвоили материал!"
        elif score >= 70:
            return "👏 Хорошо! Продолжайте изучение, вы на правильном пути!"
        elif is_improvement:
            return "📈 Заметен прогресс! Продолжайте в том же духе!"
        else:
            return "💪 Неплохо! Еще немного усилий и результат будет отличным!"


# Глобальный экземпляр агента
learning_agent = LearningAIAgent()