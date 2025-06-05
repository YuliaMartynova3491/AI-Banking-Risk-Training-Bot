"""
Сервис для работы с квизами и тестированием знаний
"""

import json
import random
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class QuizQuestion:
    """Структура вопроса квиза"""
    question: str
    options: List[str]
    correct_answer: int
    explanation: str
    topic: str
    difficulty: str = "medium"

@dataclass
class QuizResult:
    """Результат прохождения квиза"""
    user_id: int
    topic: str
    score: int
    total_questions: int
    correct_answers: List[int]
    user_answers: List[int]
    completion_time: float

class QuizService:
    """Сервис для создания и проведения квизов"""
    
    def __init__(self):
        self.questions_db: Dict[str, List[QuizQuestion]] = {}
        self.user_results: Dict[int, List[QuizResult]] = {}
        self._load_default_questions()
    
    def _load_default_questions(self):
        """Загружает базовые вопросы"""
        # Вопросы по управлению рисками
        risk_questions = [
            QuizQuestion(
                question="Что такое операционный риск?",
                options=[
                    "Риск потерь от неадекватных внутренних процессов",
                    "Риск изменения валютных курсов", 
                    "Риск снижения процентных ставок",
                    "Риск политических изменений"
                ],
                correct_answer=0,
                explanation="Операционный риск - это риск потерь от неадекватных или неэффективных внутренних процессов, людей, систем или внешних событий.",
                topic="risk_management"
            ),
            QuizQuestion(
                question="Какой принцип лежит в основе управления рисками?",
                options=[
                    "Избежание всех рисков",
                    "Максимизация прибыли любой ценой",
                    "Баланс между риском и доходностью",
                    "Перенос всех рисков на страховые компании"
                ],
                correct_answer=2,
                explanation="Основной принцип управления рисками - это поиск оптимального баланса между уровнем риска и ожидаемой доходностью.",
                topic="risk_management"
            ),
            QuizQuestion(
                question="Что включает в себя процесс идентификации рисков?",
                options=[
                    "Только анализ финансовых показателей",
                    "Выявление и описание всех потенциальных рисков",
                    "Расчет страховых премий",
                    "Создание резервных фондов"
                ],
                correct_answer=1,
                explanation="Идентификация рисков включает систематическое выявление и описание всех потенциальных рисков, которые могут повлиять на достижение целей организации.",
                topic="risk_management"
            )
        ]
        
        # Вопросы по непрерывности бизнеса
        continuity_questions = [
            QuizQuestion(
                question="Что такое план непрерывности бизнеса (BCP)?",
                options=[
                    "План маркетинговых мероприятий",
                    "Документ, описывающий процедуры для поддержания критических функций во время сбоев",
                    "Финансовый план на год",
                    "План развития персонала"
                ],
                correct_answer=1,
                explanation="План непрерывности бизнеса (BCP) - это документ, который описывает процедуры и инструкции для поддержания критических бизнес-функций во время и после значительных сбоев.",
                topic="business_continuity"
            ),
            QuizQuestion(
                question="Что такое RTO (Recovery Time Objective)?",
                options=[
                    "Время на обучение персонала",
                    "Максимально допустимое время простоя системы",
                    "Время работы в офисе",
                    "Период отпуска сотрудников"
                ],
                correct_answer=1,
                explanation="RTO (Recovery Time Objective) - это максимально допустимое время, в течение которого система или процесс могут быть недоступны после инцидента.",
                topic="business_continuity"
            )
        ]
        
        self.questions_db["risk_management"] = risk_questions
        self.questions_db["business_continuity"] = continuity_questions
    
    def get_quiz_topics(self) -> List[str]:
        """Возвращает список доступных тем для квизов"""
        return list(self.questions_db.keys())
    
    def generate_quiz(self, topic: str, num_questions: int = 3) -> List[QuizQuestion]:
        """Генерирует квиз по указанной теме"""
        if topic not in self.questions_db:
            return []
        
        available_questions = self.questions_db[topic]
        
        if len(available_questions) <= num_questions:
            return available_questions.copy()
        
        return random.sample(available_questions, num_questions)
    
    def check_answer(self, question: QuizQuestion, user_answer: int) -> bool:
        """Проверяет правильность ответа"""
        return question.correct_answer == user_answer
    
    def calculate_score(self, questions: List[QuizQuestion], user_answers: List[int]) -> int:
        """Вычисляет итоговый балл"""
        if len(questions) != len(user_answers):
            return 0
        
        correct_count = sum(
            1 for q, answer in zip(questions, user_answers)
            if q.correct_answer == answer
        )
        
        return int((correct_count / len(questions)) * 100)
    
    def save_result(self, result: QuizResult):
        """Сохраняет результат квиза"""
        if result.user_id not in self.user_results:
            self.user_results[result.user_id] = []
        
        self.user_results[result.user_id].append(result)
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Возвращает статистику пользователя"""
        if user_id not in self.user_results:
            return {
                "total_quizzes": 0,
                "average_score": 0,
                "topics_covered": [],
                "best_score": 0
            }
        
        results = self.user_results[user_id]
        
        return {
            "total_quizzes": len(results),
            "average_score": sum(r.score for r in results) / len(results),
            "topics_covered": list(set(r.topic for r in results)),
            "best_score": max(r.score for r in results)
        }
    
    def add_custom_question(self, topic: str, question: QuizQuestion):
        """Добавляет пользовательский вопрос"""
        if topic not in self.questions_db:
            self.questions_db[topic] = []
        
        self.questions_db[topic].append(question)
    
    def get_learning_recommendations(self, user_id: int) -> List[str]:
        """Возвращает рекомендации для обучения на основе результатов"""
        if user_id not in self.user_results:
            return ["Пройдите первый квиз для получения рекомендаций"]
        
        results = self.user_results[user_id]
        recommendations = []
        
        # Анализ слабых тем
        topic_scores = {}
        for result in results:
            if result.topic not in topic_scores:
                topic_scores[result.topic] = []
            topic_scores[result.topic].append(result.score)
        
        for topic, scores in topic_scores.items():
            avg_score = sum(scores) / len(scores)
            if avg_score < 70:
                recommendations.append(f"Рекомендуется дополнительное изучение темы: {topic}")
        
        if not recommendations:
            recommendations.append("Отличные результаты! Продолжайте изучать новые темы")
        
        return recommendations

# Глобальный экземпляр сервиса
quiz_service = QuizService()