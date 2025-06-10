"""
Сервис для работы с базой данных
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, and_, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from config.settings import settings
from core.models import Base, UserProgress, LessonProgress, QuizSession
from core.models import UserData, QuizResult, UserProgressResponse

logger = logging.getLogger(__name__)

# Создание движка базы данных
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# Создание сессии
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создание таблиц
Base.metadata.create_all(bind=engine)


class DatabaseService:
    """Сервис для работы с базой данных"""
    
    def __init__(self):
        self.session_factory = SessionLocal
    
    def get_session(self) -> Session:
        """Получить сессию БД"""
        return self.session_factory()
    
    def close(self):
        """Закрыть соединения с БД"""
        try:
            engine.dispose()
            logger.info("Соединения с БД закрыты")
        except Exception as e:
            logger.error(f"Ошибка закрытия соединений с БД: {e}")
    
    def get_users_count(self) -> int:
        """Получить количество пользователей"""
        try:
            with self.get_session() as session:
                return session.query(UserProgress).count()
        except Exception as e:
            logger.error(f"Ошибка получения количества пользователей: {e}")
            return 0
    
    def health_check(self) -> bool:
        """Проверка состояния БД"""
        try:
            with self.get_session() as session:
                # Используем text() для явного объявления SQL
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Ошибка проверки состояния БД: {e}")
            return False
    
    # Методы для работы с пользователями
    
    def get_or_create_user(self, user_data: UserData) -> UserProgress:
        """Получить или создать пользователя"""
        with self.get_session() as session:
            user = session.query(UserProgress).filter(
                UserProgress.user_id == user_data.user_id
            ).first()
            
            if not user:
                user = UserProgress(
                    user_id=user_data.user_id,
                    username=user_data.username,
                    first_name=user_data.first_name,
                    last_name=user_data.last_name,
                    current_topic="основы_рисков",  # Первая тема
                    current_lesson=1
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                logger.info(f"Создан новый пользователь: {user_data.user_id}")
            else:
                # Обновляем данные пользователя
                user.username = user_data.username
                user.first_name = user_data.first_name
                user.last_name = user_data.last_name
                user.last_activity = datetime.utcnow()
                session.commit()
            
            return user
    
    def update_user_progress(self, user_id: str, **kwargs) -> bool:
        """Обновить прогресс пользователя"""
        try:
            with self.get_session() as session:
                user = session.query(UserProgress).filter(
                    UserProgress.user_id == user_id
                ).first()
                
                if user:
                    for key, value in kwargs.items():
                        if hasattr(user, key):
                            setattr(user, key, value)
                    
                    user.last_activity = datetime.utcnow()
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Ошибка обновления прогресса пользователя {user_id}: {e}")
            return False
    
    # Методы для работы с прогрессом уроков
    
    def get_lesson_progress(self, user_id: str, topic_id: str, lesson_id: int) -> Optional[LessonProgress]:
        """Получить прогресс по уроку"""
        with self.get_session() as session:
            return session.query(LessonProgress).filter(
                and_(
                    LessonProgress.user_id == user_id,
                    LessonProgress.topic_id == topic_id,
                    LessonProgress.lesson_id == lesson_id
                )
            ).first()
    
    def get_or_create_lesson_progress(self, user_id: str, topic_id: str, lesson_id: int) -> LessonProgress:
        """Получить или создать прогресс по уроку"""
        with self.get_session() as session:
            progress = session.query(LessonProgress).filter(
                and_(
                    LessonProgress.user_id == user_id,
                    LessonProgress.topic_id == topic_id,
                    LessonProgress.lesson_id == lesson_id
                )
            ).first()
            
            if not progress:
                progress = LessonProgress(
                    user_id=user_id,
                    topic_id=topic_id,
                    lesson_id=lesson_id,
                    started_at=datetime.utcnow()
                )
                session.add(progress)
                session.commit()
                session.refresh(progress)
            
            return progress
    
    def update_lesson_progress(self, user_id: str, topic_id: str, lesson_id: int, 
                             score: float, is_completed: bool = False) -> bool:
        """Обновить прогресс урока"""
        try:
            with self.get_session() as session:
                progress = session.query(LessonProgress).filter(
                    and_(
                        LessonProgress.user_id == user_id,
                        LessonProgress.topic_id == topic_id,
                        LessonProgress.lesson_id == lesson_id
                    )
                ).first()
                
                if progress:
                    progress.attempts += 1
                    progress.last_attempt_score = score
                    progress.last_attempt_at = datetime.utcnow()
                    
                    if score > progress.best_score:
                        progress.best_score = score
                    
                    if is_completed and not progress.is_completed:
                        progress.is_completed = True
                        progress.completed_at = datetime.utcnow()
                    
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Ошибка обновления прогресса урока: {e}")
            return False
    
    def get_user_lessons_progress(self, user_id: str) -> List[LessonProgress]:
        """Получить весь прогресс пользователя по урокам"""
        with self.get_session() as session:
            return session.query(LessonProgress).filter(
                LessonProgress.user_id == user_id
            ).all()
    
    # Методы для работы с тестированием
    
    def create_quiz_session(self, user_id: str, topic_id: str, lesson_id: int, 
                           questions: List[Dict[str, Any]]) -> QuizSession:
        """Создать сессию тестирования"""
        with self.get_session() as session:
            # Удаляем предыдущую незавершенную сессию
            session.query(QuizSession).filter(
                and_(
                    QuizSession.user_id == user_id,
                    QuizSession.topic_id == topic_id,
                    QuizSession.lesson_id == lesson_id,
                    QuizSession.is_completed == False
                )
            ).delete()
            
            quiz_session = QuizSession(
                user_id=user_id,
                topic_id=topic_id,
                lesson_id=lesson_id,
                questions=questions
            )
            session.add(quiz_session)
            session.commit()
            session.refresh(quiz_session)
            return quiz_session
    
    def get_active_quiz_session(self, user_id: str) -> Optional[QuizSession]:
        """Получить активную сессию тестирования"""
        with self.get_session() as session:
            return session.query(QuizSession).filter(
                and_(
                    QuizSession.user_id == user_id,
                    QuizSession.is_completed == False
                )
            ).first()
    
    def update_quiz_session(self, session_id: int, **kwargs) -> bool:
        """Обновить сессию тестирования"""
        try:
            with self.get_session() as session:
                quiz_session = session.query(QuizSession).filter(
                    QuizSession.id == session_id
                ).first()
                
                if quiz_session:
                    for key, value in kwargs.items():
                        if hasattr(quiz_session, key):
                            setattr(quiz_session, key, value)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Ошибка обновления сессии тестирования: {e}")
            return False
    
    def complete_quiz_session(self, session_id: int, final_score: float) -> bool:
        """Завершить сессию тестирования"""
        try:
            with self.get_session() as session:
                quiz_session = session.query(QuizSession).filter(
                    QuizSession.id == session_id
                ).first()
                
                if quiz_session:
                    quiz_session.is_completed = True
                    quiz_session.score = final_score
                    quiz_session.completed_at = datetime.utcnow()
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Ошибка завершения сессии тестирования: {e}")
            return False
    
    # Методы для аналитики и отчетности
    
    def get_user_progress_summary(self, user_id: str) -> UserProgressResponse:
        """Получить сводку прогресса пользователя"""
        with self.get_session() as session:
            user = session.query(UserProgress).filter(
                UserProgress.user_id == user_id
            ).first()
            
            if not user:
                return UserProgressResponse(
                    user_id=user_id,
                    total_lessons_completed=0,
                    total_score=0.0,
                    current_topic=None,
                    current_lesson=1,
                    topics_progress={}
                )
            
            # Получаем прогресс по урокам
            lessons_progress = session.query(LessonProgress).filter(
                LessonProgress.user_id == user_id
            ).all()
            
            # Группируем по темам
            topics_progress = {}
            for progress in lessons_progress:
                topic_id = progress.topic_id
                if topic_id not in topics_progress:
                    topics_progress[topic_id] = {
                        "completed_lessons": 0,
                        "total_attempts": 0,
                        "average_score": 0.0,
                        "lessons": {}
                    }
                
                topics_progress[topic_id]["lessons"][progress.lesson_id] = {
                    "is_completed": progress.is_completed,
                    "best_score": progress.best_score,
                    "attempts": progress.attempts,
                    "last_attempt_at": progress.last_attempt_at.isoformat() if progress.last_attempt_at else None
                }
                
                if progress.is_completed:
                    topics_progress[topic_id]["completed_lessons"] += 1
                
                topics_progress[topic_id]["total_attempts"] += progress.attempts
            
            # Рассчитываем средние оценки
            for topic_data in topics_progress.values():
                completed_lessons = [
                    lesson for lesson in topic_data["lessons"].values() 
                    if lesson["is_completed"]
                ]
                if completed_lessons:
                    topic_data["average_score"] = sum(
                        lesson["best_score"] for lesson in completed_lessons
                    ) / len(completed_lessons)
            
            return UserProgressResponse(
                user_id=user_id,
                total_lessons_completed=user.total_lessons_completed,
                total_score=user.total_score,
                current_topic=user.current_topic,
                current_lesson=user.current_lesson,
                topics_progress=topics_progress
            )
    
    def reset_user_progress(self, user_id: str) -> bool:
        """Сбросить весь прогресс пользователя"""
        try:
            with self.get_session() as session:
                # Удаляем прогресс по урокам
                session.query(LessonProgress).filter(
                    LessonProgress.user_id == user_id
                ).delete()
                
                # Удаляем сессии тестирования
                session.query(QuizSession).filter(
                    QuizSession.user_id == user_id
                ).delete()
                
                # Сбрасываем прогресс пользователя
                user = session.query(UserProgress).filter(
                    UserProgress.user_id == user_id
                ).first()
                
                if user:
                    user.total_lessons_completed = 0
                    user.total_score = 0.0
                    user.current_topic = "основы_рисков"
                    user.current_lesson = 1
                    user.last_activity = datetime.utcnow()
                
                session.commit()
                logger.info(f"Прогресс пользователя {user_id} сброшен")
                return True
        except Exception as e:
            logger.error(f"Ошибка сброса прогресса пользователя {user_id}: {e}")
            return False
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Получить общую статистику обучения"""
        with self.get_session() as session:
            total_users = session.query(UserProgress).count()
            active_users = session.query(UserProgress).filter(
                UserProgress.total_lessons_completed > 0
            ).count()
            
            completed_lessons = session.query(LessonProgress).filter(
                LessonProgress.is_completed == True
            ).count()
            
            total_attempts = session.query(LessonProgress).count()
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "completed_lessons": completed_lessons,
                "total_attempts": total_attempts,
                "average_completion_rate": (completed_lessons / total_attempts * 100) if total_attempts > 0 else 0
            }


