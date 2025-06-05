"""
Сервис для работы с прогрессом обучения
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

from core.database import db_service
from core.enums import TopicStatus, LessonStatus, ScoreRanges, TOPIC_ORDER
from config.bot_config import LEARNING_STRUCTURE

logger = logging.getLogger(__name__)


class ProgressService:
    """Сервис управления прогрессом обучения"""
    
    def __init__(self):
        self.db_service = db_service
    
    def get_user_learning_path(self, user_id: str) -> Dict[str, Any]:
        """Получить персональный путь обучения пользователя"""
        try:
            progress = self.db_service.get_user_progress_summary(user_id)
            
            learning_path = {
                "current_position": {
                    "topic": progress.current_topic,
                    "lesson": progress.current_lesson
                },
                "available_topics": self._get_available_topics(progress),
                "available_lessons": {},
                "recommendations": self._generate_learning_recommendations(progress)
            }
            
            # Определяем доступные уроки для каждой доступной темы
            for topic_id in learning_path["available_topics"]:
                learning_path["available_lessons"][topic_id] = self._get_available_lessons(
                    topic_id, progress
                )
            
            return learning_path
            
        except Exception as e:
            logger.error(f"Ошибка получения пути обучения для {user_id}: {e}")
            return self._get_default_learning_path()
    
    def calculate_topic_progress(self, user_id: str, topic_id: str) -> Dict[str, Any]:
        """Вычислить прогресс по теме"""
        try:
            if topic_id not in LEARNING_STRUCTURE:
                return {"error": "Topic not found"}
            
            progress = self.db_service.get_user_progress_summary(user_id)
            topic_data = LEARNING_STRUCTURE[topic_id]
            total_lessons = len(topic_data["lessons"])
            
            if topic_id not in progress.topics_progress:
                return {
                    "topic_id": topic_id,
                    "status": TopicStatus.AVAILABLE.value,
                    "completed_lessons": 0,
                    "total_lessons": total_lessons,
                    "completion_percentage": 0,
                    "average_score": 0,
                    "attempts": 0
                }
            
            topic_progress = progress.topics_progress[topic_id]
            completed_lessons = topic_progress.get("completed_lessons", 0)
            average_score = topic_progress.get("average_score", 0)
            total_attempts = topic_progress.get("total_attempts", 0)
            
            # Определяем статус темы
            if completed_lessons == 0:
                status = TopicStatus.AVAILABLE
            elif completed_lessons == total_lessons:
                status = TopicStatus.COMPLETED
            else:
                status = TopicStatus.IN_PROGRESS
            
            return {
                "topic_id": topic_id,
                "status": status.value,
                "completed_lessons": completed_lessons,
                "total_lessons": total_lessons,
                "completion_percentage": (completed_lessons / total_lessons) * 100,
                "average_score": average_score,
                "attempts": total_attempts,
                "performance_level": self._get_performance_level(average_score)
            }
            
        except Exception as e:
            logger.error(f"Ошибка расчета прогресса темы {topic_id} для {user_id}: {e}")
            return {"error": str(e)}
    
    def calculate_lesson_progress(self, user_id: str, topic_id: str, lesson_id: int) -> Dict[str, Any]:
        """Вычислить прогресс по уроку"""
        try:
            lesson_progress = self.db_service.get_lesson_progress(user_id, topic_id, lesson_id)
            
            if not lesson_progress:
                return {
                    "topic_id": topic_id,
                    "lesson_id": lesson_id,
                    "status": LessonStatus.AVAILABLE.value,
                    "attempts": 0,
                    "best_score": 0,
                    "last_score": 0,
                    "is_completed": False
                }
            
            # Определяем статус урока
            if lesson_progress.is_completed:
                status = LessonStatus.COMPLETED
            elif lesson_progress.attempts > 0:
                status = LessonStatus.IN_PROGRESS
            else:
                status = LessonStatus.AVAILABLE
            
            return {
                "topic_id": topic_id,
                "lesson_id": lesson_id,
                "status": status.value,
                "attempts": lesson_progress.attempts,
                "best_score": lesson_progress.best_score,
                "last_score": lesson_progress.last_attempt_score,
                "is_completed": lesson_progress.is_completed,
                "started_at": lesson_progress.started_at.isoformat() if lesson_progress.started_at else None,
                "completed_at": lesson_progress.completed_at.isoformat() if lesson_progress.completed_at else None,
                "performance_level": self._get_performance_level(lesson_progress.best_score)
            }
            
        except Exception as e:
            logger.error(f"Ошибка расчета прогресса урока {lesson_id} для {user_id}: {e}")
            return {"error": str(e)}
    
    def get_overall_statistics(self, user_id: str) -> Dict[str, Any]:
        """Получить общую статистику пользователя"""
        try:
            progress = self.db_service.get_user_progress_summary(user_id)
            
            # Общие метрики
            total_lessons_available = sum(
                len(topic_data["lessons"]) 
                for topic_data in LEARNING_STRUCTURE.values()
            )
            
            completion_rate = (progress.total_lessons_completed / total_lessons_available) * 100
            
            # Анализ по темам
            topics_stats = {}
            for topic_id in TOPIC_ORDER:
                topics_stats[topic_id] = self.calculate_topic_progress(user_id, topic_id)
            
            # Определяем слабые места
            weak_topics = [
                topic_id for topic_id, stats in topics_stats.items()
                if stats.get("average_score", 0) < ScoreRanges.GOOD_MIN and stats.get("attempts", 0) > 0
            ]
            
            # Определяем сильные стороны
            strong_topics = [
                topic_id for topic_id, stats in topics_stats.items()
                if stats.get("average_score", 0) >= ScoreRanges.EXCELLENT_MIN
            ]
            
            return {
                "user_id": user_id,
                "overall_completion": completion_rate,
                "total_lessons_completed": progress.total_lessons_completed,
                "total_lessons_available": total_lessons_available,
                "average_score": progress.total_score,
                "topics_statistics": topics_stats,
                "weak_topics": weak_topics,
                "strong_topics": strong_topics,
                "learning_streak": self._calculate_learning_streak(user_id),
                "estimated_completion_time": self._estimate_completion_time(progress)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики для {user_id}: {e}")
            return {"error": str(e)}
    
    def check_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """Проверить достижения пользователя"""
        try:
            progress = self.db_service.get_user_progress_summary(user_id)
            achievements = []
            
            # Достижения по количеству уроков
            if progress.total_lessons_completed >= 1:
                achievements.append({
                    "id": "first_lesson",
                    "title": "Первые шаги",
                    "description": "Завершен первый урок",
                    "icon": "🎯"
                })
            
            if progress.total_lessons_completed >= 5:
                achievements.append({
                    "id": "five_lessons",
                    "title": "Активный ученик",
                    "description": "Завершено 5 уроков",
                    "icon": "📚"
                })
            
            # Достижения по оценкам
            if progress.total_score >= ScoreRanges.EXCELLENT_MIN:
                achievements.append({
                    "id": "excellent_student",
                    "title": "Отличник",
                    "description": f"Средняя оценка {progress.total_score:.1f}%",
                    "icon": "⭐"
                })
            
            # Достижения по темам
            for topic_id in TOPIC_ORDER:
                topic_stats = self.calculate_topic_progress(user_id, topic_id)
                if topic_stats.get("status") == TopicStatus.COMPLETED.value:
                    topic_title = LEARNING_STRUCTURE[topic_id]["title"]
                    achievements.append({
                        "id": f"topic_{topic_id}",
                        "title": f"Мастер темы",
                        "description": f"Завершена тема: {topic_title}",
                        "icon": "🏆"
                    })
            
            return achievements
            
        except Exception as e:
            logger.error(f"Ошибка проверки достижений для {user_id}: {e}")
            return []
    
    def generate_progress_report(self, user_id: str) -> str:
        """Сгенерировать текстовый отчет о прогрессе"""
        try:
            stats = self.get_overall_statistics(user_id)
            
            if "error" in stats:
                return "Ошибка генерации отчета"
            
            report = f"📊 **Отчет о прогрессе обучения**\n\n"
            report += f"🎯 Общий прогресс: {stats['overall_completion']:.1f}%\n"
            report += f"✅ Завершено уроков: {stats['total_lessons_completed']}/{stats['total_lessons_available']}\n"
            report += f"⭐ Средняя оценка: {stats['average_score']:.1f}%\n\n"
            
            # Прогресс по темам
            report += "📚 **Прогресс по темам:**\n"
            for topic_id, topic_stats in stats['topics_statistics'].items():
                topic_title = LEARNING_STRUCTURE[topic_id]["title"]
                completion = topic_stats.get('completion_percentage', 0)
                avg_score = topic_stats.get('average_score', 0)
                
                status_emoji = "✅" if completion == 100 else "🔄" if completion > 0 else "⏳"
                report += f"{status_emoji} {topic_title}: {completion:.0f}% ({avg_score:.1f}%)\n"
            
            # Рекомендации
            if stats['weak_topics']:
                report += f"\n💡 **Области для улучшения:**\n"
                for topic_id in stats['weak_topics']:
                    topic_title = LEARNING_STRUCTURE[topic_id]["title"]
                    report += f"• {topic_title}\n"
            
            if stats['strong_topics']:
                report += f"\n🌟 **Сильные стороны:**\n"
                for topic_id in stats['strong_topics']:
                    topic_title = LEARNING_STRUCTURE[topic_id]["title"]
                    report += f"• {topic_title}\n"
            
            return report
            
        except Exception as e:
            logger.error(f"Ошибка генерации отчета для {user_id}: {e}")
            return "Ошибка генерации отчета"
    
    # Вспомогательные методы
    
    def _get_available_topics(self, progress) -> List[str]:
        """Определить доступные темы"""
        available = ["основы_рисков"]  # Первая тема всегда доступна
        
        for i, topic_id in enumerate(TOPIC_ORDER[1:], 1):
            prev_topic = TOPIC_ORDER[i-1]
            prev_stats = self.calculate_topic_progress(progress.user_id, prev_topic)
            
            if prev_stats.get("status") == TopicStatus.COMPLETED.value:
                available.append(topic_id)
            else:
                break
        
        return available
    
    def _get_available_lessons(self, topic_id: str, progress) -> List[int]:
        """Определить доступные уроки в теме"""
        if topic_id not in progress.topics_progress:
            return [1]  # Только первый урок доступен
        
        topic_progress = progress.topics_progress[topic_id]
        lessons_data = topic_progress.get("lessons", {})
        available = [1]  # Первый урок всегда доступен
        
        total_lessons = len(LEARNING_STRUCTURE[topic_id]["lessons"])
        
        for lesson_id in range(1, total_lessons + 1):
            lesson_key = str(lesson_id)
            if lesson_key in lessons_data and lessons_data[lesson_key].get("is_completed"):
                next_lesson = lesson_id + 1
                if next_lesson <= total_lessons and next_lesson not in available:
                    available.append(next_lesson)
        
        return available
    
    def _generate_learning_recommendations(self, progress) -> List[str]:
        """Генерировать рекомендации по обучению"""
        recommendations = []
        
        if progress.total_lessons_completed == 0:
            recommendations.append("Начните с основ - первая тема ждет вас!")
        elif progress.total_score < ScoreRanges.GOOD_MIN:
            recommendations.append("Рекомендуем повторить пройденный материал")
            recommendations.append("Используйте помощь AI-агента при затруднениях")
        elif progress.total_score >= ScoreRanges.EXCELLENT_MIN:
            recommendations.append("Отличные результаты! Продолжайте в том же духе")
        
        return recommendations
    
    def _get_performance_level(self, score: float) -> str:
        """Определить уровень успеваемости"""
        if score >= ScoreRanges.EXCELLENT_MIN:
            return "excellent"
        elif score >= ScoreRanges.GOOD_MIN:
            return "good"
        elif score >= ScoreRanges.SATISFACTORY_MIN:
            return "satisfactory"
        else:
            return "poor"
    
    def _calculate_learning_streak(self, user_id: str) -> int:
        """Вычислить серию активного обучения (дни подряд)"""
        # Упрощенная версия - можно расширить добавив отслеживание активности по дням
        try:
            lessons_progress = self.db_service.get_user_lessons_progress(user_id)
            if not lessons_progress:
                return 0
            
            # Подсчитываем количество дней с активностью
            active_days = set()
            for lesson in lessons_progress:
                if lesson.completed_at:
                    active_days.add(lesson.completed_at.date())
            
            return len(active_days)
            
        except Exception as e:
            logger.error(f"Ошибка расчета серии обучения для {user_id}: {e}")
            return 0
    
    def _estimate_completion_time(self, progress) -> Optional[str]:
        """Оценить время до завершения обучения"""
        try:
            if progress.total_lessons_completed == 0:
                return "Невозможно оценить"
            
            total_lessons = sum(len(topic_data["lessons"]) for topic_data in LEARNING_STRUCTURE.values())
            remaining_lessons = total_lessons - progress.total_lessons_completed
            
            if remaining_lessons == 0:
                return "Обучение завершено"
            
            # Упрощенная оценка: 1 урок = 15 минут
            estimated_minutes = remaining_lessons * 15
            
            if estimated_minutes < 60:
                return f"~{estimated_minutes} минут"
            else:
                hours = estimated_minutes // 60
                return f"~{hours} часов"
                
        except Exception as e:
            logger.error(f"Ошибка оценки времени завершения: {e}")
            return "Невозможно оценить"
    
    def _get_default_learning_path(self) -> Dict[str, Any]:
        """Получить путь обучения по умолчанию"""
        return {
            "current_position": {"topic": "основы_рисков", "lesson": 1},
            "available_topics": ["основы_рисков"],
            "available_lessons": {"основы_рисков": [1]},
            "recommendations": ["Начните с изучения основ рисков"]
        }


# Глобальный экземпляр сервиса
progress_service = ProgressService()