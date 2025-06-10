"""
Модели данных для AI-агента
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
from enum import Enum

Base = declarative_base()


class UserProgress(Base):
    """Модель прогресса пользователя"""
    __tablename__ = "user_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    
    # Общий прогресс
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    total_lessons_completed = Column(Integer, default=0)
    total_score = Column(Float, default=0.0)
    
    # Текущий урок
    current_topic = Column(String, nullable=True)
    current_lesson = Column(Integer, default=1)
    
    # Дополнительные данные
    preferences = Column(JSON, default=dict)  # Пользовательские настройки
    ai_context = Column(JSON, default=dict)   # Контекст для ИИ-агента


class LessonProgress(Base):
    """Модель прогресса по урокам"""
    __tablename__ = "lesson_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    topic_id = Column(String, nullable=False)
    lesson_id = Column(Integer, nullable=False)
    
    # Прогресс урока
    is_completed = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
    best_score = Column(Float, default=0.0)
    last_attempt_score = Column(Float, default=0.0)
    
    # Временные метки
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    last_attempt_at = Column(DateTime, default=datetime.utcnow)
    
    # Данные о последней попытке
    last_questions = Column(JSON, default=list)  # Вопросы последней попытки
    last_answers = Column(JSON, default=list)    # Ответы последней попытки


class QuizSession(Base):
    """Модель сессии тестирования"""
    __tablename__ = "quiz_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    topic_id = Column(String, nullable=False)
    lesson_id = Column(Integer, nullable=False)
    
    # Данные сессии
    questions = Column(JSON, nullable=False)  # Список вопросов
    answers = Column(JSON, default=list)     # Ответы пользователя
    current_question = Column(Integer, default=0)
    
    # Результаты
    is_completed = Column(Boolean, default=False)
    score = Column(Float, default=0.0)
    
    # Временные метки
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


# Pydantic модели для API и валидации

class UserData(BaseModel):
    """Данные пользователя"""
    user_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class LessonData(BaseModel):
    """Данные урока"""
    topic_id: str
    lesson_id: int
    title: str
    description: str
    keywords: List[str]


class QuestionData(BaseModel):
    """Данные вопроса"""
    id: str
    question: str
    options: List[str]
    correct_answer: int
    explanation: str
    difficulty: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QuizResult(BaseModel):
    """Результат тестирования"""
    user_id: str
    topic_id: str
    lesson_id: int
    questions_count: int
    correct_answers: int
    score: float
    passed: bool
    duration_seconds: Optional[int] = None


class UserProgressResponse(BaseModel):
    """Ответ с прогрессом пользователя"""
    user_id: str
    total_lessons_completed: int
    total_score: float
    current_topic: Optional[str]
    current_lesson: int
    topics_progress: Dict[str, Dict[str, Any]]


class AIAgentState(BaseModel):
    """Состояние AI-агента"""
    user_id: str
    current_topic: Optional[str] = None
    current_lesson: Optional[int] = None
    user_context: Dict[str, Any] = Field(default_factory=dict)
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    learning_preferences: Dict[str, Any] = Field(default_factory=dict)
    
    # Адаптивные параметры
    difficulty_level: str = "beginner"  # beginner, intermediate, advanced
    learning_speed: str = "normal"      # slow, normal, fast
    focus_areas: List[str] = Field(default_factory=list)  # Области для дополнительного внимания


class KnowledgeItem(BaseModel):
    """Элемент базы знаний"""
    prompt: str
    response: str
    metadata: Dict[str, Any]


class GeneratedQuestion(BaseModel):
    """Сгенерированный вопрос"""
    question: str
    options: List[str]
    correct_answer: int
    explanation: str
    source_context: str
    difficulty: str
    confidence_score: float = Field(ge=0.0, le=1.0)

class LessonHistory(Base):
    """Модель истории прохождения уроков"""
    __tablename__ = "lesson_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    topic_id = Column(String, nullable=False)
    lesson_id = Column(Integer, nullable=False)
    session_date = Column(DateTime, default=datetime.utcnow)
    
    # Сохраненный контент
    lesson_material_viewed = Column(Text, nullable=True)  # Материал урока
    questions_asked = Column(JSON, default=list)  # Вопросы квиза
    answers_given = Column(JSON, default=list)   # Ответы пользователя
    final_score = Column(Float, default=0.0)
    duration_minutes = Column(Integer, default=0)    