# Глобальный экземпляр сервиса
db_service = DatabaseService()

def save_lesson_session(self, user_id: str, topic_id: str, lesson_id: int, 
                       material_viewed: str = None, questions: list = None, 
                       answers: list = None, score: float = 0.0) -> bool:
    """Сохранить сессию урока в историю"""
    try:
        with self.get_session() as session:
            history_entry = LessonHistory(
                user_id=user_id,
                topic_id=topic_id,
                lesson_id=lesson_id,
                lesson_material_viewed=material_viewed,
                questions_asked=questions,
                answers_given=answers,
                final_score=score
            )
            session.add(history_entry)
            session.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка сохранения истории урока: {e}")
        return False

def get_lesson_history(self, user_id: str, topic_id: str, lesson_id: int) -> List[Dict]:
    """Получить историю прохождения урока"""
    try:
        with self.get_session() as session:
            history = session.query(LessonHistory).filter(
                and_(
                    LessonHistory.user_id == user_id,
                    LessonHistory.topic_id == topic_id,
                    LessonHistory.lesson_id == lesson_id
                )
            ).order_by(LessonHistory.session_date.desc()).all()
            
            return [
                {
                    "date": h.session_date.isoformat(),
                    "material_viewed": h.lesson_material_viewed,
                    "questions": h.questions_asked,
                    "answers": h.answers_given,
                    "score": h.final_score
                }
                for h in history
            ]
    except Exception as e:
        logger.error(f"Ошибка получения истории урока: {e}")
        return []