"""
Сервис для работы с вопросами и тестированием
"""
import logging
import random
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from core.database import db_service
from core.models import GeneratedQuestion, QuestionData
from core.enums import QuestionType, LearningDifficulty
from services.rag_service import rag_service
from config.settings import settings

logger = logging.getLogger(__name__)


class QuestionService:
    """Сервис управления вопросами и тестированием"""
    
    def __init__(self):
        self.rag_service = rag_service
        self.db_service = db_service
    
    def prepare_quiz_questions(self, user_id: str, topic_id: str, lesson_id: int) -> List[Dict[str, Any]]:
        """Подготовить вопросы для тестирования"""
        try:
            # Получаем прогресс пользователя для адаптации
            user_progress = self.db_service.get_user_progress_summary(user_id)
            user_performance = self._analyze_user_performance(user_progress, topic_id)
            
            # Генерируем вопросы с помощью RAG
            generated_questions = self.rag_service.get_adaptive_questions(
                user_id=user_id,
                topic=topic_id,
                lesson_id=lesson_id,
                user_performance=user_performance
            )
            
            if not generated_questions:
                # Если генерация не удалась, используем базовые вопросы
                logger.warning(f"Генерация вопросов не удалась для {user_id}, используем базовые")
                generated_questions = self._get_fallback_questions(topic_id, lesson_id)
            
            # Преобразуем в формат для БД
            questions_data = []
            for question in generated_questions:
                questions_data.append({
                    "question": question.question,
                    "options": question.options,
                    "correct_answer": question.correct_answer,
                    "explanation": question.explanation,
                    "difficulty": question.difficulty,
                    "confidence_score": getattr(question, 'confidence_score', 0.8)
                })
            
            # Перемешиваем вопросы для разнообразия
            random.shuffle(questions_data)
            
            # Ограничиваем количество согласно настройкам
            max_questions = settings.questions_per_lesson
            questions_data = questions_data[:max_questions]
            
            logger.info(f"Подготовлено {len(questions_data)} вопросов для пользователя {user_id}")
            return questions_data
            
        except Exception as e:
            logger.error(f"Ошибка подготовки вопросов: {e}")
            return self._get_emergency_questions()
    
    def validate_answer(self, question_data: Dict[str, Any], user_answer: int) -> Dict[str, Any]:
        """Валидация ответа пользователя"""
        try:
            correct_answer = question_data.get("correct_answer", 0)
            is_correct = user_answer == correct_answer
            
            result = {
                "is_correct": is_correct,
                "correct_answer_index": correct_answer,
                "correct_answer_text": question_data.get("options", [])[correct_answer] if correct_answer < len(question_data.get("options", [])) else "",
                "user_answer_text": question_data.get("options", [])[user_answer] if user_answer < len(question_data.get("options", [])) else "",
                "explanation": question_data.get("explanation", ""),
                "question_difficulty": question_data.get("difficulty", "intermediate")
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка валидации ответа: {e}")
            return {
                "is_correct": False,
                "error": "Ошибка обработки ответа"
            }
    
    def calculate_quiz_score(self, answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Рассчитать итоговую оценку за тест"""
        try:
            if not answers:
                return {"score": 0, "details": "Нет ответов"}
            
            total_questions = len(answers)
            correct_answers = sum(1 for answer in answers if answer.get("is_correct", False))
            score_percentage = (correct_answers / total_questions) * 100
            
            # Анализ сложности вопросов
            difficulty_breakdown = {
                "beginner": {"total": 0, "correct": 0},
                "intermediate": {"total": 0, "correct": 0},
                "advanced": {"total": 0, "correct": 0}
            }
            
            for answer in answers:
                difficulty = answer.get("question_difficulty", "intermediate")
                if difficulty in difficulty_breakdown:
                    difficulty_breakdown[difficulty]["total"] += 1
                    if answer.get("is_correct", False):
                        difficulty_breakdown[difficulty]["correct"] += 1
            
            # Определяем рекомендации
            recommendations = self._generate_score_recommendations(
                score_percentage, difficulty_breakdown
            )
            
            return {
                "score": score_percentage,
                "correct_answers": correct_answers,
                "total_questions": total_questions,
                "passed": score_percentage >= settings.min_score_to_pass,
                "difficulty_breakdown": difficulty_breakdown,
                "recommendations": recommendations,
                "performance_level": self._get_performance_level(score_percentage)
            }
            
        except Exception as e:
            logger.error(f"Ошибка расчета оценки: {e}")
            return {"score": 0, "error": str(e)}
    
    def get_question_statistics(self, user_id: str, topic_id: str = None) -> Dict[str, Any]:
        """Получить статистику по вопросам пользователя"""
        try:
            # Получаем все сессии пользователя
            user_progress = self.db_service.get_user_progress_summary(user_id)
            
            stats = {
                "total_questions_answered": 0,
                "correct_answers": 0,
                "accuracy_rate": 0,
                "difficulty_performance": {
                    "beginner": {"answered": 0, "correct": 0, "accuracy": 0},
                    "intermediate": {"answered": 0, "correct": 0, "accuracy": 0},
                    "advanced": {"answered": 0, "correct": 0, "accuracy": 0}
                },
                "topic_performance": {},
                "improvement_trend": []
            }
            
            # Анализируем прогресс по урокам
            lessons_progress = self.db_service.get_user_lessons_progress(user_id)
            
            total_answered = 0
            total_correct = 0
            
            for lesson in lessons_progress:
                if lesson.last_questions and lesson.last_answers:
                    lesson_questions = len(lesson.last_questions)
                    lesson_correct = sum(1 for answer in lesson.last_answers if answer.get("is_correct", False))
                    
                    total_answered += lesson_questions
                    total_correct += lesson_correct
                    
                    # Статистика по темам
                    if lesson.topic_id not in stats["topic_performance"]:
                        stats["topic_performance"][lesson.topic_id] = {
                            "answered": 0, "correct": 0, "accuracy": 0
                        }
                    
                    stats["topic_performance"][lesson.topic_id]["answered"] += lesson_questions
                    stats["topic_performance"][lesson.topic_id]["correct"] += lesson_correct
            
            # Рассчитываем общую точность
            stats["total_questions_answered"] = total_answered
            stats["correct_answers"] = total_correct
            stats["accuracy_rate"] = (total_correct / total_answered * 100) if total_answered > 0 else 0
            
            # Рассчитываем точность по темам
            for topic_stats in stats["topic_performance"].values():
                if topic_stats["answered"] > 0:
                    topic_stats["accuracy"] = (topic_stats["correct"] / topic_stats["answered"]) * 100
            
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики вопросов: {e}")
            return {"error": str(e)}
    
    def get_personalized_feedback(self, user_id: str, quiz_result: Dict[str, Any]) -> str:
        """Получить персонализированную обратную связь"""
        try:
            score = quiz_result.get("score", 0)
            difficulty_breakdown = quiz_result.get("difficulty_breakdown", {})
            
            feedback = []
            
            # Общая оценка
            if score >= 90:
                feedback.append("🌟 Превосходный результат! Вы отлично разбираетесь в материале.")
            elif score >= 80:
                feedback.append("✅ Хороший результат! Вы усвоили основные концепции.")
            elif score >= 60:
                feedback.append("📚 Неплохо, но есть над чем поработать.")
            else:
                feedback.append("🔄 Рекомендуем повторить материал и попробовать снова.")
            
            # Анализ по сложности
            weak_areas = []
            strong_areas = []
            
            for difficulty, stats in difficulty_breakdown.items():
                if stats["total"] > 0:
                    accuracy = (stats["correct"] / stats["total"]) * 100
                    if accuracy < 60:
                        weak_areas.append(difficulty)
                    elif accuracy >= 90:
                        strong_areas.append(difficulty)
            
            if weak_areas:
                difficulty_names = {
                    "beginner": "базовые вопросы",
                    "intermediate": "вопросы среднего уровня",
                    "advanced": "сложные вопросы"
                }
                weak_names = [difficulty_names.get(area, area) for area in weak_areas]
                feedback.append(f"💡 Стоит уделить внимание: {', '.join(weak_names)}")
            
            if strong_areas:
                feedback.append("🎯 Сильные стороны отмечены!")
            
            # Рекомендации
            recommendations = quiz_result.get("recommendations", [])
            if recommendations:
                feedback.extend(recommendations)
            
            return "\n".join(feedback)
            
        except Exception as e:
            logger.error(f"Ошибка генерации обратной связи: {e}")
            return "Продолжайте обучение!"
    
    def suggest_review_topics(self, user_id: str) -> List[str]:
        """Предложить темы для повторения"""
        try:
            user_progress = self.db_service.get_user_progress_summary(user_id)
            suggestions = []
            
            # Анализируем слабые места
            for topic_id, topic_progress in user_progress.topics_progress.items():
                avg_score = topic_progress.get("average_score", 0)
                if avg_score > 0 and avg_score < 75:  # Есть попытки, но низкая оценка
                    suggestions.append(topic_id)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Ошибка предложения тем для повторения: {e}")
            return []
    
    # Вспомогательные методы
    
    def _analyze_user_performance(self, user_progress, topic_id: str) -> Dict[str, Any]:
        """Анализ успеваемости пользователя"""
        performance = {
            "average_score": 70,
            "recent_attempts": 0,
            "weak_areas": [],
            "preferred_difficulty": "intermediate"
        }
        
        if topic_id in user_progress.topics_progress:
            topic_progress = user_progress.topics_progress[topic_id]
            performance["average_score"] = topic_progress.get("average_score", 70)
            performance["recent_attempts"] = min(topic_progress.get("total_attempts", 0), 5)
            
            # Определяем предпочтительную сложность
            if performance["average_score"] >= 90:
                performance["preferred_difficulty"] = "advanced"
            elif performance["average_score"] < 60:
                performance["preferred_difficulty"] = "beginner"
        
        return performance
    
    def _get_fallback_questions(self, topic_id: str, lesson_id: int) -> List[GeneratedQuestion]:
        """Базовые вопросы если генерация не удалась"""
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
                ]
            }
        }
        
        questions = fallback_questions.get(topic_id, {}).get(lesson_id, [])
        return questions
    
    def _get_emergency_questions(self) -> List[Dict[str, Any]]:
        """Экстренные вопросы на случай полного сбоя"""
        return [
            {
                "question": "Что такое риск нарушения непрерывности деятельности?",
                "options": [
                    "Риск, связанный с нарушением операционной устойчивости",
                    "Риск потери прибыли",
                    "Риск увольнения сотрудников",
                    "Риск изменения законодательства"
                ],
                "correct_answer": 0,
                "explanation": "Риск нарушения непрерывности связан с угрозами операционной устойчивости банка.",
                "difficulty": "beginner",
                "confidence_score": 1.0
            }
        ]
    
    def _generate_score_recommendations(self, score: float, difficulty_breakdown: Dict[str, Any]) -> List[str]:
        """Генерация рекомендаций на основе оценки"""
        recommendations = []
        
        if score < 60:
            recommendations.append("Рекомендуем повторить теоретический материал")
            recommendations.append("Обратитесь за помощью к AI-помощнику")
        elif score < 80:
            recommendations.append("Хороший результат! Закрепите знания дополнительной практикой")
        else:
            recommendations.append("Отличный результат! Можете переходить к следующему уроку")
        
        # Рекомендации по сложности
        for difficulty, stats in difficulty_breakdown.items():
            if stats["total"] > 0:
                accuracy = (stats["correct"] / stats["total"]) * 100
                if accuracy < 50:
                    if difficulty == "beginner":
                        recommendations.append("Изучите основные определения и концепции")
                    elif difficulty == "intermediate":
                        recommendations.append("Поработайте над пониманием практических аспектов")
                    elif difficulty == "advanced":
                        recommendations.append("Углубите знания в сложных темах")
        
        return recommendations
    
    def _get_performance_level(self, score: float) -> str:
        """Определить уровень успеваемости"""
        if score >= 90:
            return "excellent"
        elif score >= 80:
            return "good"
        elif score >= 60:
            return "satisfactory"
        else:
            return "poor"


# Глобальный экземпляр сервиса
question_service = QuestionService()