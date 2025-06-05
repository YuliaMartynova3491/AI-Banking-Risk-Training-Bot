"""
AI-агент на LangGraph для персонализированного обучения
"""
import logging
from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict

from config.settings import settings
from services.rag_service import rag_service
from core.database import db_service
from config.bot_config import LEARNING_STRUCTURE

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Состояние агента"""
    user_id: str
    messages: List[BaseMessage]
    user_progress: Optional[Dict[str, Any]]
    user_analysis: Optional[Dict[str, Any]]
    learning_style: Optional[Dict[str, Any]]
    content_preferences: Optional[Dict[str, Any]]
    generated_questions: Optional[List[Dict[str, Any]]]
    assistance_response: Optional[str]
    adapted_difficulty: Optional[str]
    adaptation_message: Optional[str]
    topic: Optional[str]
    lesson_id: Optional[int]
    user_question: Optional[str]
    intent: Optional[str]
    current_difficulty: Optional[str]
    error: Optional[str]


class LearningAIAgent:
    """AI-агент для персонализированного обучения"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
            model=settings.openai_model,
            temperature=0.7
        )
        
        # Создаем граф агента
        self.graph = self._create_agent_graph()
    
    def _create_agent_graph(self) -> StateGraph:
        """Создание графа AI-агента"""
        
        # Создаем StateGraph
        workflow = StateGraph(AgentState)
        
        # Добавляем узлы
        workflow.add_node("analyze_user", self._analyze_user_node)
        workflow.add_node("personalize_content", self._personalize_content_node)
        workflow.add_node("generate_questions", self._generate_questions_node)
        workflow.add_node("provide_assistance", self._provide_assistance_node)
        workflow.add_node("adapt_difficulty", self._adapt_difficulty_node)
        
        # Определяем точку входа
        workflow.set_entry_point("analyze_user")
        
        # Добавляем рёбра (переходы между узлами)
        workflow.add_edge("analyze_user", "personalize_content")
        workflow.add_conditional_edges(
            "personalize_content",
            self._route_after_personalization,
            {
                "generate_questions": "generate_questions",
                "provide_assistance": "provide_assistance",
                "adapt_difficulty": "adapt_difficulty"
            }
        )
        workflow.add_edge("generate_questions", END)
        workflow.add_edge("provide_assistance", END)
        workflow.add_edge("adapt_difficulty", "generate_questions")
        
        return workflow.compile()
    
    def _analyze_user_node(self, state: AgentState) -> AgentState:
        """Узел анализа пользователя и его прогресса"""
        user_id = state.get("user_id")
        
        if not user_id:
            new_state = dict(state)
            new_state["error"] = "User ID not provided"
            return new_state
        
        try:
            # Получаем прогресс пользователя
            progress_summary = db_service.get_user_progress_summary(user_id)
            
            # Анализируем успеваемость
            user_analysis = self._perform_user_analysis(progress_summary)
            
            new_state = dict(state)
            new_state["user_progress"] = progress_summary.dict()
            new_state["user_analysis"] = user_analysis
            new_state["messages"] = state.get("messages", []) + [AIMessage(content="Анализирую ваш прогресс обучения...")]
            
            return new_state
            
        except Exception as e:
            logger.error(f"Ошибка анализа пользователя {user_id}: {e}")
            new_state = dict(state)
            new_state["error"] = f"Analysis failed: {str(e)}"
            return new_state
    
    def _personalize_content_node(self, state: AgentState) -> AgentState:
        """Узел персонализации контента"""
        user_analysis = state.get("user_analysis", {})
        user_progress = state.get("user_progress", {})
        
        # Определяем персонализированный подход
        learning_style = self._determine_learning_style(user_analysis)
        content_preferences = self._get_content_preferences(user_progress)
        
        new_state = dict(state)
        new_state["learning_style"] = learning_style
        new_state["content_preferences"] = content_preferences
        new_state["messages"] = state.get("messages", []) + [AIMessage(content="Подготавливаю персонализированный контент...")]
        
        return new_state
    
    def _generate_questions_node(self, state: AgentState) -> AgentState:
        """Узел генерации вопросов"""
        user_id = state.get("user_id")
        topic = state.get("topic")
        lesson_id = state.get("lesson_id")
        user_analysis = state.get("user_analysis", {})
        
        try:
            # Генерируем адаптивные вопросы
            questions = rag_service.get_adaptive_questions(
                user_id=user_id,
                topic=topic,
                lesson_id=lesson_id,
                user_performance=user_analysis
            )
            
            new_state = dict(state)
            new_state["generated_questions"] = [q.dict() for q in questions]
            new_state["messages"] = state.get("messages", []) + [AIMessage(content=f"Сгенерировано {len(questions)} вопросов для вашего уровня")]
            
            return new_state
            
        except Exception as e:
            logger.error(f"Ошибка генерации вопросов: {e}")
            new_state = dict(state)
            new_state["error"] = f"Question generation failed: {str(e)}"
            return new_state
    
    def _provide_assistance_node(self, state: AgentState) -> AgentState:
        """Узел предоставления помощи и объяснений"""
        user_question = state.get("user_question", "")
        topic = state.get("topic")
        lesson_id = state.get("lesson_id")
        
        try:
            # Поиск релевантной информации
            relevant_content = rag_service.search_relevant_content(
                query=user_question,
                topic=topic,
                lesson=lesson_id,
                n_results=3
            )
            
            # Простой ответ на основе найденного контента
            if relevant_content:
                context = relevant_content[0].get('document', '')
                if 'Ответ:' in context:
                    answer_part = context.split('Ответ:')[1].strip()
                    response_text = answer_part[:500]  # Ограничиваем длину
                else:
                    response_text = "Информация найдена в учебных материалах."
            else:
                response_text = "К сожалению, не могу найти ответ на ваш вопрос. Попробуйте переформулировать."
            
            new_state = dict(state)
            new_state["assistance_response"] = response_text
            new_state["messages"] = state.get("messages", []) + [AIMessage(content="Подготовил объяснение для вас...")]
            
            return new_state
            
        except Exception as e:
            logger.error(f"Ошибка предоставления помощи: {e}")
            new_state = dict(state)
            new_state["assistance_response"] = "К сожалению, не могу найти ответ на ваш вопрос. Попробуйте переформулировать."
            new_state["error"] = str(e)
            return new_state
    
    def _adapt_difficulty_node(self, state: AgentState) -> AgentState:
        """Узел адаптации сложности"""
        user_analysis = state.get("user_analysis", {})
        current_difficulty = state.get("current_difficulty", "intermediate")
        
        # Анализируем необходимость изменения сложности
        avg_score = user_analysis.get("average_score", 70)
        recent_attempts = user_analysis.get("recent_attempts", 0)
        
        new_difficulty = current_difficulty
        adaptation_message = ""
        
        if recent_attempts >= 3:
            if avg_score >= 90:
                new_difficulty = "advanced"
                adaptation_message = "Повышаю сложность - вы отлично справляетесь!"
            elif avg_score <= 60:
                new_difficulty = "beginner"
                adaptation_message = "Снижаю сложность для лучшего усвоения материала"
            else:
                new_difficulty = "intermediate"
                adaptation_message = "Оставляю средний уровень сложности"
        
        new_state = dict(state)
        new_state["adapted_difficulty"] = new_difficulty
        new_state["adaptation_message"] = adaptation_message
        if adaptation_message:
            new_state["messages"] = state.get("messages", []) + [AIMessage(content=adaptation_message)]
        
        return new_state
    
    def _route_after_personalization(self, state: AgentState) -> str:
        """Определяет следующий узел после персонализации"""
        intent = state.get("intent", "generate_questions")
        
        if intent == "help" or intent == "assistance":
            return "provide_assistance"
        elif intent == "adapt_difficulty":
            return "adapt_difficulty"
        else:
            return "generate_questions"
    
    def _perform_user_analysis(self, progress_summary) -> Dict[str, Any]:
        """Анализ успеваемости и характеристик пользователя"""
        topics_progress = progress_summary.topics_progress
        
        # Вычисляем общую статистику
        total_completed = sum(
            topic.get("completed_lessons", 0) 
            for topic in topics_progress.values()
        )
        
        total_attempts = sum(
            topic.get("total_attempts", 0) 
            for topic in topics_progress.values()
        )
        
        # Средняя оценка
        all_scores = []
        for topic_data in topics_progress.values():
            for lesson_data in topic_data.get("lessons", {}).values():
                if lesson_data.get("is_completed"):
                    all_scores.append(lesson_data.get("best_score", 0))
        
        average_score = sum(all_scores) / len(all_scores) if all_scores else 0
        
        # Определяем слабые места
        weak_areas = []
        for topic_id, topic_data in topics_progress.items():
            topic_scores = [
                lesson.get("best_score", 0) 
                for lesson in topic_data.get("lessons", {}).values()
                if lesson.get("is_completed")
            ]
            if topic_scores and sum(topic_scores) / len(topic_scores) < 70:
                weak_areas.append(topic_id)
        
        # Анализ скорости обучения
        learning_speed = "normal"
        if total_attempts > 0:
            success_rate = total_completed / total_attempts
            if success_rate > 0.8:
                learning_speed = "fast"
            elif success_rate < 0.5:
                learning_speed = "slow"
        
        return {
            "total_completed": total_completed,
            "total_attempts": total_attempts,
            "average_score": average_score,
            "weak_areas": weak_areas,
            "learning_speed": learning_speed,
            "recent_attempts": min(total_attempts, 5)  # Последние 5 попыток
        }
    
    def _determine_learning_style(self, user_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Определение стиля обучения пользователя"""
        learning_speed = user_analysis.get("learning_speed", "normal")
        average_score = user_analysis.get("average_score", 70)
        
        style = {
            "pace": learning_speed,
            "support_level": "high" if average_score < 70 else "medium",
            "explanation_detail": "detailed" if average_score < 80 else "concise",
            "encouragement_frequency": "high" if average_score < 70 else "medium"
        }
        
        return style
    
    def _get_content_preferences(self, user_progress: Dict[str, Any]) -> Dict[str, Any]:
        """Определение предпочтений по контенту"""
        current_topic = user_progress.get("current_topic")
        current_lesson = user_progress.get("current_lesson", 1)
        
        # Получаем информацию о текущем уроке
        lesson_info = None
        if current_topic and current_topic in LEARNING_STRUCTURE:
            topic_data = LEARNING_STRUCTURE[current_topic]
            for lesson in topic_data["lessons"]:
                if lesson["id"] == current_lesson:
                    lesson_info = lesson
                    break
        
        return {
            "current_topic": current_topic,
            "current_lesson": current_lesson,
            "lesson_info": lesson_info,
            "focus_keywords": lesson_info.get("keywords", []) if lesson_info else []
        }
    
    # Основные методы для взаимодействия с ботом
    
    def generate_adaptive_questions(self, user_id: str, topic: str, lesson_id: int) -> List[Dict[str, Any]]:
        """Генерация адаптивных вопросов для пользователя"""
        try:
            state: AgentState = {
                "user_id": user_id,
                "messages": [],
                "topic": topic,
                "lesson_id": lesson_id,
                "intent": "generate_questions",
                "user_progress": None,
                "user_analysis": None,
                "learning_style": None,
                "content_preferences": None,
                "generated_questions": None,
                "assistance_response": None,
                "adapted_difficulty": None,
                "adaptation_message": None,
                "user_question": None,
                "current_difficulty": None,
                "error": None
            }
            
            result = self.graph.invoke(state)
            return result.get("generated_questions", [])
            
        except Exception as e:
            logger.error(f"Ошибка генерации адаптивных вопросов: {e}")
            return []
    
    def provide_learning_assistance(self, user_id: str, question: str, 
                                  topic: str = None, lesson_id: int = None) -> str:
        """Предоставление помощи и объяснений"""
        try:
            state: AgentState = {
                "user_id": user_id,
                "messages": [],
                "user_question": question,
                "topic": topic,
                "lesson_id": lesson_id,
                "intent": "assistance",
                "user_progress": None,
                "user_analysis": None,
                "learning_style": None,
                "content_preferences": None,
                "generated_questions": None,
                "assistance_response": None,
                "adapted_difficulty": None,
                "adaptation_message": None,
                "current_difficulty": None,
                "error": None
            }
            
            result = self.graph.invoke(state)
            return result.get("assistance_response", "Извините, не могу помочь с этим вопросом.")
            
        except Exception as e:
            logger.error(f"Ошибка предоставления помощи: {e}")
            return "Произошла ошибка при обработке вашего вопроса."
    
    def adapt_learning_path(self, user_id: str) -> Dict[str, Any]:
        """Адаптация пути обучения на основе прогресса"""
        try:
            state: AgentState = {
                "user_id": user_id,
                "messages": [],
                "intent": "adapt_difficulty",
                "user_progress": None,
                "user_analysis": None,
                "learning_style": None,
                "content_preferences": None,
                "generated_questions": None,
                "assistance_response": None,
                "adapted_difficulty": None,
                "adaptation_message": None,
                "topic": None,
                "lesson_id": None,
                "user_question": None,
                "current_difficulty": None,
                "error": None
            }
            
            result = self.graph.invoke(state)
            
            return {
                "difficulty": result.get("adapted_difficulty", "intermediate"),
                "message": result.get("adaptation_message", ""),
                "recommendations": self._get_learning_recommendations(result)
            }
            
        except Exception as e:
            logger.error(f"Ошибка адаптации пути обучения: {e}")
            return {"difficulty": "intermediate", "message": "", "recommendations": []}
    
    def _get_learning_recommendations(self, agent_result: Dict[str, Any]) -> List[str]:
        """Получение рекомендаций по обучению"""
        recommendations = []
        user_analysis = agent_result.get("user_analysis", {})
        
        avg_score = user_analysis.get("average_score", 70)
        weak_areas = user_analysis.get("weak_areas", [])
        learning_speed = user_analysis.get("learning_speed", "normal")
        
        if avg_score < 70:
            recommendations.append("Рекомендуем повторить пройденный материал")
            recommendations.append("Обратитесь за помощью к AI-помощнику при затруднениях")
        
        if weak_areas:
            topic_names = {
                "основы_рисков": "основы рисков",
                "критичность_процессов": "критичность процессов", 
                "оценка_рисков": "оценка рисков"
            }
            for area in weak_areas:
                topic_name = topic_names.get(area, area)
                recommendations.append(f"Уделите больше внимания теме: {topic_name}")
        
        if learning_speed == "slow":
            recommendations.append("Не торопитесь, изучайте материал в удобном темпе")
            recommendations.append("Делайте паузы между уроками для лучшего усвоения")
        elif learning_speed == "fast":
            recommendations.append("Вы быстро усваиваете материал - отлично!")
            recommendations.append("Попробуйте более сложные задания")
        
        return recommendations
    
    def get_personalized_encouragement(self, user_id: str, score: float, 
                                     is_improvement: bool = False) -> str:
        """Получение персонализированного поощрения"""
        try:
            # Получаем анализ пользователя для персонализации
            progress_summary = db_service.get_user_progress_summary(user_id)
            user_analysis = self._perform_user_analysis(progress_summary)
            
            avg_score = user_analysis.get("average_score", 70)
            learning_speed = user_analysis.get("learning_speed", "normal")
            
            if score >= 90:
                if learning_speed == "fast":
                    return "🌟 Превосходно! Вы демонстрируете отличное понимание материала!"
                else:
                    return "🎉 Отличный результат! Вы хорошо усвоили материал!"
            elif score >= 80:
                if is_improvement:
                    return "📈 Заметен прогресс! Продолжайте в том же духе!"
                else:
                    return "✅ Хороший результат! Вы на правильном пути!"
            elif score >= 60:
                return "💪 Неплохо! Еще немного усилий и результат будет отличным!"
            else:
                if avg_score > score + 10:
                    return "🤔 Возможно, стоит повторить материал. Вы можете лучше!"
                else:
                    return "📚 Не расстраивайтесь! Изучение требует времени. Попробуйте еще раз!"
            
        except Exception as e:
            logger.error(f"Ошибка генерации поощрения: {e}")
            return "Продолжайте обучение!"


# Глобальный экземпляр агента
learning_agent = LearningAIAgent()(self, state: AgentState) -> str:
        """Определяет следующий узел после персонализации"""
        intent = state.get("intent", "generate_questions")
        
        if intent == "help" or intent == "assistance":
            return "provide_assistance"
        elif intent == "adapt_difficulty":
            return "adapt_difficulty"
        else:
            return "generate_questions"
    
    def _perform_user_analysis(self, progress_summary) -> Dict[str, Any]:
        """Анализ успеваемости и характеристик пользователя"""
        topics_progress = progress_summary.topics_progress
        
        # Вычисляем общую статистику
        total_completed = sum(
            topic.get("completed_lessons", 0) 
            for topic in topics_progress.values()
        )
        
        total_attempts = sum(
            topic.get("total_attempts", 0) 
            for topic in topics_progress.values()
        )
        
        # Средняя оценка
        all_scores = []
        for topic_data in topics_progress.values():
            for lesson_data in topic_data.get("lessons", {}).values():
                if lesson_data.get("is_completed"):
                    all_scores.append(lesson_data.get("best_score", 0))
        
        average_score = sum(all_scores) / len(all_scores) if all_scores else 0
        
        # Определяем слабые места
        weak_areas = []
        for topic_id, topic_data in topics_progress.items():
            topic_scores = [
                lesson.get("best_score", 0) 
                for lesson in topic_data.get("lessons", {}).values()
                if lesson.get("is_completed")
            ]
            if topic_scores and sum(topic_scores) / len(topic_scores) < 70:
                weak_areas.append(topic_id)
        
        # Анализ скорости обучения
        learning_speed = "normal"
        if total_attempts > 0:
            success_rate = total_completed / total_attempts
            if success_rate > 0.8:
                learning_speed = "fast"
            elif success_rate < 0.5:
                learning_speed = "slow"
        
        return {
            "total_completed": total_completed,
            "total_attempts": total_attempts,
            "average_score": average_score,
            "weak_areas": weak_areas,
            "learning_speed": learning_speed,
            "recent_attempts": min(total_attempts, 5)  # Последние 5 попыток
        }
    
    def _determine_learning_style(self, user_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Определение стиля обучения пользователя"""
        learning_speed = user_analysis.get("learning_speed", "normal")
        average_score = user_analysis.get("average_score", 70)
        
        style = {
            "pace": learning_speed,
            "support_level": "high" if average_score < 70 else "medium",
            "explanation_detail": "detailed" if average_score < 80 else "concise",
            "encouragement_frequency": "high" if average_score < 70 else "medium"
        }
        
        return style
    
    def _get_content_preferences(self, user_progress: Dict[str, Any]) -> Dict[str, Any]:
        """Определение предпочтений по контенту"""
        current_topic = user_progress.get("current_topic")
        current_lesson = user_progress.get("current_lesson", 1)
        
        # Получаем информацию о текущем уроке
        lesson_info = None
        if current_topic and current_topic in LEARNING_STRUCTURE:
            topic_data = LEARNING_STRUCTURE[current_topic]
            for lesson in topic_data["lessons"]:
                if lesson["id"] == current_lesson:
                    lesson_info = lesson
                    break
        
        return {
            "current_topic": current_topic,
            "current_lesson": current_lesson,
            "lesson_info": lesson_info,
            "focus_keywords": lesson_info.get("keywords", []) if lesson_info else []
        }
    
    # Основные методы для взаимодействия с ботом
    
    def generate_adaptive_questions(self, user_id: str, topic: str, lesson_id: int) -> List[Dict[str, Any]]:
        """Генерация адаптивных вопросов для пользователя"""
        try:
            state = AgentState(
                messages=[],
                user_id=user_id,
                topic=topic,
                lesson_id=lesson_id,
                intent="generate_questions",
                user_progress=None,
                user_analysis=None,
                learning_style=None,
                content_preferences=None,
                generated_questions=None,
                assistance_response=None,
                adapted_difficulty=None,
                adaptation_message=None,
                user_question=None,
                current_difficulty=None,
                error=None
            )
            
            result = self.graph.invoke(state)
            return result.get("generated_questions", [])
            
        except Exception as e:
            logger.error(f"Ошибка генерации адаптивных вопросов: {e}")
            return []
    
    def provide_learning_assistance(self, user_id: str, question: str, 
                                  topic: str = None, lesson_id: int = None) -> str:
        """Предоставление помощи и объяснений"""
        try:
            state = AgentState(
                messages=[],
                user_id=user_id,
                user_question=question,
                topic=topic,
                lesson_id=lesson_id,
                intent="assistance",
                user_progress=None,
                user_analysis=None,
                learning_style=None,
                content_preferences=None,
                generated_questions=None,
                assistance_response=None,
                adapted_difficulty=None,
                adaptation_message=None,
                current_difficulty=None,
                error=None
            )
            
            result = self.graph.invoke(state)
            return result.get("assistance_response", "Извините, не могу помочь с этим вопросом.")
            
        except Exception as e:
            logger.error(f"Ошибка предоставления помощи: {e}")
            return "Произошла ошибка при обработке вашего вопроса."
    
    def adapt_learning_path(self, user_id: str) -> Dict[str, Any]:
        """Адаптация пути обучения на основе прогресса"""
        try:
            state = AgentState(
                messages=[],
                user_id=user_id,
                intent="adapt_difficulty",
                user_progress=None,
                user_analysis=None,
                learning_style=None,
                content_preferences=None,
                generated_questions=None,
                assistance_response=None,
                adapted_difficulty=None,
                adaptation_message=None,
                topic=None,
                lesson_id=None,
                user_question=None,
                current_difficulty=None,
                error=None
            )
            
            result = self.graph.invoke(state)
            
            return {
                "difficulty": result.get("adapted_difficulty", "intermediate"),
                "message": result.get("adaptation_message", ""),
                "recommendations": self._get_learning_recommendations(result)
            }
            
        except Exception as e:
            logger.error(f"Ошибка адаптации пути обучения: {e}")
            return {"difficulty": "intermediate", "message": "", "recommendations": []}
    
    def _get_learning_recommendations(self, agent_result: Dict[str, Any]) -> List[str]:
        """Получение рекомендаций по обучению"""
        recommendations = []
        user_analysis = agent_result.get("user_analysis", {})
        
        avg_score = user_analysis.get("average_score", 70)
        weak_areas = user_analysis.get("weak_areas", [])
        learning_speed = user_analysis.get("learning_speed", "normal")
        
        if avg_score < 70:
            recommendations.append("Рекомендуем повторить пройденный материал")
            recommendations.append("Обратитесь за помощью к AI-помощнику при затруднениях")
        
        if weak_areas:
            topic_names = {
                "основы_рисков": "основы рисков",
                "критичность_процессов": "критичность процессов", 
                "оценка_рисков": "оценка рисков"
            }
            for area in weak_areas:
                topic_name = topic_names.get(area, area)
                recommendations.append(f"Уделите больше внимания теме: {topic_name}")
        
        if learning_speed == "slow":
            recommendations.append("Не торопитесь, изучайте материал в удобном темпе")
            recommendations.append("Делайте паузы между уроками для лучшего усвоения")
        elif learning_speed == "fast":
            recommendations.append("Вы быстро усваиваете материал - отлично!")
            recommendations.append("Попробуйте более сложные задания")
        
        return recommendations
    
    def get_personalized_encouragement(self, user_id: str, score: float, 
                                     is_improvement: bool = False) -> str:
        """Получение персонализированного поощрения"""
        try:
            # Получаем анализ пользователя для персонализации
            progress_summary = db_service.get_user_progress_summary(user_id)
            user_analysis = self._perform_user_analysis(progress_summary)
            
            avg_score = user_analysis.get("average_score", 70)
            learning_speed = user_analysis.get("learning_speed", "normal")
            
            if score >= 90:
                if learning_speed == "fast":
                    return "🌟 Превосходно! Вы демонстрируете отличное понимание материала!"
                else:
                    return "🎉 Отличный результат! Вы хорошо усвоили материал!"
            elif score >= 80:
                if is_improvement:
                    return "📈 Заметен прогресс! Продолжайте в том же духе!"
                else:
                    return "✅ Хороший результат! Вы на правильном пути!"
            elif score >= 60:
                return "💪 Неплохо! Еще немного усилий и результат будет отличным!"
            else:
                if avg_score > score + 10:
                    return "🤔 Возможно, стоит повторить материал. Вы можете лучше!"
                else:
                    return "📚 Не расстраивайтесь! Изучение требует времени. Попробуйте еще раз!"
            
        except Exception as e:
            logger.error(f"Ошибка генерации поощрения: {e}")
            return "Продолжайте обучение!"


# Глобальный экземпляр агента
learning_agent = LearningAIAgent().llm.invoke(prompt)
            
            return {
                "assistance_response": response.content,
                "messages": [AIMessage(content="Подготовил объяснение для вас...")]
            }
            
        except Exception as e:
            logger.error(f"Ошибка предоставления помощи: {e}")
            return {
                "assistance_response": "К сожалению, не могу найти ответ на ваш вопрос. Попробуйте переформулировать.",
                "error": str(e)
            }
    
    def _adapt_difficulty_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел адаптации сложности"""
        user_analysis = state.get("user_analysis", {})
        current_difficulty = state.get("current_difficulty", "intermediate")
        
        # Анализируем необходимость изменения сложности
        avg_score = user_analysis.get("average_score", 70)
        recent_attempts = user_analysis.get("recent_attempts", 0)
        
        new_difficulty = current_difficulty
        adaptation_message = ""
        
        if recent_attempts >= 3:
            if avg_score >= 90:
                new_difficulty = "advanced"
                adaptation_message = "Повышаю сложность - вы отлично справляетесь!"
            elif avg_score <= 60:
                new_difficulty = "beginner"
                adaptation_message = "Снижаю сложность для лучшего усвоения материала"
            else:
                new_difficulty = "intermediate"
                adaptation_message = "Оставляю средний уровень сложности"
        
        return {
            "adapted_difficulty": new_difficulty,
            "adaptation_message": adaptation_message,
            "messages": [AIMessage(content=adaptation_message)] if adaptation_message else []
        }
    
    def _route_after_personalization(self, state: Dict[str, Any]) -> str:
        """Определяет следующий узел после персонализации"""
        intent = state.get("intent", "generate_questions")
        
        if intent == "help" or intent == "assistance":
            return "provide_assistance"
        elif intent == "adapt_difficulty":
            return "adapt_difficulty"
        else:
            return "generate_questions"
    
    def _perform_user_analysis(self, progress_summary) -> Dict[str, Any]:
        """Анализ успеваемости и характеристик пользователя"""
        topics_progress = progress_summary.topics_progress
        
        # Вычисляем общую статистику
        total_completed = sum(
            topic.get("completed_lessons", 0) 
            for topic in topics_progress.values()
        )
        
        total_attempts = sum(
            topic.get("total_attempts", 0) 
            for topic in topics_progress.values()
        )
        
        # Средняя оценка
        all_scores = []
        for topic_data in topics_progress.values():
            for lesson_data in topic_data.get("lessons", {}).values():
                if lesson_data.get("is_completed"):
                    all_scores.append(lesson_data.get("best_score", 0))
        
        average_score = sum(all_scores) / len(all_scores) if all_scores else 0
        
        # Определяем слабые места
        weak_areas = []
        for topic_id, topic_data in topics_progress.items():
            topic_scores = [
                lesson.get("best_score", 0) 
                for lesson in topic_data.get("lessons", {}).values()
                if lesson.get("is_completed")
            ]
            if topic_scores and sum(topic_scores) / len(topic_scores) < 70:
                weak_areas.append(topic_id)
        
        # Анализ скорости обучения
        learning_speed = "normal"
        if total_attempts > 0:
            success_rate = total_completed / total_attempts
            if success_rate > 0.8:
                learning_speed = "fast"
            elif success_rate < 0.5:
                learning_speed = "slow"
        
        return {
            "total_completed": total_completed,
            "total_attempts": total_attempts,
            "average_score": average_score,
            "weak_areas": weak_areas,
            "learning_speed": learning_speed,
            "recent_attempts": min(total_attempts, 5)  # Последние 5 попыток
        }
    
    def _determine_learning_style(self, user_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Определение стиля обучения пользователя"""
        learning_speed = user_analysis.get("learning_speed", "normal")
        average_score = user_analysis.get("average_score", 70)
        
        style = {
            "pace": learning_speed,
            "support_level": "high" if average_score < 70 else "medium",
            "explanation_detail": "detailed" if average_score < 80 else "concise",
            "encouragement_frequency": "high" if average_score < 70 else "medium"
        }
        
        return style
    
    def _get_content_preferences(self, user_progress: Dict[str, Any]) -> Dict[str, Any]:
        """Определение предпочтений по контенту"""
        current_topic = user_progress.get("current_topic")
        current_lesson = user_progress.get("current_lesson", 1)
        
        # Получаем информацию о текущем уроке
        lesson_info = None
        if current_topic and current_topic in LEARNING_STRUCTURE:
            topic_data = LEARNING_STRUCTURE[current_topic]
            for lesson in topic_data["lessons"]:
                if lesson["id"] == current_lesson:
                    lesson_info = lesson
                    break
        
        return {
            "current_topic": current_topic,
            "current_lesson": current_lesson,
            "lesson_info": lesson_info,
            "focus_keywords": lesson_info.get("keywords", []) if lesson_info else []
        }
    
    # Основные методы для взаимодействия с ботом
    
    def generate_adaptive_questions(self, user_id: str, topic: str, lesson_id: int) -> List[Dict[str, Any]]:
        """Генерация адаптивных вопросов для пользователя"""
        try:
            state = {
                "user_id": user_id,
                "topic": topic,
                "lesson_id": lesson_id,
                "intent": "generate_questions"
            }
            
            result = self.graph.invoke(state)
            return result.get("generated_questions", [])
            
        except Exception as e:
            logger.error(f"Ошибка генерации адаптивных вопросов: {e}")
            return []
    
    def provide_learning_assistance(self, user_id: str, question: str, 
                                  topic: str = None, lesson_id: int = None) -> str:
        """Предоставление помощи и объяснений"""
        try:
            state = {
                "user_id": user_id,
                "user_question": question,
                "topic": topic,
                "lesson_id": lesson_id,
                "intent": "assistance"
            }
            
            result = self.graph.invoke(state)
            return result.get("assistance_response", "Извините, не могу помочь с этим вопросом.")
            
        except Exception as e:
            logger.error(f"Ошибка предоставления помощи: {e}")
            return "Произошла ошибка при обработке вашего вопроса."
    
    def adapt_learning_path(self, user_id: str) -> Dict[str, Any]:
        """Адаптация пути обучения на основе прогресса"""
        try:
            state = {
                "user_id": user_id,
                "intent": "adapt_difficulty"
            }
            
            result = self.graph.invoke(state)
            
            return {
                "difficulty": result.get("adapted_difficulty", "intermediate"),
                "message": result.get("adaptation_message", ""),
                "recommendations": self._get_learning_recommendations(result)
            }
            
        except Exception as e:
            logger.error(f"Ошибка адаптации пути обучения: {e}")
            return {"difficulty": "intermediate", "message": "", "recommendations": []}
    
    def _get_learning_recommendations(self, agent_result: Dict[str, Any]) -> List[str]:
        """Получение рекомендаций по обучению"""
        recommendations = []
        user_analysis = agent_result.get("user_analysis", {})
        
        avg_score = user_analysis.get("average_score", 70)
        weak_areas = user_analysis.get("weak_areas", [])
        learning_speed = user_analysis.get("learning_speed", "normal")
        
        if avg_score < 70:
            recommendations.append("Рекомендуем повторить пройденный материал")
            recommendations.append("Обратитесь за помощью к AI-помощнику при затруднениях")
        
        if weak_areas:
            topic_names = {
                "основы_рисков": "основы рисков",
                "критичность_процессов": "критичность процессов", 
                "оценка_рисков": "оценка рисков"
            }
            for area in weak_areas:
                topic_name = topic_names.get(area, area)
                recommendations.append(f"Уделите больше внимания теме: {topic_name}")
        
        if learning_speed == "slow":
            recommendations.append("Не торопитесь, изучайте материал в удобном темпе")
            recommendations.append("Делайте паузы между уроками для лучшего усвоения")
        elif learning_speed == "fast":
            recommendations.append("Вы быстро усваиваете материал - отлично!")
            recommendations.append("Попробуйте более сложные задания")
        
        return recommendations
    
    def get_personalized_encouragement(self, user_id: str, score: float, 
                                     is_improvement: bool = False) -> str:
        """Получение персонализированного поощрения"""
        try:
            # Получаем анализ пользователя для персонализации
            progress_summary = db_service.get_user_progress_summary(user_id)
            user_analysis = self._perform_user_analysis(progress_summary)
            
            avg_score = user_analysis.get("average_score", 70)
            learning_speed = user_analysis.get("learning_speed", "normal")
            
            if score >= 90:
                if learning_speed == "fast":
                    return "🌟 Превосходно! Вы демонстрируете отличное понимание материала!"
                else:
                    return "🎉 Отличный результат! Вы хорошо усвоили материал!"
            elif score >= 80:
                if is_improvement:
                    return "📈 Заметен прогресс! Продолжайте в том же духе!"
                else:
                    return "✅ Хороший результат! Вы на правильном пути!"
            elif score >= 60:
                return "💪 Неплохо! Еще немного усилий и результат будет отличным!"
            else:
                if avg_score > score + 10:
                    return "🤔 Возможно, стоит повторить материал. Вы можете лучше!"
                else:
                    return "📚 Не расстраивайтесь! Изучение требует времени. Попробуйте еще раз!"
            
        except Exception as e:
            logger.error(f"Ошибка генерации поощрения: {e}")
            return "Продолжайте обучение!"


# Глобальный экземпляр агента
learning_agent = LearningAIAgent()