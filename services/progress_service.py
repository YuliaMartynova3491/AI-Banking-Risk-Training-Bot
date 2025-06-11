# Файл: services/progress_service.py
"""
Сервис управления прогрессом обучения - УЛУЧШЕННАЯ ВЕРСИЯ
Основные улучшения:
1. Правильная логика обновления прогресса
2. Исправлена функция update_lesson_completion
3. Добавлены методы для отладки и мониторинга
4. Улучшена производительность
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from core.database import db_service
from config.bot_config import LEARNING_STRUCTURE

logger = logging.getLogger(__name__)

class ProgressService:
    """Сервис для управления прогрессом обучения пользователей"""
    
    @staticmethod
    def update_lesson_completion(user_id: int, topic_id: str, lesson_id: int, 
                               score: int, passed: bool = None) -> Dict[str, Any]:
        """
        ИСПРАВЛЕНО: Обновление результатов урока с правильной логикой
        """
        try:
            logger.info(f"[update_lesson_completion] user_id={user_id}, topic_id={topic_id}, lesson_id={lesson_id}, score={score}, passed={passed}")
            
            # Получаем текущий прогресс
            user_progress = db_service.get_user_progress(user_id)
            if not user_progress:
                user_progress = ProgressService._create_initial_progress()
            
            # Инициализируем структуру если нужно
            if "topics_progress" not in user_progress:
                user_progress["topics_progress"] = {}
            
            if topic_id not in user_progress["topics_progress"]:
                user_progress["topics_progress"][topic_id] = {
                    "lessons": {},
                    "completed_lessons": 0,
                    "total_score": 0,
                    "total_attempts": 0
                }
            
            topic_progress = user_progress["topics_progress"][topic_id]
            
            # ИСПРАВЛЕНО: Используем lesson_id как число, НЕ как строку
            if lesson_id not in topic_progress["lessons"]:
                topic_progress["lessons"][lesson_id] = {
                    "attempts": 0,
                    "best_score": 0,
                    "is_completed": False,
                    "completion_date": None
                }
            
            lesson_data = topic_progress["lessons"][lesson_id]
            
            # Обновляем статистику урока
            lesson_data["attempts"] += 1
            lesson_data["best_score"] = max(lesson_data["best_score"], score)
            
            # ИСПРАВЛЕНО: Логика завершения урока
            passing_score = 70  # Минимальный балл для прохождения
            
            if passed is None:
                passed = score >= passing_score
            
            # Если урок пройден и еще не был завершен
            if passed and not lesson_data["is_completed"]:
                lesson_data["is_completed"] = True
                lesson_data["completion_date"] = datetime.now().isoformat()
                
                # Увеличиваем счетчик завершенных уроков в теме
                topic_progress["completed_lessons"] += 1
                logger.info(f"[update_lesson_completion] ✅ Урок {lesson_id} темы {topic_id} завершен! Всего завершено: {topic_progress['completed_lessons']}")
            
            # Обновляем общую статистику темы
            topic_progress["total_attempts"] += 1
            
            # Пересчитываем общий прогресс пользователя
            ProgressService._recalculate_total_progress(user_progress)
            
            # Сохраняем в базу
            db_service.update_user_progress(user_id, user_progress)
            
            logger.info(f"[update_lesson_completion] ✅ Прогресс успешно обновлен")
            
            return {
                "success": True,
                "lesson_completed": passed and lesson_data["is_completed"],
                "total_completed": user_progress.get("total_lessons_completed", 0),
                "topic_completed_lessons": topic_progress["completed_lessons"]
            }
            
        except Exception as e:
            logger.error(f"[update_lesson_completion] ❌ Ошибка обновления прогресса: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _recalculate_total_progress(user_progress: Dict[str, Any]) -> None:
        """Пересчитывает общий прогресс пользователя"""
        try:
            total_completed = 0
            total_score = 0
            total_attempts = 0
            
            topics_progress = user_progress.get("topics_progress", {})
            
            for topic_id, topic_data in topics_progress.items():
                completed_lessons = topic_data.get("completed_lessons", 0)
                total_completed += completed_lessons
                
                lessons_data = topic_data.get("lessons", {})
                for lesson_data in lessons_data.values():
                    if lesson_data.get("is_completed"):
                        total_score += lesson_data.get("best_score", 0)
                    total_attempts += lesson_data.get("attempts", 0)
            
            # Вычисляем средний балл
            avg_score = (total_score / total_completed) if total_completed > 0 else 0
            
            # Обновляем общие метрики
            user_progress.update({
                "total_lessons_completed": total_completed,
                "total_score": round(avg_score, 1),
                "total_attempts": total_attempts,
                "last_activity": datetime.now().isoformat()
            })
            
            logger.info(f"[_recalculate_total_progress] Пересчитан прогресс: завершено={total_completed}, средний_балл={avg_score}")
            
        except Exception as e:
            logger.error(f"[_recalculate_total_progress] Ошибка пересчета: {e}")
    
    @staticmethod
    def _create_initial_progress() -> Dict[str, Any]:
        """Создает начальную структуру прогресса"""
        return {
            "topics_progress": {},
            "total_lessons_completed": 0,
            "total_score": 0,
            "total_attempts": 0,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }
    
    @staticmethod
    def get_lesson_status(user_id: int, topic_id: str, lesson_id: int) -> Dict[str, Any]:
        """Получает статус конкретного урока"""
        try:
            user_progress = db_service.get_user_progress(user_id)
            if not user_progress:
                return {"is_completed": False, "attempts": 0, "best_score": 0}
            
            topic_progress = user_progress.get("topics_progress", {}).get(topic_id, {})
            lessons_data = topic_progress.get("lessons", {})
            lesson_data = lessons_data.get(lesson_id, {})
            
            return {
                "is_completed": lesson_data.get("is_completed", False),
                "attempts": lesson_data.get("attempts", 0),
                "best_score": lesson_data.get("best_score", 0),
                "completion_date": lesson_data.get("completion_date")
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статуса урока: {e}")
            return {"is_completed": False, "attempts": 0, "best_score": 0}
    
    @staticmethod
    def get_topic_progress(user_id: int, topic_id: str) -> Dict[str, Any]:
        """Получает прогресс по конкретной теме"""
        try:
            user_progress = db_service.get_user_progress(user_id)
            if not user_progress:
                return {"completed_lessons": 0, "total_lessons": 0, "progress_percentage": 0}
            
            topic_progress = user_progress.get("topics_progress", {}).get(topic_id, {})
            completed_lessons = topic_progress.get("completed_lessons", 0)
            
            total_lessons = len(LEARNING_STRUCTURE.get(topic_id, {}).get("lessons", []))
            progress_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
            
            return {
                "completed_lessons": completed_lessons,
                "total_lessons": total_lessons,
                "progress_percentage": round(progress_percentage, 1),
                "total_attempts": topic_progress.get("total_attempts", 0)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения прогресса темы: {e}")
            return {"completed_lessons": 0, "total_lessons": 0, "progress_percentage": 0}
    
    @staticmethod
    def reset_user_progress(user_id: int) -> bool:
        """Сбрасывает весь прогресс пользователя"""
        try:
            initial_progress = ProgressService._create_initial_progress()
            db_service.update_user_progress(user_id, initial_progress)
            logger.info(f"Прогресс пользователя {user_id} сброшен")
            return True
        except Exception as e:
            logger.error(f"Ошибка сброса прогресса: {e}")
            return False
    
    @staticmethod
    def get_user_achievements(user_id: int) -> Dict[str, Any]:
        """Получает достижения пользователя"""
        try:
            user_progress = db_service.get_user_progress(user_id)
            if not user_progress:
                return {"achievements": [], "total_points": 0}
            
            achievements = []
            total_completed = user_progress.get("total_lessons_completed", 0)
            avg_score = user_progress.get("total_score", 0)
            
            # Достижения за количество завершенных уроков
            if total_completed >= 1:
                achievements.append("🎯 Первые шаги")
            if total_completed >= 5:
                achievements.append("📚 Знаток")
            if total_completed >= 10:
                achievements.append("🏆 Эксперт")
            
            # Достижения за качество
            if avg_score >= 80:
                achievements.append("⭐ Отличник")
            if avg_score >= 90:
                achievements.append("🌟 Мастер")
            
            # Достижения за темы
            topics_progress = user_progress.get("topics_progress", {})
            for topic_id, topic_data in topics_progress.items():
                total_lessons = len(LEARNING_STRUCTURE.get(topic_id, {}).get("lessons", []))
                completed = topic_data.get("completed_lessons", 0)
                if completed == total_lessons and total_lessons > 0:
                    topic_title = LEARNING_STRUCTURE[topic_id]["title"]
                    achievements.append(f"✅ {topic_title}")
            
            return {
                "achievements": achievements,
                "total_points": len(achievements) * 10,
                "completion_rate": round((total_completed / 12 * 100), 1) if total_completed > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения достижений: {e}")
            return {"achievements": [], "total_points": 0}
    
    @staticmethod 
    def debug_user_progress(user_id: int) -> str:
        """НОВЫЙ МЕТОД: Отладочная информация о прогрессе пользователя"""
        try:
            user_progress = db_service.get_user_progress(user_id)
            if not user_progress:
                return "❌ Прогресс пользователя не найден"
            
            debug_info = []
            debug_info.append(f"🔍 ОТЛАДКА ПРОГРЕССА ПОЛЬЗОВАТЕЛЯ {user_id}")
            debug_info.append(f"📊 Общая статистика:")
            debug_info.append(f"   - Завершено уроков: {user_progress.get('total_lessons_completed', 0)}")
            debug_info.append(f"   - Средний балл: {user_progress.get('total_score', 0)}")
            debug_info.append(f"   - Всего попыток: {user_progress.get('total_attempts', 0)}")
            
            topics_progress = user_progress.get("topics_progress", {})
            debug_info.append(f"\n📚 Прогресс по темам:")
            
            for topic_id, topic_data in topics_progress.items():
                debug_info.append(f"   🎯 {topic_id}:")
                debug_info.append(f"      - Завершено уроков: {topic_data.get('completed_lessons', 0)}")
                debug_info.append(f"      - Попыток: {topic_data.get('total_attempts', 0)}")
                
                lessons_data = topic_data.get("lessons", {})
                debug_info.append(f"      - Уроки:")
                for lesson_id, lesson_data in lessons_data.items():
                    status = "✅" if lesson_data.get("is_completed") else "❌"
                    debug_info.append(f"        {status} Урок {lesson_id}: {lesson_data.get('attempts', 0)} попыток, лучший результат: {lesson_data.get('best_score', 0)}%")
            
            return "\n".join(debug_info)
            
        except Exception as e:
            return f"❌ Ошибка отладки: {e}"

# Создаем экземпляр сервиса
progress_service = ProgressService()