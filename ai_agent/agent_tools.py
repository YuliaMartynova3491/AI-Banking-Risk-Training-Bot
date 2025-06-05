"""
Инструменты для AI-агента
"""
import logging
from typing import Dict, Any, List, Optional
from langchain.tools import BaseTool
from pydantic import Field

from core.database import db_service
from services.rag_service import rag_service
from services.progress_service import progress_service
from services.question_service import question_service

logger = logging.getLogger(__name__)


class UserProgressTool(BaseTool):
    """Инструмент для получения прогресса пользователя"""
    
    name: str = "get_user_progress"
    description: str = "Получить подробную информацию о прогрессе обучения пользователя"
    
    def _run(self, user_id: str) -> Dict[str, Any]:
        """Выполнение инструмента"""
        try:
            progress = db_service.get_user_progress_summary(user_id)
            detailed_stats = progress_service.get_overall_statistics(user_id)
            
            return {
                "success": True,
                "progress_summary": progress.dict(),
                "detailed_statistics": detailed_stats
            }
        except Exception as e:
            logger.error(f"Ошибка получения прогресса пользователя {user_id}: {e}")
            return {"success": False, "error": str(e)}


class KnowledgeSearchTool(BaseTool):
    """Инструмент для поиска в базе знаний"""
    
    name: str = "search_knowledge"
    description: str = "Поиск релевантной информации в базе знаний банка"
    
    def _run(self, query: str, topic: str = None, lesson: int = None, 
             limit: int = 5) -> Dict[str, Any]:
        """Выполнение поиска"""
        try:
            results = rag_service.search_relevant_content(
                query=query,
                topic=topic,
                lesson=lesson,
                n_results=limit
            )
            
            return {
                "success": True,
                "results": results,
                "count": len(results)
            }
        except Exception as e:
            logger.error(f"Ошибка поиска в базе знаний: {e}")
            return {"success": False, "error": str(e)}


class QuestionGeneratorTool(BaseTool):
    """Инструмент для генерации вопросов"""
    
    name: str = "generate_questions"
    description: str = "Генерация адаптивных вопросов для тестирования"
    
    def _run(self, user_id: str, topic: str, lesson_id: int, 
             difficulty: str = "intermediate", count: int = 3) -> Dict[str, Any]:
        """Генерация вопросов"""
        try:
            # Получаем анализ пользователя
            user_progress = db_service.get_user_progress_summary(user_id)
            
            # Формируем данные о производительности
            user_performance = {}
            if topic in user_progress.topics_progress:
                topic_progress = user_progress.topics_progress[topic]
                user_performance = {
                    "average_score": topic_progress.get("average_score", 70),
                    "recent_attempts": topic_progress.get("total_attempts", 0),
                    "weak_areas": []
                }
            
            # Генерируем вопросы
            questions = rag_service.get_adaptive_questions(
                user_id=user_id,
                topic=topic,
                lesson_id=lesson_id,
                user_performance=user_performance
            )
            
            return {
                "success": True,
                "questions": [q.dict() for q in questions],
                "count": len(questions),
                "difficulty": difficulty
            }
        except Exception as e:
            logger.error(f"Ошибка генерации вопросов: {e}")
            return {"success": False, "error": str(e)}


class PerformanceAnalyzerTool(BaseTool):
    """Инструмент для анализа успеваемости"""
    
    name: str = "analyze_performance"
    description: str = "Анализ успеваемости и выявление областей для улучшения"
    
    def _run(self, user_id: str, topic_id: str = None) -> Dict[str, Any]:
        """Анализ успеваемости"""
        try:
            # Получаем статистику по вопросам
            question_stats = question_service.get_question_statistics(user_id, topic_id)
            
            # Получаем общую статистику
            overall_stats = progress_service.get_overall_statistics(user_id)
            
            # Анализируем слабые места
            weak_areas = overall_stats.get("weak_topics", [])
            strong_areas = overall_stats.get("strong_topics", [])
            
            # Генерируем рекомендации
            recommendations = question_service.suggest_review_topics(user_id)
            
            return {
                "success": True,
                "question_statistics": question_stats,
                "overall_statistics": overall_stats,
                "weak_areas": weak_areas,
                "strong_areas": strong_areas,
                "recommendations": recommendations
            }
        except Exception as e:
            logger.error(f"Ошибка анализа успеваемости: {e}")
            return {"success": False, "error": str(e)}


class LearningPathTool(BaseTool):
    """Инструмент для работы с путем обучения"""
    
    name: str = "get_learning_path"
    description: str = "Получение персонального пути обучения пользователя"
    
    def _run(self, user_id: str) -> Dict[str, Any]:
        """Получение пути обучения"""
        try:
            learning_path = progress_service.get_user_learning_path(user_id)
            
            return {
                "success": True,
                "learning_path": learning_path
            }
        except Exception as e:
            logger.error(f"Ошибка получения пути обучения: {e}")
            return {"success": False, "error": str(e)}


