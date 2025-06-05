"""
Перечисления и константы для AI-агента
"""
from enum import Enum, IntEnum


class LearningDifficulty(Enum):
    """Уровни сложности обучения"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class LearningSpeed(Enum):
    """Скорость обучения пользователя"""
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"


class QuestionType(Enum):
    """Типы вопросов"""
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"


class TopicStatus(Enum):
    """Статус темы"""
    LOCKED = "locked"
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class LessonStatus(Enum):
    """Статус урока"""
    LOCKED = "locked"
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class UserRole(Enum):
    """Роли пользователей"""
    STUDENT = "student"
    ADMIN = "admin"
    INSTRUCTOR = "instructor"


class NotificationType(Enum):
    """Типы уведомлений"""
    LESSON_COMPLETE = "lesson_complete"
    TOPIC_COMPLETE = "topic_complete"
    REMINDER = "reminder"
    ACHIEVEMENT = "achievement"


class AIAgentAction(Enum):
    """Действия AI-агента"""
    GENERATE_QUESTIONS = "generate_questions"
    PROVIDE_HELP = "provide_help"
    ANALYZE_PROGRESS = "analyze_progress"
    ADAPT_DIFFICULTY = "adapt_difficulty"
    GIVE_RECOMMENDATION = "give_recommendation"


class RiskThreatType(Enum):
    """Типы угроз из методики"""
    TECHNOLOGICAL = "технологические"
    SOCIAL = "социальные"
    NATURAL = "природные"
    GEOPOLITICAL = "геополитические"
    ECONOMIC = "экономические"
    BIOLOGICAL_SOCIAL = "биолого-социальные"


# Константы
class Constants:
    """Константы системы"""
    
    # Ограничения
    MAX_QUESTIONS_PER_LESSON = 10
    MIN_QUESTIONS_PER_LESSON = 1
    MAX_LESSON_ATTEMPTS = 5
    MAX_USERNAME_LENGTH = 50
    MAX_QUESTION_LENGTH = 500
    MAX_EXPLANATION_LENGTH = 1000
    
    # Временные интервалы (в секундах)
    SESSION_TIMEOUT = 1800  # 30 минут
    QUIZ_TIMEOUT = 900      # 15 минут
    AI_RESPONSE_TIMEOUT = 30  # 30 секунд
    
    # Пороговые значения
    DEFAULT_PASS_SCORE = 80
    HIGH_PERFORMANCE_THRESHOLD = 90
    LOW_PERFORMANCE_THRESHOLD = 60
    
    # Сообщения
    ERROR_GENERIC = "Произошла ошибка. Попробуйте позже."
    ERROR_SESSION_EXPIRED = "Сессия истекла. Начните заново."
    ERROR_INVALID_INPUT = "Некорректный ввод. Попробуйте еще раз."
    
    # Форматирование
    PROGRESS_BAR_LENGTH = 20
    DECIMAL_PLACES = 1
    
    # AI настройки
    AI_MAX_RETRIES = 3
    AI_TEMPERATURE = 0.7
    AI_MAX_TOKENS = 1000


class ScoreRanges(IntEnum):
    """Диапазоны оценок"""
    EXCELLENT_MIN = 90
    GOOD_MIN = 80
    SATISFACTORY_MIN = 60
    POOR_MAX = 59


class MessagePriority(IntEnum):
    """Приоритеты сообщений"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


# Маппинги для удобства
DIFFICULTY_ORDER = [
    LearningDifficulty.BEGINNER,
    LearningDifficulty.INTERMEDIATE,
    LearningDifficulty.ADVANCED
]

TOPIC_ORDER = [
    "основы_рисков",
    "критичность_процессов", 
    "оценка_рисков"
]

SCORE_DESCRIPTIONS = {
    ScoreRanges.EXCELLENT_MIN: "Отлично",
    ScoreRanges.GOOD_MIN: "Хорошо",
    ScoreRanges.SATISFACTORY_MIN: "Удовлетворительно",
    0: "Неудовлетворительно"
}

# Эмодзи для статусов
STATUS_EMOJIS = {
    TopicStatus.LOCKED: "🔒",
    TopicStatus.AVAILABLE: "📖",
    TopicStatus.IN_PROGRESS: "📚",
    TopicStatus.COMPLETED: "✅"
}

LESSON_EMOJIS = {
    LessonStatus.LOCKED: "🔒",
    LessonStatus.AVAILABLE: "📝",
    LessonStatus.IN_PROGRESS: "🔄",
    LessonStatus.COMPLETED: "✅",
    LessonStatus.FAILED: "❌"
}