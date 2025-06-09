"""
Вспомогательные утилиты для бота
"""
import logging
from urllib.parse import parse_qs

logger = logging.getLogger(__name__)


def parse_callback_data(data: str) -> dict:
    """
    Парсит строку callback_data формата 'action:value;key:value' в словарь.
    
    Args:
        data: Строка вида "action:topic;tid:r_basics;lesson_id:1"
    
    Returns:
        dict: {"action": "topic", "tid": "r_basics", "lesson_id": "1"}
    """
    if not data:
        return {}
    
    try:
        # Заменяем ';' на '&' для совместимости с parse_qs
        normalized_data = data.replace(';', '&')
        parsed = parse_qs(normalized_data)
        
        # Преобразуем {'key': ['value']} в {'key': 'value'}
        result = {k: v[0] for k, v in parsed.items()}
        
        logger.debug(f"Parsed callback_data: {data} -> {result}")
        return result
        
    except Exception as e:
        logger.error(f"Ошибка парсинга callback_data '{data}': {e}")
        return {}


def validate_callback_data(data: dict, required_fields: list) -> bool:
    """
    Валидация parsed callback data
    
    Args:
        data: Распарсенные данные
        required_fields: Список обязательных полей
    
    Returns:
        bool: True если все поля присутствуют
    """
    for field in required_fields:
        if field not in data:
            logger.warning(f"Отсутствует обязательное поле '{field}' в callback_data")
            return False
    return True