"""
Сервис для работы с базой данных
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from sqlalchemy import create_engine, and_, text, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from config.settings import settings
from core.models import Base, UserProgress, LessonProgress, QuizSession, LessonHistory
from core.models import UserData, QuizResult, UserProgressResponse

logger = logging.getLogger(__name__)

# Создание движка базы данных с пулом соединений
engine = create_engine(
    settings.database_url,
    pool_size=10,                # Размер пула соединений
    max_overflow=20,             # Максимальное переполнение
    pool_recycle=3600,           # Пересоздание соединений каждый час
    pool_pre_ping=True,          # Проверка соединений перед использованием
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False                   # Отключаем SQL логи для производительности
)

# Создание сессии
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создание таблиц
try:
    Base.metadata.create_all(bind=engine)
    logger.info("✅ [Database] Таблицы базы данных созданы/обновлены")
except Exception as e:
    logger.error(f"❌ [Database] Ошибка создания таблиц: {e}")
    raise


class DatabaseService:
    """Улучшенный сервис для работы с базой данных"""
    
    def __init__(self):
        self.session_factory = SessionLocal
        logger.info("🗄️ [Database] Сервис базы данных инициализирован")
    
    @contextmanager
    def get_session(self):
        """Контекстный менеджер для сессий БД с автоматическим rollback"""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"❌ [Database] Ошибка сессии БД: {e}")
            raise
        finally:
            session.close()
    
    def close(self):
        """Закрыть соединения с БД"""
        try:
            engine.dispose()
            logger.info("✅ [Database] Соединения с БД закрыты")
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка закрытия соединений с БД: {e}")
    
    def get_users_count(self) -> int:
        """Получить количество пользователей"""
        try:
            with self.get_session() as session:
                count = session.query(UserProgress).count()
                logger.debug(f"📊 [Database] Количество пользователей: {count}")
                return count
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка получения количества пользователей: {e}")
            return 0
    
    def health_check(self) -> bool:
        """Проверка состояния БД"""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
                logger.debug("✅ [Database] Health check прошел успешно")
                return True
        except Exception as e:
            logger.error(f"❌ [Database] Health check провален: {e}")
            return False
    
    # Методы для работы с пользователями
    
    def get_or_create_user(self, user_data: UserData) -> UserProgress:
        """Получить или создать пользователя"""
        try:
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
                    logger.info(f"👤 [Database] Создан новый пользователь: {user_data.user_id}")
                else:
                    # Обновляем данные пользователя
                    user.username = user_data.username
                    user.first_name = user_data.first_name
                    user.last_name = user_data.last_name
                    user.last_activity = datetime.utcnow()
                    logger.debug(f"👤 [Database] Обновлены данные пользователя: {user_data.user_id}")
                
                return user
                
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка создания/получения пользователя {user_data.user_id}: {e}")
            raise
    
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
                    logger.debug(f"📊 [Database] Обновлен прогресс пользователя {user_id}: {kwargs}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка обновления прогресса пользователя {user_id}: {e}")
            return False
    
    # Методы для работы с прогрессом уроков
    
    def get_lesson_progress(self, user_id: str, topic_id: str, lesson_id: int) -> Optional[LessonProgress]:
        """Получить прогресс по уроку"""
        try:
            with self.get_session() as session:
                progress = session.query(LessonProgress).filter(
                    and_(
                        LessonProgress.user_id == user_id,
                        LessonProgress.topic_id == topic_id,
                        LessonProgress.lesson_id == lesson_id
                    )
                ).first()
                
                logger.debug(f"📖 [Database] Получен прогресс урока {topic_id}.{lesson_id} для {user_id}")
                return progress
                
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка получения прогресса урока: {e}")
            return None
    
    def get_or_create_lesson_progress(self, user_id: str, topic_id: str, lesson_id: int) -> LessonProgress:
        """Получить или создать прогресс по уроку"""
        try:
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
                    logger.info(f"📝 [Database] Создан прогресс урока {topic_id}.{lesson_id} для {user_id}")
                
                return progress
                
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка создания прогресса урока: {e}")
            raise
    
    def update_lesson_progress(self, user_id: str, topic_id: str, lesson_id: int, 
                             score: float, is_completed: bool = False) -> bool:
        """ИСПРАВЛЕНО: Обновить прогресс урока И общий прогресс пользователя"""
        try:
            with self.get_session() as session:
                progress = session.query(LessonProgress).filter(
                    and_(
                        LessonProgress.user_id == user_id,
                        LessonProgress.topic_id == topic_id,
                        LessonProgress.lesson_id == lesson_id
                    )
                ).first()
                
                if not progress:
                    logger.warning(f"⚠️ [Database] Прогресс урока не найден: {topic_id}.{lesson_id} для {user_id}")
                    return False
                
                # Запоминаем старое состояние
                was_completed_before = progress.is_completed
                
                # Обновляем прогресс урока
                progress.attempts += 1
                progress.last_attempt_score = score
                progress.last_attempt_at = datetime.utcnow()
                
                if score > progress.best_score:
                    progress.best_score = score
                
                if is_completed and not progress.is_completed:
                    progress.is_completed = True
                    progress.completed_at = datetime.utcnow()
                
                # НОВОЕ: Обновляем общий прогресс пользователя если урок завершен впервые
                if is_completed and not was_completed_before:
                    self._update_user_total_progress(session, user_id)
                
                logger.info(f"📊 [Database] Обновлен прогресс урока {topic_id}.{lesson_id}: score={score}, completed={is_completed}")
                return True
                
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка обновления прогресса урока: {e}")
            return False
    
    def _update_user_total_progress(self, session: Session, user_id: str):
        """НОВЫЙ МЕТОД: Обновление общего прогресса пользователя"""
        try:
            # Подсчитываем завершенные уроки
            completed_lessons_count = session.query(LessonProgress).filter(
                and_(
                    LessonProgress.user_id == user_id,
                    LessonProgress.is_completed == True
                )
            ).count()
            
            # Рассчитываем средний балл завершенных уроков
            avg_score_result = session.query(
                func.avg(LessonProgress.best_score)
            ).filter(
                and_(
                    LessonProgress.user_id == user_id,
                    LessonProgress.is_completed == True
                )
            ).scalar()
            
            avg_score = float(avg_score_result) if avg_score_result else 0.0
            
            # Обновляем пользователя
            user = session.query(UserProgress).filter(
                UserProgress.user_id == user_id
            ).first()
            
            if user:
                user.total_lessons_completed = completed_lessons_count
                user.total_score = avg_score
                user.last_activity = datetime.utcnow()
                
                # НОВОЕ: Определяем текущую позицию (следующий доступный урок)
                next_position = self._find_next_available_position(session, user_id)
                if next_position:
                    user.current_topic = next_position['topic']
                    user.current_lesson = next_position['lesson']
                
                logger.info(f"✅ [Database] Общий прогресс обновлен для {user_id}: {completed_lessons_count} уроков, средний балл: {avg_score:.1f}%")
            
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка обновления общего прогресса: {e}")
            raise
    
    def _find_next_available_position(self, session: Session, user_id: str) -> Optional[Dict[str, Any]]:
        """НОВЫЙ МЕТОД: Находит следующую доступную позицию для обучения"""
        try:
            from config.bot_config import LEARNING_STRUCTURE
            
            for topic_id, topic_data in LEARNING_STRUCTURE.items():
                for lesson in topic_data["lessons"]:
                    lesson_id = lesson["id"]
                    
                    # Проверяем, завершен ли урок
                    lesson_progress = session.query(LessonProgress).filter(
                        and_(
                            LessonProgress.user_id == user_id,
                            LessonProgress.topic_id == topic_id,
                            LessonProgress.lesson_id == lesson_id,
                            LessonProgress.is_completed == True
                        )
                    ).first()
                    
                    # Если урок не завершен - это следующая позиция
                    if not lesson_progress:
                        return {"topic": topic_id, "lesson": lesson_id}
            
            # Если все уроки завершены
            return {"topic": "оценка_рисков", "lesson": 7}  # Последний урок
            
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка поиска следующей позиции: {e}")
            return None
    
    def get_user_lessons_progress(self, user_id: str) -> List[LessonProgress]:
        """Получить весь прогресс пользователя по урокам"""
        try:
            with self.get_session() as session:
                progress_list = session.query(LessonProgress).filter(
                    LessonProgress.user_id == user_id
                ).all()
                
                logger.debug(f"📚 [Database] Получен прогресс по {len(progress_list)} урокам для {user_id}")
                return progress_list
                
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка получения прогресса уроков: {e}")
            return []
    
    # Методы для работы с тестированием
    
    def create_quiz_session(self, user_id: str, topic_id: str, lesson_id: int, 
                           questions: List[Dict[str, Any]]) -> QuizSession:
        """Создать сессию тестирования"""
        try:
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
                
                logger.info(f"🧪 [Database] Создана сессия тестирования {quiz_session.id} для {user_id}")
                return quiz_session
                
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка создания сессии тестирования: {e}")
            raise
    
    def get_active_quiz_session(self, user_id: str) -> Optional[QuizSession]:
        """Получить активную сессию тестирования"""
        try:
            with self.get_session() as session:
                session_obj = session.query(QuizSession).filter(
                    and_(
                        QuizSession.user_id == user_id,
                        QuizSession.is_completed == False
                    )
                ).first()
                
                if session_obj:
                    logger.debug(f"🧪 [Database] Найдена активная сессия {session_obj.id} для {user_id}")
                
                return session_obj
                
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка получения активной сессии: {e}")
            return None
    
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
                    
                    logger.debug(f"🧪 [Database] Обновлена сессия тестирования {session_id}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка обновления сессии тестирования: {e}")
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
                    
                    logger.info(f"✅ [Database] Завершена сессия тестирования {session_id} с результатом {final_score}%")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка завершения сессии тестирования: {e}")
            return False
    
    # Методы для аналитики и отчетности
    
    def get_user_progress_summary(self, user_id: str) -> UserProgressResponse:
        """Получить сводку прогресса пользователя"""
        try:
            with self.get_session() as session:
                user = session.query(UserProgress).filter(
                    UserProgress.user_id == user_id
                ).first()
                
                if not user:
                    logger.debug(f"👤 [Database] Пользователь {user_id} не найден, создаем пустой профиль")
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
                    
                    # ИСПРАВЛЕНО: Используем lesson_id как int, НЕ как строку
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
                
                logger.debug(f"📊 [Database] Получена сводка прогресса для {user_id}")
                
                return UserProgressResponse(
                    user_id=user_id,
                    total_lessons_completed=user.total_lessons_completed,
                    total_score=user.total_score,
                    current_topic=user.current_topic,
                    current_lesson=user.current_lesson,
                    topics_progress=topics_progress
                )
                
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка получения сводки прогресса: {e}")
            raise
    
    def reset_user_progress(self, user_id: str) -> bool:
        """Сбросить весь прогресс пользователя"""
        try:
            with self.get_session() as session:
                # Удаляем прогресс по урокам
                deleted_lessons = session.query(LessonProgress).filter(
                    LessonProgress.user_id == user_id
                ).delete()
                
                # Удаляем сессии тестирования
                deleted_sessions = session.query(QuizSession).filter(
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
                
                logger.info(f"🔄 [Database] Прогресс пользователя {user_id} сброшен: {deleted_lessons} уроков, {deleted_sessions} сессий")
                return True
                
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка сброса прогресса пользователя {user_id}: {e}")
            return False
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Получить общую статистику обучения"""
        try:
            with self.get_session() as session:
                total_users = session.query(UserProgress).count()
                active_users = session.query(UserProgress).filter(
                    UserProgress.total_lessons_completed > 0
                ).count()
                
                completed_lessons = session.query(LessonProgress).filter(
                    LessonProgress.is_completed == True
                ).count()
                
                total_attempts = session.query(LessonProgress).count()
                
                stats = {
                    "total_users": total_users,
                    "active_users": active_users,
                    "completed_lessons": completed_lessons,
                    "total_attempts": total_attempts,
                    "average_completion_rate": (completed_lessons / total_attempts * 100) if total_attempts > 0 else 0
                }
                
                logger.debug(f"📈 [Database] Получена статистика обучения: {stats}")
                return stats
                
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка получения статистики: {e}")
            return {}
    
    # Методы для работы с историей уроков
    
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
                
                logger.debug(f"📝 [Database] Сохранена история урока {topic_id}.{lesson_id} для {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка сохранения истории урока: {e}")
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
                
                result = [
                    {
                        "date": h.session_date.isoformat(),
                        "material_viewed": h.lesson_material_viewed,
                        "questions": h.questions_asked,
                        "answers": h.answers_given,
                        "score": h.final_score
                    }
                    for h in history
                ]
                
                logger.debug(f"📚 [Database] Получена история {len(result)} сессий урока {topic_id}.{lesson_id}")
                return result
                
        except Exception as e:
            logger.error(f"❌ [Database] Ошибка получения истории урока: {e}")
            return []


# Глобальный экземпляр сервиса
db_service = DatabaseService()

# Функция для тестирования сервиса
def test_database_service():
    """Тестирование основных функций сервиса БД"""
    try:
        logger.info("🧪 [Database] Начало тестирования сервиса БД...")
        
        # Проверяем health check
        if not db_service.health_check():
            raise Exception("Health check провален")
        
        # Проверяем счетчик пользователей
        users_count = db_service.get_users_count()
        logger.info(f"👥 [Database] Количество пользователей: {users_count}")
        
        logger.info("✅ [Database] Тестирование завершено успешно")
        return True
        
    except Exception as e:
        logger.error(f"❌ [Database] Тестирование провалено: {e}")
        return False

# Запускаем тест при импорте модуля
if __name__ == "__main__":
    test_database_service()