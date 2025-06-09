"""
Сервис для глубокого анализа прогресса и профиля пользователя.
Централизует всю аналитическую логику.
"""
import logging
from typing import Dict, Any

from core.database import db_service
from services.progress_service import progress_service

logger = logging.getLogger(__name__)


class UserAnalysisService:
    """Сервис для анализа пользователя."""

    def get_full_user_analysis(self, user_id: str) -> Dict[str, Any]:
        """
        Собирает полный аналитический профиль пользователя.
        Это основная точка входа для получения данных об пользователе.
        """
        try:
            progress_summary = db_service.get_user_progress_summary(user_id)
            detailed_stats = progress_service.get_overall_statistics(user_id)

            user_profile = self._build_user_profile(progress_summary, detailed_stats)
            learning_patterns = self._analyze_learning_patterns(detailed_stats)
            personalization_strategy = self._determine_personalization_strategy(user_profile, learning_patterns)
            content_settings = self._configure_content_settings(personalization_strategy)

            return {
                "user_progress": progress_summary.dict(),
                "detailed_statistics": detailed_stats,
                "user_profile": user_profile,
                "learning_patterns": learning_patterns,
                "personalization_strategy": personalization_strategy,
                "content_settings": content_settings
            }
        except Exception as e:
            logger.error(f"Ошибка полного анализа пользователя {user_id}: {e}")
            return {"error": str(e)}

    def _analyze_learning_patterns(self, detailed_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Анализ паттернов обучения пользователя."""
        patterns = {
            "learning_speed": "normal",
            "consistency": "variable",
            "strength_areas": [],
            "challenge_areas": [],
            "preferred_difficulty": "intermediate",
            "engagement_level": "medium"
        }
        try:
            completion_rate = detailed_stats.get("overall_completion", 0)
            if completion_rate > 80:
                patterns["learning_speed"] = "fast"
            elif completion_rate < 40:
                patterns["learning_speed"] = "slow"

            topic_stats = detailed_stats.get("topics_statistics", {})
            for topic_id, stats in topic_stats.items():
                avg_score = stats.get("average_score", 0)
                if avg_score >= 85:
                    patterns["strength_areas"].append(topic_id)
                elif avg_score > 0 and avg_score < 70:
                    patterns["challenge_areas"].append(topic_id)
            
            avg_score = detailed_stats.get("average_score", 70)
            if avg_score >= 90:
                patterns["preferred_difficulty"] = "advanced"
            elif avg_score < 65:
                patterns["preferred_difficulty"] = "beginner"
        except Exception as e:
            logger.error(f"Ошибка анализа паттернов обучения: {e}")
        return patterns

    def _build_user_profile(self, progress_summary, detailed_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Построение профиля пользователя."""
        profile = {
            "experience_level": "beginner",
            "motivation_level": "medium",
            "support_needs": "medium",
        }
        try:
            completed_lessons = progress_summary.total_lessons_completed
            if completed_lessons >= 10:
                profile["experience_level"] = "advanced"
            elif completed_lessons >= 5:
                profile["experience_level"] = "intermediate"

            avg_score = detailed_stats.get("average_score", 0)
            if avg_score >= 85:
                profile["motivation_level"] = "high"
            elif avg_score < 60:
                profile["motivation_level"] = "low"

            weak_topics_count = len(detailed_stats.get("weak_topics", []))
            if weak_topics_count >= 2:
                profile["support_needs"] = "high"
            elif weak_topics_count == 0:
                profile["support_needs"] = "low"
        except Exception as e:
            logger.error(f"Ошибка построения профиля пользователя: {e}")
        return profile

    def _determine_personalization_strategy(self, user_profile: Dict[str, Any], learning_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Определение стратегии персонализации."""
        strategy = {
            "approach": "adaptive",
            "support_level": user_profile.get("support_needs", "medium"),
            "difficulty_progression": "gradual",
        }
        if learning_patterns.get("learning_speed") == "fast":
            strategy["difficulty_progression"] = "accelerated"
        elif learning_patterns.get("learning_speed") == "slow":
            strategy["difficulty_progression"] = "gentle"
        return strategy

    def _configure_content_settings(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Настройка параметров контента."""
        settings = {
            "difficulty": "intermediate",
            "question_count": 3,
            "explanation_detail": "medium",
        }
        if strategy.get("difficulty_progression") == "accelerated":
            settings["difficulty"] = "advanced"
        elif strategy.get("difficulty_progression") == "gentle":
            settings["difficulty"] = "beginner"

        if strategy.get("support_level") == "high":
            settings["explanation_detail"] = "detailed"
        elif strategy.get("support_level") == "low":
            settings["explanation_detail"] = "concise"
        return settings


# Глобальный экземпляр сервиса
user_analysis_service = UserAnalysisService()