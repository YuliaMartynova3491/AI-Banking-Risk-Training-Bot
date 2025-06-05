"""
Вспомогательные функции для AI-агента
"""
import re
import json
import logging
import random
import os
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from core.enums import ScoreRanges, SCORE_DESCRIPTIONS, Constants
from config.bot_config import LEARNING_STRUCTURE

logger = logging.getLogger(__name__)


def format_score(score: float) -> str:
    """Форматирование оценки с описанием"""
    score_int = int(score)
    
    if score >= ScoreRanges.EXCELLENT_MIN:
        description = SCORE_DESCRIPTIONS[ScoreRanges.EXCELLENT_MIN]
        emoji = "🌟"
    elif score >= ScoreRanges.GOOD_MIN:
        description = SCORE_DESCRIPTIONS[ScoreRanges.GOOD_MIN] 
        emoji = "✅"
    elif score >= ScoreRanges.SATISFACTORY_MIN:
        description = SCORE_DESCRIPTIONS[ScoreRanges.SATISFACTORY_MIN]
        emoji = "📚"
    else:
        description = SCORE_DESCRIPTIONS[0]
        emoji = "📖"
    
    return f"{emoji} {score_int}% ({description})"


def create_progress_bar(completed: int, total: int, length: int = Constants.PROGRESS_BAR_LENGTH) -> str:
    """Создание текстового прогресс-бара"""
    if total == 0:
        return "▱" * length
    
    filled_length = int(length * completed / total)
    bar = "▰" * filled_length + "▱" * (length - filled_length)
    percentage = (completed / total) * 100
    
    return f"{bar} {percentage:.1f}% ({completed}/{total})"


def format_duration(seconds: int) -> str:
    """Форматирование длительности в читаемый вид"""
    if seconds < 60:
        return f"{seconds} сек"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} мин"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes == 0:
            return f"{hours} ч"
        else:
            return f"{hours} ч {minutes} мин"


def format_datetime(dt: datetime, format_type: str = "full") -> str:
    """Форматирование даты и времени"""
    if format_type == "full":
        return dt.strftime("%d.%m.%Y %H:%M")
    elif format_type == "date":
        return dt.strftime("%d.%m.%Y")
    elif format_type == "time":
        return dt.strftime("%H:%M")
    elif format_type == "relative":
        return format_relative_time(dt)
    else:
        return dt.isoformat()


def format_relative_time(dt: datetime) -> str:
    """Форматирование времени относительно текущего момента"""
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} дн. назад"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} ч назад"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} мин назад"
    else:
        return "только что"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Обрезание текста до указанной длины"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def clean_text(text: str) -> str:
    """Очистка текста от лишних символов"""
    # Удаляем лишние пробелы и переносы строк
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Удаляем HTML-теги если есть
    text = re.sub(r'<[^>]+>', '', text)
    
    return text


def validate_callback_data(data: str, expected_parts: int) -> Optional[List[str]]:
    """Валидация и разбор callback_data"""
    if not data:
        return None
    
    parts = data.split('_')
    
    if len(parts) != expected_parts:
        logger.warning(f"Invalid callback data format: {data}, expected {expected_parts} parts")
        return None
    
    return parts


def safe_int_conversion(value: Any, default: int = 0) -> int:
    """Безопасное преобразование в int"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """Безопасное преобразование в float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def calculate_percentage(part: Union[int, float], total: Union[int, float]) -> float:
    """Безопасное вычисление процентов"""
    if total == 0:
        return 0.0
    return (part / total) * 100


def extract_topic_and_lesson(callback_data: str) -> Tuple[Optional[str], Optional[int]]:
    """Извлечение темы и урока из callback_data"""
    try:
        parts = callback_data.split('_')
        
        # Ищем тему и урок в разных форматах
        topic_id = None
        lesson_id = None
        
        for i, part in enumerate(parts):
            # Проверяем, является ли часть известной темой
            if part in LEARNING_STRUCTURE:
                topic_id = part
                # Следующая часть может быть lesson_id
                if i + 1 < len(parts) and parts[i + 1].isdigit():
                    lesson_id = int(parts[i + 1])
                break
        
        return topic_id, lesson_id
        
    except Exception as e:
        logger.error(f"Ошибка извлечения темы и урока из {callback_data}: {e}")
        return None, None