class RecommendationTool(BaseTool):
    """Инструмент для генерации персонализированных рекомендаций"""
    
    name: str = "generate_recommendations"
    description: str = "Генерация персонализированных рекомендаций по обучению"
    
    def _run(self, user_id: str, context: str = "general") -> Dict[str, Any]:
        """Генерация рекомендаций"""
        try:
            # Получаем данные пользователя
            progress = db_service.get_user_progress_summary(user_id)
            detailed_stats = progress_service.get_overall_statistics(user_id)
            
            recommendations = []
            
            # Рекомендации на основе прогресса
            if progress.total_lessons_completed == 0:
                recommendations.append({
                    "type": "start_learning",
                    "message": "Начните с изучения основ рисков нарушения непрерывности",
                    "action": "start_topic_основы_рисков"
                })
            
            # Рекомендации на основе слабых мест
            weak_topics = detailed_stats.get("weak_topics", [])
            for topic in weak_topics:
                recommendations.append({
                    "type": "review_topic",
                    "message": f"Рекомендуем повторить материал по теме: {topic}",
                    "action": f"review_topic_{topic}"
                })
            
            # Рекомендации на основе сильных сторон
            strong_topics = detailed_stats.get("strong_topics", [])
            if strong_topics:
                recommendations.append({
                    "type": "advance_learning",
                    "message": "Отличные результаты! Можете переходить к более сложным темам",
                    "action": "increase_difficulty"
                })
            
            # Рекомендации по активности
            completion_rate = detailed_stats.get("overall_completion", 0)
            if completion_rate > 0 and completion_rate < 50:
                recommendations.append({
                    "type": "continue_learning",
                    "message": "Продолжайте активное обучение для достижения лучших результатов",
                    "action": "continue_current_path"
                })
            
            return {
                "success": True,
                "recommendations": recommendations,
                "context": context
            }
        except Exception as e:
            logger.error(f"Ошибка генерации рекомендаций: {e}")
            return {"success": False, "error": str(e)}


class AchievementTool(BaseTool):
    """Инструмент для работы с достижениями"""
    
    name: str = "check_achievements"
    description: str = "Проверка достижений пользователя"
    
    def _run(self, user_id: str) -> Dict[str, Any]:
        """Проверка достижений"""
        try:
            achievements = progress_service.check_achievements(user_id)
            
            return {
                "success": True,
                "achievements": achievements,
                "count": len(achievements)
            }
        except Exception as e:
            logger.error(f"Ошибка проверки достижений: {e}")
            return {"success": False, "error": str(e)}


class ExplanationTool(BaseTool):
    """Инструмент для генерации объяснений"""
    
    name: str = "generate_explanation"
    description: str = "Генерация персонализированных объяснений концепций"
    
    def _run(self, concept: str, user_id: str, difficulty_level: str = "intermediate") -> Dict[str, Any]:
        """Генерация объяснения"""
        try:
            # Поиск информации о концепции
            relevant_content = rag_service.search_relevant_content(
                query=concept,
                n_results=3
            )
            
            if not relevant_content:
                return {
                    "success": False,
                    "error": "Информация о концепции не найдена"
                }
            
            # Получаем профиль пользователя для персонализации
            user_progress = db_service.get_user_progress_summary(user_id)
            
            # Формируем объяснение на основе найденной информации
            explanation_parts = []
            for item in relevant_content:
                document = item.get('document', '')
                if 'Ответ:' in document:
                    answer_part = document.split('Ответ:')[1].strip()
                    explanation_parts.append(answer_part)
            
            # Объединяем и форматируем объяснение
            if explanation_parts:
                explanation = explanation_parts[0][:500]  # Ограничиваем длину
                
                # Добавляем персонализацию
                if user_progress.total_lessons_completed < 3:
                    explanation += "\n\n💡 Совет для начинающих: изучите этот материал внимательно, он важен для понимания основ."
                
                return {
                    "success": True,
                    "explanation": explanation,
                    "sources_count": len(relevant_content)
                }
            else:
                return {
                    "success": False,
                    "error": "Не удалось сформировать объяснение"
                }
                
        except Exception as e:
            logger.error(f"Ошибка генерации объяснения: {e}")
            return {"success": False, "error": str(e)}


# Класс для управления всеми инструментами
class AgentToolKit:
    """Набор инструментов для AI-агента"""
    
    def __init__(self):
        self.tools = [
            UserProgressTool(),
            KnowledgeSearchTool(),
            QuestionGeneratorTool(),
            PerformanceAnalyzerTool(),
            LearningPathTool(),
            RecommendationTool(),
            AchievementTool(),
            ExplanationTool()
        ]
    
    def get_tool_by_name(self, name: str) -> Optional[BaseTool]:
        """Получить инструмент по имени"""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
    
    def get_all_tools(self) -> List[BaseTool]:
        """Получить все инструменты"""
        return self.tools
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Выполнить инструмент по имени"""
        tool = self.get_tool_by_name(tool_name)
        if tool:
            try:
                return tool._run(**kwargs)
            except Exception as e:
                logger.error(f"Ошибка выполнения инструмента {tool_name}: {e}")
                return {"success": False, "error": str(e)}
        else:
            return {"success": False, "error": f"Инструмент {tool_name} не найден"}


# Глобальный экземпляр набора инструментов
agent_toolkit = AgentToolKit()