def generate_unique_id(prefix: str = "") -> str:
    """Генерация уникального ID"""
    import uuid
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique_part = str(uuid.uuid4())[:8]
    
    if prefix:
        return f"{prefix}_{timestamp}_{unique_part}"
    else:
        return f"{timestamp}_{unique_part}"


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Разбивка списка на чанки указанного размера"""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Превращение вложенного словаря в плоский"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Глубокое слияние двух словарей"""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def load_json_file(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Безопасная загрузка JSON файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Файл не найден: {file_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка JSON в файле {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Ошибка загрузки файла {file_path}: {e}")
        return None


def save_json_file(data: Dict[str, Any], file_path: Union[str, Path]) -> bool:
    """Безопасное сохранение в JSON файл"""
    try:
        # Создаем директорию если её нет
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения файла {file_path}: {e}")
        return False


def get_nested_value(data: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """Получение значения по вложенному ключу (например, 'user.profile.name')"""
    keys = key_path.split('.')
    current = data
    
    try:
        for key in keys:
            current = current[key]
        return current
    except (KeyError, TypeError):
        return default


def set_nested_value(data: Dict[str, Any], key_path: str, value: Any) -> Dict[str, Any]:
    """Установка значения по вложенному ключу"""
    keys = key_path.split('.')
    current = data
    
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value
    return data


def filter_dict_keys(data: Dict[str, Any], allowed_keys: List[str]) -> Dict[str, Any]:
    """Фильтрация словаря по разрешенным ключам"""
    return {k: v for k, v in data.items() if k in allowed_keys}


def remove_dict_keys(data: Dict[str, Any], keys_to_remove: List[str]) -> Dict[str, Any]:
    """Удаление указанных ключей из словаря"""
    return {k: v for k, v in data.items() if k not in keys_to_remove}


def format_list_as_text(items: List[str], bullet_point: str = "•", max_items: int = None) -> str:
    """Форматирование списка в текст с маркерами"""
    if not items:
        return "Нет элементов"
    
    if max_items and len(items) > max_items:
        items = items[:max_items]
        items.append(f"... и еще {len(items) - max_items}")
    
    return "\n".join(f"{bullet_point} {item}" for item in items)


def extract_mentions(text: str) -> List[str]:
    """Извлечение упоминаний пользователей из текста"""
    pattern = r'@(\w+)'
    return re.findall(pattern, text)


def extract_hashtags(text: str) -> List[str]:
    """Извлечение хэштегов из текста"""
    pattern = r'#(\w+)'
    return re.findall(pattern, text)


def normalize_phone_number(phone: str) -> str:
    """Нормализация номера телефона"""
    # Удаляем все кроме цифр
    digits = re.sub(r'\D', '', phone)
    
    # Добавляем код страны если нужно
    if len(digits) == 10:  # Российский номер без кода страны
        digits = '7' + digits
    elif len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
    
    return digits


def validate_email(email: str) -> bool:
    """Валидация email адреса"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def generate_random_string(length: int = 8, include_numbers: bool = True) -> str:
    """Генерация случайной строки"""
    import random
    import string
    
    chars = string.ascii_letters
    if include_numbers:
        chars += string.digits
    
    return ''.join(random.choice(chars) for _ in range(length))


def mask_sensitive_data(text: str, mask_char: str = "*") -> str:
    """Маскировка чувствительных данных в тексте"""
    # Маскируем телефоны
    text = re.sub(r'\b\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{2}[-.\s]?\d{2}\b', 
                  lambda m: mask_char * len(m.group()), text)
    
    # Маскируем email
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                  lambda m: mask_char * len(m.group()), text)
    
    return text


def calculate_text_similarity(text1: str, text2: str) -> float:
    """Простое вычисление схожести текстов (по пересечению слов)"""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    if not union:
        return 0.0
    
    return len(intersection) / len(union)


def format_currency(amount: float, currency: str = "₽") -> str:
    """Форматирование суммы в валюте"""
    return f"{amount:,.2f} {currency}".replace(",", " ")


def is_business_hours(dt: datetime = None) -> bool:
    """Проверка, является ли время рабочим"""
    if dt is None:
        dt = datetime.now()
    
    # Рабочие часы: понедельник-пятница, 9:00-18:00
    weekday = dt.weekday()  # 0 = понедельник, 6 = воскресенье
    hour = dt.hour
    
    return weekday < 5 and 9 <= hour < 18


def get_week_boundaries(dt: datetime = None) -> Tuple[datetime, datetime]:
    """Получение границ недели (понедельник - воскресенье)"""
    if dt is None:
        dt = datetime.now()
    
    # Понедельник текущей недели
    monday = dt - timedelta(days=dt.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Воскресенье текущей недели
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    return monday, sunday


def batch_process(items: List[Any], batch_size: int, processor_func, *args, **kwargs) -> List[Any]:
    """Пакетная обработка элементов списка"""
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        try:
            batch_result = processor_func(batch, *args, **kwargs)
            if isinstance(batch_result, list):
                results.extend(batch_result)
            else:
                results.append(batch_result)
        except Exception as e:
            logger.error(f"Ошибка обработки пакета {i//batch_size + 1}: {e}")
            continue
    
    return results


def retry_on_failure(max_attempts: int = 3, delay: float = 1.0):
    """Декоратор для повторных попыток при ошибках"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise e
                    
                    logger.warning(f"Попытка {attempt + 1} неудачна в {func.__name__}: {e}")
                    import time
                    time.sleep(delay * (attempt + 1))  # Увеличиваем задержку
            
        return wrapper
    return decorator


def memoize(func):
    """Простой декоратор мемоизации"""
    cache = {}
    
    def wrapper(*args, **kwargs):
        key = str(args) + str(sorted(kwargs.items()))
        
        if key in cache:
            return cache[key]
        
        result = func(*args, **kwargs)
        cache[key] = result
        return result
    
    return wrapper


def encode_base64(text: str) -> str:
    """Кодирование текста в base64"""
    import base64
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')


def decode_base64(encoded_text: str) -> str:
    """Декодирование из base64"""
    import base64
    try:
        return base64.b64decode(encoded_text.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error(f"Ошибка декодирования base64: {e}")
        return ""


def generate_hash(text: str, algorithm: str = 'sha256') -> str:
    """Генерация хеша от текста"""
    import hashlib
    
    hash_obj = getattr(hashlib, algorithm)()
    hash_obj.update(text.encode('utf-8'))
    return hash_obj.hexdigest()


def is_valid_json(text: str) -> bool:
    """Проверка, является ли строка валидным JSON"""
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


def extract_numbers(text: str) -> List[float]:
    """Извлечение всех чисел из текста"""
    pattern = r'-?\d+(?:\.\d+)?'
    matches = re.findall(pattern, text)
    return [float(match) for match in matches]


def format_file_size(size_bytes: int) -> str:
    """Форматирование размера файла в читаемый вид"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    
    return f"{s} {size_names[i]}"


def get_file_extension(filename: str) -> str:
    """Получение расширения файла"""
    return Path(filename).suffix.lower()


def is_image_file(filename: str) -> bool:
    """Проверка, является ли файл изображением"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}
    return get_file_extension(filename) in image_extensions


def create_temporary_file(content: str, suffix: str = '.txt') -> str:
    """Создание временного файла с контентом"""
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False, encoding='utf-8') as f:
        f.write(content)
        return f.name


def delete_file_safely(file_path: Union[str, Path]) -> bool:
    """Безопасное удаление файла"""
    try:
        Path(file_path).unlink(missing_ok=True)
        return True
    except Exception as e:
        logger.error(f"Ошибка удаления файла {file_path}: {e}")
        return False


def ensure_directory_exists(directory: Union[str, Path]) -> bool:
    """Создание директории если её нет"""
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Ошибка создания директории {directory}: {e}")
        return False


def get_learning_statistics_summary(user_stats: Dict[str, Any]) -> Dict[str, str]:
    """Создание краткой сводки статистики обучения"""
    summary = {}
    
    # Общий прогресс
    overall_completion = user_stats.get('overall_completion', 0)
    summary['completion'] = f"{overall_completion:.1f}%"
    
    # Средняя оценка
    avg_score = user_stats.get('average_score', 0)
    summary['average_score'] = format_score(avg_score)
    
    # Уроки
    completed_lessons = user_stats.get('total_lessons_completed', 0)
    total_lessons = user_stats.get('total_lessons_available', 0)
    summary['lessons'] = f"{completed_lessons}/{total_lessons}"
    
    # Слабые места
    weak_topics = user_stats.get('weak_topics', [])
    if weak_topics:
        topic_names = []
        for topic_id in weak_topics:
            if topic_id in LEARNING_STRUCTURE:
                topic_names.append(LEARNING_STRUCTURE[topic_id]['title'])
        summary['weak_areas'] = ', '.join(topic_names[:2])  # Первые 2
    else:
        summary['weak_areas'] = 'Нет'
    
    # Сильные стороны
    strong_topics = user_stats.get('strong_topics', [])
    if strong_topics:
        topic_names = []
        for topic_id in strong_topics:
            if topic_id in LEARNING_STRUCTURE:
                topic_names.append(LEARNING_STRUCTURE[topic_id]['title'])
        summary['strong_areas'] = ', '.join(topic_names[:2])  # Первые 2
    else:
        summary['strong_areas'] = 'Развиваются'
    
    return summary


def format_topic_progress(topic_stats: Dict[str, Any]) -> str:
    """Форматирование прогресса по теме"""
    completed = topic_stats.get('completed_lessons', 0)
    total = topic_stats.get('total_lessons', 0)
    avg_score = topic_stats.get('average_score', 0)
    
    progress_bar = create_progress_bar(completed, total, 10)
    score_text = format_score(avg_score) if avg_score > 0 else "Не начато"
    
    return f"{progress_bar}\n{score_text}"


def get_next_available_lesson(user_progress: Dict[str, Any]) -> Tuple[Optional[str], Optional[int]]:
    """Получение следующего доступного урока"""
    current_topic = user_progress.get('current_topic')
    current_lesson = user_progress.get('current_lesson', 1)
    
    if not current_topic or current_topic not in LEARNING_STRUCTURE:
        return "основы_рисков", 1
    
    # Проверяем, есть ли следующий урок в текущей теме
    topic_data = LEARNING_STRUCTURE[current_topic]
    total_lessons = len(topic_data['lessons'])
    
    if current_lesson < total_lessons:
        return current_topic, current_lesson
    
    # Переходим к следующей теме
    topic_order = ["основы_рисков", "критичность_процессов", "оценка_рисков"]
    try:
        current_index = topic_order.index(current_topic)
        if current_index + 1 < len(topic_order):
            return topic_order[current_index + 1], 1
    except ValueError:
        pass
    
    return None, None  # Все уроки завершены


def calculate_study_time_estimate(lessons_remaining: int, user_performance: Dict[str, Any] = None) -> str:
    """Оценка времени изучения оставшихся уроков"""
    if lessons_remaining <= 0:
        return "Обучение завершено"
    
    # Базовое время на урок: 15 минут
    base_time_per_lesson = 15
    
    # Корректируем на основе успеваемости пользователя
    if user_performance:
        avg_score = user_performance.get('average_score', 70)
        if avg_score >= 85:
            # Быстрые ученики
            base_time_per_lesson = 12
        elif avg_score < 60:
            # Медленнее для тех, кто испытывает трудности
            base_time_per_lesson = 20
    
    total_minutes = lessons_remaining * base_time_per_lesson
    return format_duration(total_minutes * 60)  # Конвертируем в секунды


def get_encouragement_message(context: str, score: float = None) -> str:
    """Получение подходящего сообщения поощрения"""
    encouragements = {
        'lesson_start': [
            "Удачи в изучении! 🌟",
            "Вперед к новым знаниям! 📚",
            "У вас все получится! 💪"
        ],
        'lesson_complete': [
            "Отличная работа! ✨",
            "Урок успешно завершен! 🎉", 
            "Вы молодец! 👏"
        ],
        'lesson_failed': [
            "Не расстраивайтесь! Попробуйте еще раз 🤗",
            "Каждая ошибка - это опыт! 📖",
            "Продолжайте изучать, успех придет! 🌈"
        ],
        'quiz_correct': [
            "Правильно! 🎯",
            "Отлично! ✅",
            "Именно так! 👍"
        ],
        'quiz_wrong': [
            "Попробуйте еще раз 🤔",
            "Близко к правильному ответу! 📝",
            "Изучите материал внимательнее 📚"
        ]
    }
    
    messages = encouragements.get(context, ["Продолжайте обучение!"])
    
    # Выбираем сообщение на основе оценки
    if score is not None and context in ['lesson_complete', 'quiz_correct']:
        if score >= 90:
            return random.choice([
                "Превосходный результат! 🌟",
                "Вы настоящий эксперт! 🏆",
                "Блестящая работа! ✨"
            ])
        elif score >= 80:
            return random.choice(messages)
        else:
            return random.choice([
                "Хороший результат! Есть над чем поработать 📈",
                "Неплохо! Продолжайте изучать 📚"
            ])
    
    import random
    return random.choice(messages)


def sanitize_filename(filename: str) -> str:
    """Очистка имени файла от недопустимых символов"""
    # Заменяем недопустимые символы
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Удаляем множественные подчеркивания
    filename = re.sub(r'_+', '_', filename)
    
    # Обрезаем длину
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length - len(ext)] + ext
    
    return filename.strip('_')


def create_backup_filename(original_path: Union[str, Path]) -> str:
    """Создание имени файла резервной копии"""
    path = Path(original_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return f"{path.stem}_backup_{timestamp}{path.suffix}"


# Константы для часто используемых эмодзи
class Emojis:
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    LOADING = "⏳"
    FIRE = "🔥"
    STAR = "⭐"
    TROPHY = "🏆"
    BOOKS = "📚"
    BRAIN = "🧠"
    TARGET = "🎯"
    ROCKET = "🚀"
    HEART = "❤️"
    THUMBS_UP = "👍"
    CLAP = "👏"
    THINKING = "🤔"
    LIGHTBULB = "💡"
    CHART = "📊"
    CALENDAR = "📅"
    CLOCK = "🕐"